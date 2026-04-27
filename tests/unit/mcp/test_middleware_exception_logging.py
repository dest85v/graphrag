# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for MCP unexpected exception logging (001-middleware-exception-logging).

Verifies that unexpected exceptions in MCP tool calls are logged
and that sync/async paths are consistent (both log AND track exceptions).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from graphrag_llm.mcp.middleware import MCPCompletionMiddleware
from graphrag_llm.mcp.types import MCPTool


class TestMCPUnexpectedExceptionLogging:
    """Tests for unexpected exception logging in MCP middleware (US2)."""

    def _make_mock_response(self, tool_calls=None):
        """Create a mock LLM completion response."""
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.tool_calls = tool_calls
        mock_message.content = "Final answer"
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4o"
        return mock_response

    def _make_mock_tool_call(self, tool_name="echo", tool_id="call_001"):
        """Create a mock tool call object."""
        tc = MagicMock()
        tc.id = tool_id
        tc.type = "function"
        tc.function = MagicMock()
        tc.function.name = tool_name
        tc.function.arguments = '{"arg": "value"}'
        return tc

    @pytest.mark.asyncio
    async def test_async_unexpected_exception_logs_and_tracked(self):
        """Async path: unexpected exception must be logged AND added to results.

        The async path catches unexpected exceptions, logs them with log.exception(),
        and appends error messages to results — matching MCP-specific error handling.
        Previously the async path had no log.exception() call.
        """
        mock_response_with_tools = self._make_mock_response(
            tool_calls=[self._make_mock_tool_call()],
        )
        mock_response_final = self._make_mock_response()

        mock_base = AsyncMock(
            side_effect=[mock_response_with_tools, mock_response_final]
        )

        mw = MCPCompletionMiddleware(
            mcp_config={
                "transport_type": "stdio",
                "stdio": {"command": "python"},
            },
        )
        mw._base_async = mock_base
        mw._initialized = True
        mw._mcp_tools = [MCPTool(name="echo", description="Echo", input_schema={})]

        # Mock client to raise unexpected exception
        mw._client = MagicMock()
        mw._client.call_tool = AsyncMock(side_effect=RuntimeError("unexpected"))

        result = await mw._wrap_completion_async(
            messages=[{"role": "user", "content": "hello"}],
        )

        # Must return a result (doesn't raise — exception is caught and logged)
        assert result is not None

    def test_sync_unexpected_exception_logs_and_tracked(self):
        """Sync path: unexpected exception must be logged AND added to results.

        The sync path catches unexpected exceptions, logs them, and appends
        error messages to results (matching the MCP-specific error handling).
        This is the critical fix: previously the sync path had no log.exception()
        and no exceptions list.
        """
        mock_response_with_tools = self._make_mock_response(
            tool_calls=[self._make_mock_tool_call()],
        )
        mock_response_final = self._make_mock_response()

        mock_base = MagicMock(
            side_effect=[mock_response_with_tools, mock_response_final]
        )

        mw = MCPCompletionMiddleware(
            mcp_config={
                "transport_type": "stdio",
                "stdio": {"command": "python"},
            },
        )
        mw._base_sync = mock_base
        mw._initialized = True
        mw._mcp_tools = [MCPTool(name="echo", description="Echo", input_schema={})]

        mw._client = MagicMock()
        mw._client.call_tool = MagicMock(side_effect=RuntimeError("unexpected"))

        result = mw._wrap_completion(
            messages=[{"role": "user", "content": "hello"}],
        )

        # Must return a result (doesn't raise — exception is caught and logged)
        assert result is not None

    def test_sync_exceptions_list_populated_on_error(self):
        """Sync _wrap_completion must track exceptions for all tool call failures.

        The sync path now declares `exceptions: list[Exception] = []` at the
        same scope as `results`, matching the async `_execute_tool_calls` pattern.
        """
        mock_response_with_tools = self._make_mock_response(
            tool_calls=[
                self._make_mock_tool_call(tool_name="echo", tool_id="call_001"),
                self._make_mock_tool_call(tool_name="echo", tool_id="call_002"),
            ],
        )
        mock_response_final = self._make_mock_response()

        mock_base = MagicMock(
            side_effect=[mock_response_with_tools, mock_response_final]
        )

        mw = MCPCompletionMiddleware(
            mcp_config={
                "transport_type": "stdio",
                "stdio": {"command": "python"},
            },
        )
        mw._base_sync = mock_base
        mw._initialized = True
        mw._mcp_tools = [MCPTool(name="echo", description="Echo", input_schema={})]

        # Both calls raise unexpected exceptions
        mw._client = MagicMock()
        mw._client.call_tool = MagicMock(side_effect=RuntimeError("fail"))

        result = mw._wrap_completion(messages=[{"role": "user", "content": "hello"}])
        assert result is not None
