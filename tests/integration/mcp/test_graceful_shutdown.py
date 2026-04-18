# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Integration tests for MCP graceful shutdown and lifecycle.

Tests subprocess termination, connection loss handling, and cleanup.
Uses mocked subprocess to avoid requiring a real MCP server.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from graphrag_llm.config.mcp_config import MCPConfig, MCPStdioConfig
from graphrag_llm.mcp.client import MCPClient, MCPConnectionError, MCPState
from graphrag_llm.mcp.types import MCPTool


class TestGracefulShutdown:
    """Tests for MCP client graceful shutdown."""

    @pytest.mark.asyncio
    async def test_disconnect_terminates_subprocess(self):
        """Test that disconnect terminates the stdio subprocess."""
        mock_transport = MagicMock()
        mock_transport.disconnect = AsyncMock()
        mock_transport.is_connected = True

        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python", args=["-m", "server"]),
        )
        client = MCPClient(config)
        client._transport = mock_transport
        client._state = MCPState.INITIALIZED

        await client.disconnect()

        mock_transport.disconnect.assert_called_once()
        assert client.state == MCPState.CLOSED
        assert client._disconnected is True

    @pytest.mark.asyncio
    async def test_disconnect_without_transport(self):
        """Test disconnect without a transport is safe."""
        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        await client.disconnect()  # Should not raise
        assert client.state == MCPState.CLOSED

    @pytest.mark.asyncio
    async def test_double_disconnect_is_safe(self):
        """Test calling disconnect twice doesn't raise."""
        mock_transport = MagicMock()
        mock_transport.disconnect = AsyncMock()

        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        client._transport = mock_transport
        client._state = MCPState.INITIALIZED

        await client.disconnect()
        await client.disconnect()  # Second call should be safe
        assert client.state == MCPState.CLOSED


class TestConnectionLost:
    """Tests for MCP connection loss handling."""

    @pytest.mark.asyncio
    async def test_tool_call_after_disconnect_raises(self):
        """Test tool call after disconnect raises MCPConnectionError."""
        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)

        with pytest.raises(MCPConnectionError, match="Not connected"):
            await client.call_tool("some_tool")

    @pytest.mark.asyncio
    async def test_initialize_after_disconnect_raises(self):
        """Test initialize after disconnect raises MCPConnectionError."""
        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        await client.disconnect()

        with pytest.raises(MCPConnectionError, match="closed"):
            await client.connect()


class TestMCPClientContextManagerCleanup:
    """Tests for MCP client async context manager cleanup."""

    @pytest.mark.asyncio
    async def test_context_manager_calls_disconnect(self):
        """Test that exiting context manager calls disconnect."""
        mock_transport = MagicMock()
        mock_transport.disconnect = AsyncMock()
        mock_transport._read_stream = AsyncMock(
            __aiter__=MagicMock(return_value=iter([])),
        )
        mock_transport._write_stream = AsyncMock(
            __aiter__=MagicMock(return_value=iter([])),
        )

        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        client._transport = mock_transport

        async with client:
            assert client._transport == mock_transport

        mock_transport.disconnect.assert_called_once()
        assert client.state == MCPState.CLOSED


class TestSubprocessCrashDetection:
    """Tests for MCP subprocess crash detection."""

    @pytest.mark.asyncio
    async def test_client_detects_disconnect_before_tool_call(self):
        """Test client raises error when not connected before tool call."""
        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        # State is DISCONNECTED, no session

        with pytest.raises(MCPConnectionError, match="Not connected"):
            await client.call_tool("any_tool")

    @pytest.mark.asyncio
    async def test_middleware_handles_connection_error(self):
        """Test middleware handles MCP connection errors gracefully."""
        from graphrag_llm.mcp.middleware import MCPCompletionMiddleware

        mw = MCPCompletionMiddleware(
            mcp_config={
                "transport_type": "stdio",
                "stdio": {"command": "python"},
            },
        )

        # Simulate connection error during tool call
        mock_response = MagicMock()
        mock_choice = MagicMock()
        tc = MagicMock()
        tc.id = "call_001"
        tc.function = MagicMock()
        tc.function.name = "test_tool"
        tc.function.arguments = "{}"
        mock_choice.message.tool_calls = [tc]
        mock_choice.message.content = ""
        mock_response.choices = [mock_choice]

        mock_base = AsyncMock(return_value=mock_response)
        mw._base_async = mock_base
        mw._initialized = True
        mw._mcp_tools = [MCPTool(name="test_tool", description="Test")]
        mw._client = MagicMock()
        mw._client.call_tool = AsyncMock(
            side_effect=MCPConnectionError("Connection lost"),
        )

        # Should handle the error and continue
        result = await mw._wrap_completion_async(
            messages=[{"role": "user", "content": "Test"}],
        )

        # Should return the second response (after error handling)
        assert result is not None


