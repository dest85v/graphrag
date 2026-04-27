# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""MCP completion middleware for graphrag-llm.

Wraps the LLM completion function to enable automatic MCP tool discovery
and invocation during chat completions. When enabled, the middleware
transparently handles the tool cycle: LLM tool calls -> MCP invocation ->
result formatting -> LLM final response.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from graphrag_llm.mcp.client import (
    MCPClient,
    MCPConnectionError,
    MCPTimeoutError,
    MCPToolError,
)
from graphrag_llm.types import (
    LLMCompletionResponse,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from graphrag_llm.mcp.types import MCPTool
    from graphrag_llm.types import (
        AsyncLLMFunction,
        LLMCompletionChunk,
        LLMCompletionFunction,
    )


log = logging.getLogger(__name__)


class MCPCompletionMiddleware:
    """Middleware that intercepts LLM completions to use MCP tools.

    Wraps the completion function and automatically handles the MCP tool
    call cycle when the LLM decides to use tools. The middleware is
    fully optional -- if no MCP config is provided, completions proceed
    normally without any MCP involvement.
    """

    def __init__(self, mcp_config: dict[str, Any] | None = None) -> None:
        """Initialize the MCP middleware.

        Parameters
        ----------
        mcp_config : dict[str, Any] | None
            MCP configuration. If None, MCP is disabled.
        """
        self._mcp_config = mcp_config
        self._client: MCPClient | None = None
        self._mcp_tools: list[MCPTool] = []
        self._initialized = False
        self._disabled = mcp_config is None
        self._base_sync: Any = None
        self._base_async: Any = None

    @staticmethod
    def _run_async(coro: Any) -> Any:
        """Run an async coroutine from sync code, reusing a running loop or creating one."""
        from graphrag_llm.middleware._event_loop import run_async_in_loop

        return run_async_in_loop(coro)

    def _should_use_mcp(self) -> bool:
        """Check if MCP is enabled."""
        return not self._disabled

    def _ensure_client(self) -> None:
        """Lazy-initialize the MCP client on first use."""
        if self._initialized or self._disabled:
            return
        from graphrag_llm.config.mcp_config import MCPConfig

        mcp_conf = MCPConfig(**self._mcp_config)  # type: ignore[arg-type]
        self._client = MCPClient(mcp_conf)
        self._initialized = True

    async def _initialize_mcp(self) -> None:
        """Connect to MCP server and discover tools."""
        if self._client is None:
            self._ensure_client()
        if self._client is None:
            return

        try:
            await self._client.connect()
            await self._client.initialize()
            self._mcp_tools = await self._client.list_tools()
            log.info(
                "MCP tools discovered: %d tools available",
                len(self._mcp_tools),
            )
        except (MCPConnectionError, MCPTimeoutError) as e:
            log.warning(
                "MCP initialization failed, disabling MCP for this session: %s",
                e,
            )
            self._mcp_tools = []

    def _convert_tools_to_openai_format(self) -> list[dict[str, Any]]:
        """Convert discovered MCP tools to OpenAI tool format.

        Returns
        -------
        list[dict[str, Any]]
            Tools formatted for OpenAI's tools parameter.
        """
        return [tool.to_openai_tool() for tool in self._mcp_tools]  # type: ignore[return-value]

    def _format_tool_results(
        self,
        tool_calls: list[Any],
        results: list[str],
    ) -> list[dict[str, Any]]:
        """Format tool call results as tool_result messages.

        Parameters
        ----------
        tool_calls : list[Any]
            The tool_call objects from the LLM response.
        results : list[str]
            The text results from MCP tool invocations.

        Returns
        -------
        list[dict[str, Any]]
            Messages to append to the conversation.
        """
        messages = []
        for i, (tc, result_text) in enumerate(zip(tool_calls, results, strict=False)):
            tool_id = getattr(tc, "id", f"call_{i}")
            tool_name = (
                getattr(tc, "function", None)
                and getattr(tc.function, "name", "<unknown>")
            ) or getattr(tc, "name", "<unknown>")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": result_text,
            })
            log.debug(
                "Tool call %s (%s): %s characters of result",
                tool_id,
                tool_name,
                len(result_text),
            )
        return messages

    def _make_available_tools_error(self) -> str:
        """Generate an error message listing available tools.

        Used when the LLM hallucinates a tool name.

        Returns
        -------
        str
            Error message listing available tool names.
        """
        names = (
            ", ".join(sorted(t.name for t in self._mcp_tools))
            if self._mcp_tools
            else "(none)"
        )
        return (
            f"Error: Tool not found. Available tools: [{names}]. "
            "Please use only the listed tool names."
        )

    async def _execute_tool_calls(
        self,
        tool_calls: list[Any],
    ) -> tuple[list[str], list[Exception]]:
        """Execute LLM tool calls via MCP server.

        Parameters
        ----------
        tool_calls : list[Any]
            Tool call objects from the LLM response.

        Returns
        -------
        tuple[list[str], list[Exception]]
            Lists of results (strings) and exceptions, one per tool call.
        """
        results: list[str] = []
        exceptions: list[Exception] = []

        if self._client is None:
            for _ in tool_calls:
                results.append("Error: MCP client not connected.")
                exceptions.append(MCPConnectionError("Client not connected"))
            return results, exceptions

        for tc in tool_calls:
            # Extract tool name and arguments
            tool_name = (
                getattr(tc, "function", None) and getattr(tc.function, "name", None)
            ) or getattr(tc, "name", None)
            tool_args = (
                (
                    getattr(tc, "function", None)
                    and getattr(tc.function, "arguments", "{}")
                )
                or getattr(tc, "input", None)
                or {}
            )

            # Handle string arguments (JSON-encoded)
            if isinstance(tool_args, str):
                try:
                    tool_args = json.loads(tool_args)
                except (json.JSONDecodeError, ValueError):
                    tool_args = {}

            if not tool_name:
                results.append("Error: Could not determine tool name from tool call.")
                exceptions.append(ValueError("No tool name in tool call"))
                continue

            try:
                result = await self._client.call_tool(
                    name=tool_name,
                    arguments=tool_args if isinstance(tool_args, dict) else {},
                )
                results.append(result)
            except MCPToolError as e:
                results.append(str(e))
                exceptions.append(e)
            except MCPConnectionError as e:
                results.append(f"Connection error: {e}")
                exceptions.append(e)
            except MCPTimeoutError as e:
                results.append(f"Timeout error: {e}")
                exceptions.append(e)
            except Exception as e:  # noqa: BLE001
                results.append(f"Unexpected error: {e}")
                exceptions.append(e)

        return results, exceptions

    async def _wrap_completion_async(
        self,
        **kwargs: Any,
    ) -> LLMCompletionResponse | AsyncIterator[LLMCompletionChunk]:
        """Wrap the async completion function with MCP tool handling.

        Parameters
        ----------
        **kwargs
            Completion arguments passed to the underlying LLM function.

        Returns
        -------
        LLMCompletionResponse | AsyncIterator[LLMCompletionChunk]
            The LLM response, potentially after tool call cycles.
        """
        # Check MCP availability once
        if not self._should_use_mcp():
            msg = "MCP is not configured"
            raise ValueError(msg)

        # Ensure client is initialized
        if not self._initialized:
            self._ensure_client()

        # Lazy init: connect and discover tools on first completion
        if not self._initialized:
            await self._initialize_mcp()

        # Get tools for the LLM
        openai_tools = self._convert_tools_to_openai_format()

        # Build messages with tool definitions if not present
        messages: list[dict[str, Any]] = list(kwargs.pop("messages", []))
        kwargs["tools"] = openai_tools or kwargs.get("tools")

        max_iterations = 10  # Safety limit to prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            log.debug("MCP tool cycle iteration %d", iteration)

            # Call the LLM
            response = await self._base_async(  # type: ignore[misc]
                messages=messages,
                **kwargs,
            )

            # Check for tool calls in the response
            try:
                tool_calls = getattr(  # type: ignore[union-attr]
                    getattr(
                        getattr(response, "choices", [None])[0],
                        "message",
                        None,
                    ),
                    "tool_calls",
                    None,
                )
            except Exception:
                log.exception("Failed to extract tool_calls from response")
                tool_calls = None

            if not tool_calls:
                # No tool calls -- this is the final response
                return response  # type: ignore[return-value]

            # Execute tool calls via MCP
            results, exceptions = await self._execute_tool_calls(tool_calls)

            # Format results as tool_result messages
            tool_messages = self._format_tool_results(tool_calls, results)
            messages.extend(tool_messages)

            # Check if all results were errors
            if exceptions and all(isinstance(e, Exception) for e in exceptions):
                # LLM may need guidance -- add error info and retry
                error_messages = [
                    {
                        "role": "tool",
                        "tool_call_id": getattr(tc, "id", "unknown"),
                        "content": self._make_available_tools_error(),
                    }
                    for tc in tool_calls
                ]
                messages.extend(error_messages)

        # Safety: exceeded max iterations
        return LLMCompletionResponse(  # type: ignore[return-value]
            model=kwargs.get("model", "unknown"),
            choices=[],
            object="chat.completion",
            usage=None,
            created=int(__import__("time").time()),
            id="mcp-tool-limit",
        )

    def _wrap_completion(
        self,
        **kwargs: Any,
    ) -> LLMCompletionResponse | Iterator[LLMCompletionChunk]:
        """Wrap the sync completion function with MCP tool handling."""
        if not self._should_use_mcp():
            msg = "MCP is not configured"
            raise ValueError(msg)

        if not self._initialized:
            self._ensure_client()

        if not self._initialized:
            self._run_async(self._initialize_mcp())

        openai_tools = self._convert_tools_to_openai_format()

        messages: list[dict[str, Any]] = list(kwargs.pop("messages", []))
        kwargs["tools"] = openai_tools or kwargs.get("tools")

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            response = self._base_sync(  # type: ignore[misc]
                messages=messages,
                **kwargs,
            )

            try:
                tool_calls = getattr(  # type: ignore[union-attr]
                    getattr(
                        getattr(response, "choices", [None])[0],
                        "message",
                        None,
                    ),
                    "tool_calls",
                    None,
                )
            except Exception:
                log.exception("Failed to extract tool_calls from response")
                tool_calls = None

            if not tool_calls:
                return response  # type: ignore[return-value]

            # For sync, execute tools in a loop
            results: list[str] = []
            for tc in tool_calls:
                tool_name = (
                    getattr(tc, "function", None) and getattr(tc.function, "name", None)
                ) or getattr(tc, "name", None)
                if not tool_name:
                    results.append("Error: Could not determine tool name.")
                    continue
                if self._client is None:
                    results.append("Error: MCP client not connected.")
                    continue
                try:
                    args = (
                        getattr(tc.function, "arguments", "{}")
                        if hasattr(tc, "function")
                        else {}
                    )
                    if isinstance(args, str):
                        args = json.loads(args)
                    elif not isinstance(args, dict):
                        args = {}
                    result = self._run_async(
                        self._client.call_tool(
                            name=tool_name,
                            arguments=args,
                        ),
                    )
                    results.append(str(result))
                except Exception as e:  # noqa: BLE001
                    results.append(f"Error: {e}")

            tool_messages = self._format_tool_results(tool_calls, results)
            messages.extend(tool_messages)

        return LLMCompletionResponse(  # type: ignore[return-value]
            model=kwargs.get("model", "unknown"),
            choices=[],
            object="chat.completion",
            usage=None,
            created=int(__import__("time").time()),
            id="mcp-tool-limit",
        )

    def wrap(
        self,
        model_fn: LLMCompletionFunction,
        async_model_fn: AsyncLLMFunction,
    ) -> tuple[LLMCompletionFunction, AsyncLLMFunction]:
        """Wrap completion functions with MCP tool handling.

        Parameters
        ----------
        model_fn : LLMCompletionFunction
            The synchronous completion function.
        async_model_fn : AsyncLLMFunction
            The asynchronous completion function.

        Returns
        -------
        tuple[LLMCompletionFunction, AsyncLLMFunction]
            Wrapped completion functions.
        """
        if self._disabled:
            return (model_fn, async_model_fn)

        self._base_sync = model_fn
        self._base_async = async_model_fn

        # pyright can't verify the lambda return types match the protocol
        result: Any = (  # type: ignore[assignment]
            self._wrap_completion,
            self._wrap_completion_async,
        )
        return result  # type: ignore[return-value]

    async def cleanup(self) -> None:
        """Clean up MCP resources.

        Disconnects the MCP client if connected.
        """
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception:
                log.exception("Error during MCP middleware cleanup")
            finally:
                self._client = None
