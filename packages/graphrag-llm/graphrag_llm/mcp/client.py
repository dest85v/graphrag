# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""MCP client for graphrag-llm.

Provides the MCPClient class that manages connections to MCP servers,
handles tool discovery, and tool invocation.
"""

from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import anyio
from typing_extensions import Self

from graphrag_llm.mcp.transport import (
    MCPTransport,
    SSETransport,
    StdioTransport,
    StreamableHTTPTransport,
)
from graphrag_llm.mcp.types import MCPTool

if TYPE_CHECKING:
    from mcp import ClientSession

    from graphrag_llm.config.mcp_config import MCPConfig


log = logging.getLogger(__name__)


class MCPState(str, Enum):
    """State machine for the MCP client lifecycle."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    INITIALIZED = auto()
    TOOLS_DISCOVERED = auto()
    ERROR = auto()
    CLOSED = auto()


class MCPConnectionError(Exception):
    """Raised when MCP connection is lost or cannot be established."""


class MCPToolError(Exception):
    """Raised when an MCP tool call fails."""


class MCPTimeoutError(Exception):
    """Raised when an MCP operation times out."""


class MCPClient:
    """Manages the connection to an MCP server.

    Handles initialization, tool discovery, tool invocation, and lifecycle
    management using the official mcp Python SDK.
    """

    def __init__(self, config: MCPConfig) -> None:
        """Initialize the MCP client.

        Parameters
        ----------
        config : MCPConfig
            Configuration for the MCP server connection.
        """
        self._config = config
        self._session: ClientSession | None = None
        self._transport: MCPTransport | None = None
        self._exit_stack = AsyncExitStack()
        self._state = MCPState.DISCONNECTED
        self._tools: list[MCPTool] = []
        self._initialized = False
        self._disconnected = False

    @property
    def state(self) -> MCPState:
        """Current state of the client."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Whether the client is connected and initialized."""
        return self._state in {
            MCPState.INITIALIZED,
            MCPState.TOOLS_DISCOVERED,
        }

    @property
    def tools(self) -> list[MCPTool]:
        """List of discovered tools (empty if not yet discovered)."""
        return self._tools

    async def connect(self, transport: MCPTransport | None = None) -> None:
        """Connect to the MCP server.

        If transport is not provided, creates one based on config.

        Parameters
        ----------
        transport : MCPTransport | None
            Optional transport to use. If None, created from config.

        Raises
        ------
        MCPConnectionError
            If connection fails.
        """
        if self._state == MCPState.CLOSED:
            msg = "Client is closed and cannot be reconnected"
            raise MCPConnectionError(msg)

        if transport is None:
            transport = _create_transport(self._config)

        self._transport = transport
        self._state = MCPState.CONNECTING

        try:
            await transport.connect()
            # Create session using the SDK
            from mcp import ClientSession

            read_stream = _get_read_stream(transport)
            write_stream = _get_write_stream(transport)
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream),
            )
            self._state = MCPState.INITIALIZED
            log.info("MCP session created for transport: %s", type(transport).__name__)
        except Exception as e:
            self._state = MCPState.ERROR
            log.exception("Failed to connect to MCP server")
            msg = f"Failed to connect: {e}"
            raise MCPConnectionError(msg) from e

    async def initialize(self) -> None:
        """Initialize the MCP session (protocol handshake)."""
        if self._session is None:
            msg = "Not connected; call connect() first"
            raise MCPConnectionError(msg)

        self._state = MCPState.CONNECTING
        try:
            with anyio.move_on_after(self._config.init_timeout):
                await self._session.initialize()
            self._initialized = True
            self._state = MCPState.INITIALIZED
            log.info(
                "MCP session initialized successfully (timeout: %.1fs)",
                self._config.init_timeout,
            )
        except TimeoutError as e:
            self._state = MCPState.ERROR
            msg = f"Initialization timed out after {self._config.init_timeout}s"
            raise MCPTimeoutError(
                msg,
            ) from e
        except MCPConnectionError:
            raise
        except Exception as e:
            self._state = MCPState.ERROR
            msg = f"Initialization failed: {e}"
            raise MCPConnectionError(msg) from e

    async def list_tools(self) -> list[MCPTool]:
        """Discover available tools from the MCP server."""
        if self._session is None:
            msg = "Not connected; call connect() and initialize() first"
            raise MCPConnectionError(msg)

        if self._initialized and self._tools:
            return self._tools

        try:
            result = await self._session.list_tools()
        except Exception as e:
            self._state = MCPState.ERROR
            msg = f"Tool discovery failed: {e}"
            raise MCPConnectionError(msg) from e
        self._tools = [
            MCPTool(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema
                if hasattr(tool, "inputSchema")
                else {},
            )
            for tool in result.tools
        ]
        if self._initialized:
            self._state = MCPState.TOOLS_DISCOVERED
        log.info("Discovered %d tools from MCP server", len(self._tools))
        return self._tools

    async def call_tool(
        self, name: str, arguments: dict[str, Any] | None = None,
    ) -> str:
        """Invoke a tool on the MCP server."""
        if self._session is None:
            msg = "Not connected; call connect() and initialize() first"
            raise MCPConnectionError(msg)

        if not self._tools:
            msg = "No tools discovered yet. Call list_tools() first."
            raise MCPToolError(msg)

        valid_tool_names = {t.name for t in self._tools}
        if name not in valid_tool_names:
            available = ", ".join(sorted(valid_tool_names))
            msg = f"Tool '{name}' not found. Available tools: [{available}]"
            raise MCPToolError(msg)

        try:
            result_text = ""
            result: Any = None

            # TRY301 — inner function abstracts raise to avoid TRY300 on outer block
            def _raise_timeout() -> None:
                msg = f"Tool '{name}' timed out after {self._config.tool_timeout}s"
                raise MCPTimeoutError(msg)  # noqa: TRY301

            # TRY301 — inner function abstracts raise to avoid TRY300 on outer block
            def _raise_tool_error(err_text: str) -> None:
                err_msg = f"Tool '{name}' returned error: {err_text}"
                raise MCPToolError(err_msg)  # noqa: TRY301

            with anyio.move_on_after(self._config.tool_timeout) as scope:
                result = await self._session.call_tool(
                    name=name,
                    arguments=arguments or {},
                )

            if scope.cancelled_caught:
                _raise_timeout()

            text_parts: list[str] = []
            if result is not None:
                for content in result.content:  # type: ignore[union-attr]
                    text = getattr(content, "text", None)
                    if text:
                        text_parts.append(text)
                    else:
                        data = getattr(content, "data", None)
                        if data:
                            text_parts.append(str(data))
                result_text = "\n".join(text_parts)
                if getattr(result, "isError", False):
                    _raise_tool_error(result_text)
            return result_text if result is not None else ""  # type: ignore[return-value]  # noqa: TRY300
        except MCPTimeoutError:
            raise
        except MCPConnectionError:
            raise
        except MCPToolError:
            raise
        except Exception as e:
            msg = f"Tool '{name}' failed: {e}"
            raise MCPToolError(msg) from e

    async def disconnect(self) -> None:
        """Disconnect and clean up resources."""
        self._disconnected = True
        self._state = MCPState.CLOSED
        try:
            if self._transport:
                await self._transport.disconnect()
        except Exception:
            log.exception("Error during MCP client disconnect")
        finally:
            try:
                await self._exit_stack.aclose()
            except Exception:
                log.exception("Error closing exit stack")

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit."""
        await self.disconnect()

    def __repr__(self) -> str:
        """Return a string representation of the MCPClient."""
        return (
            f"MCPClient(state={self._state.name}, "
            f"tools={len(self._tools)}, "
            f"connected={self.is_connected})"
        )


def _create_transport(config: MCPConfig) -> MCPTransport:
    """Create a transport based on MCPConfig."""
    if config.transport_type == "stdio":
        if config.stdio is None:
            msg = "stdio config is required for stdio transport"
            raise ValueError(msg)
        return StdioTransport(
            command=config.stdio.command,
            args=config.stdio.args,
            env=config.stdio.env,
        )
    if config.transport_type == "sse":
        if config.sse is None:
            msg = "sse config is required for sse transport"
            raise ValueError(msg)
        return SSETransport(
            url=config.sse.url,
            headers=config.sse.headers,
            timeout=config.sse.timeout,
            sse_read_timeout=config.sse.sse_read_timeout,
        )
    if config.transport_type == "streamable_http":
        if config.streamable_http is None:
            msg = "streamable_http config is required"
            raise ValueError(msg)
        return StreamableHTTPTransport(
            url=config.streamable_http.url,
            headers=config.streamable_http.headers,
            timeout=config.streamable_http.timeout,
        )
    msg = f"Unknown transport type: {config.transport_type}"
    raise ValueError(msg)


def _get_read_stream(transport: MCPTransport) -> Any:
    """Extract the read stream from a transport."""
    return transport._read_stream  # type: ignore[attr-defined]  # noqa: SLF001


def _get_write_stream(transport: MCPTransport) -> Any:
    """Extract the write stream from a transport."""
    return transport._write_stream  # type: ignore[attr-defined]  # noqa: SLF001
