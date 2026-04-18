# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for MCP transports."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from graphrag_llm.mcp.transport import (
    SSETransport,
    StdioTransport,
    StreamableHTTPTransport,
)


class TestStdioTransport:
    """Tests for StdioTransport."""

    @patch("mcp.client.stdio.stdio_client")
    @patch("graphrag_llm.mcp.transport.AsyncExitStack")
    async def test_stdio_transport_connect(self, mock_exit_stack, mock_stdio_client):
        """Test stdio transport initialization with correct parameters."""
        mock_exit_stack_instance = AsyncMock()
        mock_exit_stack.return_value = mock_exit_stack_instance

        mock_read = AsyncMock(__aiter__=MagicMock(return_value=iter([])))
        mock_write = AsyncMock(__aiter__=MagicMock(return_value=iter([])))

        # The code does: transport_cm = enter_async_context(...) then await transport_cm.
        # We need enter_async_context to be a coroutine function so that
        # calling it returns a coroutine, and awaiting it gives us (read, write).
        # Use object.__setattr__ to bypass MagicMock.__setattr__ which wraps callables.
        async def fake_enter_async_context(*args, **kwargs):  # noqa: RUF029
            return (mock_read, mock_write)

        object.__setattr__(mock_exit_stack_instance, "enter_async_context", fake_enter_async_context)

        transport = StdioTransport(
            command="python",
            args=["-m", "my_server"],
            env={"MY_ENV": "value"},
        )
        await transport.connect()

        # Verify stdio_client was called with correct params
        mock_stdio_client.assert_called_once()
        server_params = mock_stdio_client.call_args.args[0]
        assert server_params.command == "python"
        assert server_params.args == ["-m", "my_server"]
        assert server_params.env == {"MY_ENV": "value"}
        assert transport.is_connected is True

    @patch("mcp.client.stdio.stdio_client")
    async def test_stdio_transport_disconnect(self, mock_stdio_client):
        """Test stdio transport disconnect."""
        mock_transport_cm = AsyncMock()
        mock_stdio_client.return_value = mock_transport_cm

        mock_read = AsyncMock(__aiter__=MagicMock(return_value=iter([])))
        mock_write = AsyncMock(__aiter__=MagicMock(return_value=iter([])))
        mock_transport_cm.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))

        transport = StdioTransport(command="python")
        await transport.connect()
        await transport.disconnect()

        assert transport.is_connected is False

    async def test_stdio_transport_send_not_connected(self):
        """Test send raises error when not connected."""
        transport = StdioTransport(command="python")
        # Send before connect should raise ConnectionError
        with pytest.raises(ConnectionError):
            # Just need any call to send() on a non-connected transport
            await transport.send(MagicMock())

    def test_stdio_transport_default_args(self):
        """Test stdio transport with default args and env."""
        transport = StdioTransport(command="node")
        assert transport._args == []
        assert transport._env is None


class TestSSETransport:
    """Tests for SSETransport."""

    @patch("mcp.client.sse.sse_client")
    async def test_sse_transport_connect(self, mock_sse_client):
        """Test SSE transport initialization."""
        mock_transport_cm = AsyncMock()
        mock_sse_client.return_value = mock_transport_cm

        mock_read = AsyncMock(__aiter__=MagicMock(return_value=iter([])))
        mock_write = AsyncMock(__aiter__=MagicMock(return_value=iter([])))
        mock_transport_cm.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))

        transport = SSETransport(
            url="http://localhost:8080/mcp",
            headers={"X-Custom": "header"},
            timeout=10.0,
            sse_read_timeout=600.0,
        )
        await transport.connect()

        mock_sse_client.assert_called_once()
        call_kwargs = mock_sse_client.call_args.kwargs
        assert call_kwargs["url"] == "http://localhost:8080/mcp"
        assert call_kwargs["headers"] == {"X-Custom": "header"}
        assert call_kwargs["timeout"] == 10.0
        assert call_kwargs["sse_read_timeout"] == 600.0
        assert transport.is_connected is True

    @patch("mcp.client.sse.sse_client")
    async def test_sse_transport_disconnect(self, mock_sse_client):
        """Test SSE transport disconnect."""
        mock_transport_cm = AsyncMock()
        mock_sse_client.return_value = mock_transport_cm

        mock_read = AsyncMock(__aiter__=MagicMock(return_value=iter([])))
        mock_write = AsyncMock(__aiter__=MagicMock(return_value=iter([])))
        mock_transport_cm.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))

        transport = SSETransport(url="http://localhost:8080/mcp")
        await transport.connect()
        await transport.disconnect()

        assert transport.is_connected is False


class TestStreamableHTTPTransport:
    """Tests for StreamableHTTPTransport."""

    @patch("mcp.client.streamable_http.streamable_http_client")
    async def test_streamable_http_connect(self, mock_client):
        """Test Streamable HTTP transport initialization."""
        mock_stream_result = MagicMock()
        mock_client.return_value.__aenter__.return_value = mock_stream_result

        mock_read = AsyncMock(__aiter__=MagicMock(return_value=iter([])))
        mock_write = AsyncMock(__aiter__=MagicMock(return_value=iter([])))
        mock_session_id_getter = MagicMock()
        mock_stream_result.__iter__ = MagicMock(return_value=iter([mock_read, mock_write, mock_session_id_getter]))
        mock_stream_result.__getitem__ = MagicMock(side_effect=lambda i: [mock_read, mock_write, mock_session_id_getter][i])

        transport = StreamableHTTPTransport(
            url="http://localhost:8000/mcp",
            headers={"Authorization": "Bearer token"},
            timeout=15.0,
        )
        await transport.connect()

        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args.kwargs
        assert call_kwargs["url"] == "http://localhost:8000/mcp"
        # Verify the http_client was created with correct headers and timeout
        http_client = call_kwargs["http_client"]
        assert http_client.timeout.connect == 15.0
        assert transport.is_connected is True

    @patch("mcp.client.streamable_http.streamable_http_client")
    async def test_streamable_http_disconnect(self, mock_client):
        """Test Streamable HTTP transport disconnect."""
        mock_stream_result = MagicMock()
        mock_client.return_value.__aenter__.return_value = mock_stream_result

        mock_read = AsyncMock(__aiter__=MagicMock(return_value=iter([])))
        mock_write = AsyncMock(__aiter__=MagicMock(return_value=iter([])))
        mock_session_id_getter = MagicMock()
        mock_stream_result.__iter__ = MagicMock(return_value=iter([mock_read, mock_write, mock_session_id_getter]))
        mock_stream_result.__getitem__ = MagicMock(side_effect=lambda i: [mock_read, mock_write, mock_session_id_getter][i])

        transport = StreamableHTTPTransport(url="http://localhost:8000/mcp")
        await transport.connect()
        await transport.disconnect()

        assert transport.is_connected is False
