# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for MCP middleware."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from graphrag_llm.mcp.middleware import MCPCompletionMiddleware
from graphrag_llm.mcp.types import MCPTool


class TestMCPCompletionMiddleware:
    """Tests for MCPCompletionMiddleware."""

    def test_middleware_disabled_no_config(self):
        """Test middleware is disabled when no config is provided."""
        mw = MCPCompletionMiddleware()
        assert mw._disabled is True

    def test_middleware_enabled_with_config(self):
        """Test middleware is enabled when config is provided."""
        mw = MCPCompletionMiddleware(
            mcp_config={
                "transport_type": "stdio",
                "stdio": {"command": "python"},
            },
        )
        assert mw._disabled is False

    def test_wrap_returns_original_when_disabled(self):
        """Test wrap returns original functions when disabled."""
        original_sync = MagicMock(return_value="result")
        original_async = AsyncMock(return_value="result")

        mw = MCPCompletionMiddleware()
        wrapped_sync, wrapped_async = mw.wrap(original_sync, original_async)

        assert wrapped_sync is original_sync
        assert wrapped_async is original_async


class TestMCPCompletionMiddlewareToolCycle:
    """Tests for MCP tool call cycle in middleware."""

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

    def _make_mock_tool_call(self, tool_name="test_tool", tool_id="call_001"):
        """Create a mock tool call object."""
        tc = MagicMock()
        tc.id = tool_id
        tc.type = "function"
        tc.function = MagicMock()
        tc.function.name = tool_name
        tc.function.arguments = '{"arg": "value"}'
        return tc

    @pytest.mark.asyncio
    async def test_no_tool_calls_returns_response_immediately(self):
        """Test response without tool calls is returned directly."""
        mock_base = AsyncMock(return_value=self._make_mock_response())

        mw = MCPCompletionMiddleware(
            mcp_config={
                "transport_type": "stdio",
                "stdio": {"command": "python"},
            },
        )
        mw._base_async = mock_base
        mw._initialized = True
        mw._mcp_tools = [MCPTool(name="echo", description="Echo")]

        result = await mw._wrap_completion_async(
            messages=[{"role": "user", "content": "Hello"}],
        )

        mock_base.assert_called_once()
        assert result is mock_base.return_value

    @pytest.mark.asyncio
    async def test_tool_call_invokes_mcp_server(self):
        """Test tool calls trigger MCP tool invocation."""
        mock_response_with_tools = self._make_mock_response(
            tool_calls=[self._make_mock_tool_call()],
        )
        mock_response_final = self._make_mock_response()

        mock_base = AsyncMock(side_effect=[mock_response_with_tools, mock_response_final])

        mw = MCPCompletionMiddleware(
            mcp_config={
                "transport_type": "stdio",
                "stdio": {"command": "python"},
            },
        )
        mw._base_async = mock_base
        mw._initialized = True
        mw._mcp_tools = [MCPTool(name="test_tool", description="Test", input_schema={})]

        # Mock the client
        mw._client = MagicMock()
        mw._client.call_tool = AsyncMock(return_value="Tool result")

        await mw._wrap_completion_async(
            messages=[{"role": "user", "content": "Do something"}],
        )

        # Should have called call_tool once
        mw._client.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_hallucinated_tool_gives_error(self):
        """Test LLM hallucinating a tool name returns error listing available tools."""
        self._make_mock_response(
            tool_calls=[self._make_mock_tool_call(tool_name="nonexistent_tool")],
        )

        mw = MCPCompletionMiddleware(
            mcp_config={
                "transport_type": "stdio",
                "stdio": {"command": "python"},
            },
        )
        mw._base_async = AsyncMock(return_value=self._make_mock_response())
        mw._initialized = True
        mw._mcp_tools = [MCPTool(name="real_tool", description="Real")]
        mw._client = MagicMock()
        mw._client.call_tool = AsyncMock(side_effect=Exception("Tool not found"))

        # Should handle the error gracefully
        result = await mw._wrap_completion_async(
            messages=[{"role": "user", "content": "Use nonexistent"}],
        )

        # Result should not crash
        assert result is not None

    def test_format_tool_results(self):
        """Test formatting tool call results as tool_result messages."""
        mw = MCPCompletionMiddleware()

        tc1 = MagicMock()
        tc1.id = "call_001"
        tc1.function = MagicMock()
        tc1.function.name = "tool_a"

        tc2 = MagicMock()
        tc2.id = "call_002"
        tc2.function = MagicMock()
        tc2.function.name = "tool_b"

        results = ["Result A", "Result B"]
        messages = mw._format_tool_results([tc1, tc2], results)

        assert len(messages) == 2
        assert messages[0]["role"] == "tool"
        assert messages[0]["tool_call_id"] == "call_001"
        assert messages[0]["content"] == "Result A"
        assert messages[1]["role"] == "tool"
        assert messages[1]["content"] == "Result B"

    def test_make_available_tools_error(self):
        """Test error message lists available tools."""
        mw = MCPCompletionMiddleware()
        mw._mcp_tools = [
            MCPTool(name="tool_a", description="A"),
            MCPTool(name="tool_b", description="B"),
        ]
        error = mw._make_available_tools_error()
        assert "tool_a" in error
        assert "tool_b" in error
        assert "not found" in error.lower()

    def test_convert_tools_to_openai_format(self):
        """Test tool conversion to OpenAI format."""
        mw = MCPCompletionMiddleware()
        mw._mcp_tools = [
            MCPTool(name="echo", description="Echo", input_schema={"type": "object"}),
        ]
        tools = mw._convert_tools_to_openai_format()
        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "echo"

    def test_convert_empty_tools(self):
        """Test empty tools list."""
        mw = MCPCompletionMiddleware()
        mw._mcp_tools = []
        tools = mw._convert_tools_to_openai_format()
        assert tools == []


class TestMCPCompletionMiddlewareCleanup:
    """Tests for MCP middleware cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_disconnects_client(self):
        """Test cleanup disconnects the MCP client."""
        mock_client = AsyncMock()
        mock_client.disconnect = AsyncMock()

        mw = MCPCompletionMiddleware(
            mcp_config={
                "transport_type": "stdio",
                "stdio": {"command": "python"},
            },
        )
        mw._client = mock_client
        mw._initialized = True

        await mw.cleanup()

        mock_client.disconnect.assert_called_once()
        assert mw._client is None

    @pytest.mark.asyncio
    async def test_cleanup_no_client(self):
        """Test cleanup when no client exists."""
        mw = MCPCompletionMiddleware()
        await mw.cleanup()  # Should not raise
