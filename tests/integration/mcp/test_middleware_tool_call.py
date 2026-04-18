# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Integration tests for MCP middleware tool call cycle.

Tests the end-to-end flow: completion → tool discovery → tool invocation → LLM response.
Uses mocked MCP client to simulate real server interactions.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from graphrag_llm.mcp.middleware import MCPCompletionMiddleware
from graphrag_llm.mcp.types import MCPTool


class TestMiddlewareToolCallCycle:
    """End-to-end tests for the MCP middleware tool call cycle."""

    def _make_completion_response(
        self, has_tool_calls=False, tool_name="test_tool", content="Final answer",
        tool_arguments=None,
    ):
        """Create a mock LLM completion response."""
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = content

        if has_tool_calls:
            tc = MagicMock()
            tc.id = "call_001"
            tc.type = "function"
            tc.function = MagicMock()
            tc.function.name = tool_name
            tc.function.arguments = tool_arguments or '{"query": "test"}'
            mock_message.tool_calls = [tc]
        else:
            mock_message.tool_calls = None

        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4o"
        mock_response.object = "chat.completion"
        mock_response.usage = None
        mock_response.created = 1234567890
        mock_response.id = "chatcmpl-test"
        return mock_response

    @pytest.mark.asyncio
    async def test_tool_call_discovery_invokes_mcp(self):
        """Test that LLM tool calls trigger MCP tool discovery and invocation."""
        # First response has tool calls, second response (after tool result) has final answer
        mock_base = AsyncMock(
            side_effect=[
                self._make_completion_response(
                    has_tool_calls=True, tool_name="list_files",
                    content="Listing files in /tmp",
                    tool_arguments='{"path": "/tmp"}',
                ),
                self._make_completion_response(
                    has_tool_calls=False, content="Files in /tmp: file1.txt, file2.txt",
                ),
            ],
        )

        mw = MCPCompletionMiddleware(
            mcp_config={
                "transport_type": "stdio",
                "stdio": {
                    "command": "python",
                    "args": ["-m", "mcp_server"],
                },
                "init_timeout": 30.0,
                "tool_timeout": 30.0,
            },
        )
        mw._base_async = mock_base
        mw._initialized = True

        # Mock MCP client with tools
        mw._client = MagicMock()
        mw._client.tools = [
            MCPTool(
                name="list_files",
                description="List files in directory",
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            ),
        ]
        mw._mcp_tools = mw._client.tools
        mw._client.call_tool = AsyncMock(return_value="file1.txt\nfile2.txt")

        # Make the completion call
        result = await mw._wrap_completion_async(
            messages=[{"role": "user", "content": "What files are in /tmp?"}],
        )

        # Verify MCP tool was invoked
        mw._client.call_tool.assert_called_once()
        call_args = mw._client.call_tool.call_args
        assert call_args.kwargs["name"] == "list_files"
        assert "path" in call_args.kwargs["arguments"]

        # Verify final response is returned
        assert result is not None  # type: ignore[union-attr]
        assert "file1.txt" in result.choices[0].message.content

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_executed_sequentially(self):
        """Test multiple tool calls in one response are executed sequentially."""
        # First response has 2 tool calls
        tc1 = MagicMock()
        tc1.id = "call_001"
        tc1.type = "function"
        tc1.function = MagicMock()
        tc1.function.name = "read_file"
        tc1.function.arguments = '{"path": "/tmp/a.txt"}'

        tc2 = MagicMock()
        tc2.id = "call_002"
        tc2.type = "function"
        tc2.function = MagicMock()
        tc2.function.name = "read_file"
        tc2.function.arguments = '{"path": "/tmp/b.txt"}'

        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.tool_calls = [tc1, tc2]
        mock_choice.message = mock_message
        mock_response_with_tools = MagicMock()
        mock_response_with_tools.choices = [mock_choice]

        mock_response_final = self._make_completion_response(
            has_tool_calls=False, content="Contents of a.txt and b.txt",
        )

        mock_base = AsyncMock(
            side_effect=[mock_response_with_tools, mock_response_final],
        )

        mw = MCPCompletionMiddleware(
            mcp_config={
                "transport_type": "stdio",
                "stdio": {"command": "python"},
            },
        )
        mw._base_async = mock_base
        mw._initialized = True

        mw._client = MagicMock()
        mw._mcp_tools = [
            MCPTool(
                name="read_file",
                description="Read a file",
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            ),
        ]
        mw._client.call_tool = AsyncMock(
            side_effect=["Content of a.txt", "Content of b.txt"],
        )

        await mw._wrap_completion_async(
            messages=[{"role": "user", "content": "Read both files"}],
        )

        # Both tool calls should be executed
        assert mw._client.call_tool.call_count == 2

    @pytest.mark.asyncio
    async def test_mcp_error_returned_to_llm(self):
        """Test that MCP errors are returned to LLM for recovery."""
        mock_base = AsyncMock(
            side_effect=[
                self._make_completion_response(has_tool_calls=True),
                self._make_completion_response(
                    has_tool_calls=False,
                    content="I understand, here's the answer without using tools.",
                ),
            ],
        )

        mw = MCPCompletionMiddleware(
            mcp_config={
                "transport_type": "stdio",
                "stdio": {"command": "python"},
            },
        )
        mw._base_async = mock_base
        mw._initialized = True

        mw._client = MagicMock()
        mw._mcp_tools = [MCPTool(name="broken_tool", description="Broken")]
        mw._client.call_tool = AsyncMock(side_effect=Exception("Server error 500"))

        result = await mw._wrap_completion_async(
            messages=[{"role": "user", "content": "Use the broken tool"}],
        )

        # Should recover with a non-error response
        assert result is not None  # type: ignore[union-attr]
        assert hasattr(result, "choices")
