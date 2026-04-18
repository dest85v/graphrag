# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for MCPClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from graphrag_llm.config.mcp_config import (
    MCPConfig,
    MCPSSEConfig,
    MCPStdioConfig,
    MCPStreamableHTTPConfig,
)
from graphrag_llm.mcp.client import (
    MCPClient,
    MCPConnectionError,
    MCPState,
    MCPToolError,
    _create_transport,
)
from graphrag_llm.mcp.types import MCPTool


class TestCreateTransport:
    """Tests for _create_transport helper."""

    def test_stdio_transport_creation(self):
        """Test stdio transport is created from config."""
        from graphrag_llm.mcp.transport import StdioTransport

        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python", args=["-m", "server"]),
        )
        transport = _create_transport(config)
        assert isinstance(transport, StdioTransport)
        assert transport._command == "python"
        assert transport._args == ["-m", "server"]

    def test_sse_transport_creation(self):
        """Test SSE transport is created from config."""
        from graphrag_llm.mcp.transport import SSETransport

        config = MCPConfig(
            transport_type="sse",
            sse=MCPSSEConfig(url="http://localhost:8080/mcp"),
        )
        transport = _create_transport(config)
        assert isinstance(transport, SSETransport)
        assert transport._url == "http://localhost:8080/mcp"

    def test_streamable_http_transport_creation(self):
        """Test Streamable HTTP transport is created from config."""
        from graphrag_llm.mcp.transport import StreamableHTTPTransport

        config = MCPConfig(
            transport_type="streamable_http",
            streamable_http=MCPStreamableHTTPConfig(url="http://localhost:8000/mcp"),
        )
        transport = _create_transport(config)
        assert isinstance(transport, StreamableHTTPTransport)
        assert transport._url == "http://localhost:8000/mcp"

    def test_unknown_transport_type(self):
        """Test unknown transport type raises ValueError."""
        config = MCPConfig.model_construct(transport_type="websocket")  # type: ignore[arg-type]
        # This bypasses pydantic validation to test the helper function directly
        with pytest.raises(ValueError, match="Unknown transport type"):
            _create_transport(config)


class TestMCPClientInitialization:
    """Tests for MCPClient initialization."""

    def test_client_initial_state(self):
        """Test client starts in DISCONNECTED state."""
        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        assert client.state == MCPState.DISCONNECTED
        assert not client.is_connected
        assert client.tools == []

    def test_client_repr(self):
        """Test client string representation."""
        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        repr_str = repr(client)
        assert "MCPClient" in repr_str
        assert "DISCONNECTED" in repr_str


class TestMCPClientConnect:
    """Tests for MCPClient connection."""

    @patch("mcp.ClientSession")
    @patch("graphrag_llm.mcp.client._create_transport")
    async def test_connect_creates_session(
        self, mock_create_transport, mock_client_session,
    ):
        """Test connect creates a ClientSession."""
        # Setup
        mock_transport = MagicMock()
        mock_create_transport.return_value = mock_transport
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_client_session.return_value = mock_session

        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)

        # Patch transport methods - _read_stream and _write_stream must be
        # proper async iterables so the mcp ClientSession can iterate them.
        mock_transport.connect = AsyncMock()

        async def _async_iter():  # noqa: RUF029
            return
            yield

        mock_transport._read_stream = _async_iter()
        mock_transport._write_stream = _async_iter()

        await client.connect()

        mock_transport.connect.assert_called_once()
        mock_client_session.assert_called_once()

    async def test_connect_closed_client(self):
        """Test connect raises error on closed client."""
        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        client._state = MCPState.CLOSED

        with pytest.raises(MCPConnectionError, match="closed"):
            await client.connect()


class TestMCPClientInitialize:
    """Tests for MCPClient.initialize()."""

    async def test_initialize_success(self):
        """Test successful initialization."""
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()

        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        client._session = mock_session
        client._transport = MagicMock()

        await client.initialize()

        mock_session.initialize.assert_called_once()
        assert client._initialized is True
        assert client.state == MCPState.INITIALIZED

    async def test_initialize_no_session(self):
        """Test initialize raises error without session."""
        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)

        with pytest.raises(MCPConnectionError, match="Not connected"):
            await client.initialize()


class TestMCPClientListTools:
    """Tests for MCPClient.list_tools()."""

    async def test_list_tools_returns_tools(self):
        """Test list_tools returns list of MCPTool objects."""
        # Create mock tools
        mock_mcp_tool1 = MagicMock()
        mock_mcp_tool1.name = "tool1"
        mock_mcp_tool1.description = "First tool"
        mock_mcp_tool1.inputSchema = {
            "type": "object",
            "properties": {"x": {"type": "string"}},
        }

        mock_mcp_tool2 = MagicMock()
        mock_mcp_tool2.name = "tool2"
        mock_mcp_tool2.description = "Second tool"
        mock_mcp_tool2.inputSchema = {}

        mock_result = MagicMock()
        mock_result.tools = [mock_mcp_tool1, mock_mcp_tool2]

        mock_session = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=mock_result)

        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        client._session = mock_session
        client._initialized = True

        tools = await client.list_tools()

        assert len(tools) == 2
        assert tools[0].name == "tool1"
        assert tools[1].name == "tool2"
        assert isinstance(tools[0], MCPTool)

    async def test_list_tools_caches_results(self):
        """Test list_tools caches results for subsequent calls."""
        mock_mcp_tool = MagicMock()
        mock_mcp_tool.name = "cached"
        mock_mcp_tool.description = "Cached tool"
        mock_mcp_tool.inputSchema = {}

        mock_result = MagicMock()
        mock_result.tools = [mock_mcp_tool]

        mock_session = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=mock_result)

        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        client._session = mock_session
        client._initialized = True
        client._tools = []

        tools1 = await client.list_tools()
        tools2 = await client.list_tools()

        # list_tools should return cached results on second call
        mock_session.list_tools.assert_called_once()
        assert tools1 is tools2  # Same list object

    async def test_list_tools_no_session(self):
        """Test list_tools raises error without session."""
        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)

        with pytest.raises(MCPConnectionError):
            await client.list_tools()


class TestMCPClientCallTool:
    """Tests for MCPClient.call_tool()."""

    async def test_call_tool_success(self):
        """Test successful tool call returns text."""
        mock_content = MagicMock()
        mock_content.type = "text"
        mock_content.text = "Result text"

        mock_result = MagicMock()
        mock_result.content = [mock_content]
        mock_result.isError = False

        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        client._session = mock_session
        client._tools = [MCPTool(name="test_tool", description="Test")]

        result = await client.call_tool("test_tool", {"arg": "value"})

        assert result == "Result text"
        mock_session.call_tool.assert_called_once_with(
            name="test_tool", arguments={"arg": "value"},
        )

    async def test_call_tool_unknown_name(self):
        """Test call_tool raises error for unknown tool name."""
        mock_session = AsyncMock()

        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        client._session = mock_session
        client._tools = [
            MCPTool(name="tool_a", description="A"),
            MCPTool(name="tool_b", description="B"),
        ]

        with pytest.raises(MCPToolError, match="not found"):
            await client.call_tool("nonexistent")

    async def test_call_tool_no_tools_discovered(self):
        """Test call_tool raises error when no tools discovered."""
        mock_session = AsyncMock()

        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        client._session = mock_session

        with pytest.raises(MCPToolError, match=r"[Nn]o tools discovered"):
            await client.call_tool("any_tool")

    async def test_call_tool_error_result(self):
        """Test call_tool handles server error responses."""
        mock_content = MagicMock()
        mock_content.text = "Something went wrong"

        mock_result = MagicMock()
        mock_result.content = [mock_content]
        mock_result.isError = True

        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        client._session = mock_session
        client._tools = [MCPTool(name="failing_tool", description="Fail")]

        with pytest.raises(MCPToolError, match="Something went wrong"):
            await client.call_tool("failing_tool")


class TestMCPClientDisconnect:
    """Tests for MCPClient.disconnect()."""

    async def test_disconnect_cleans_up(self):
        """Test disconnect sets state to CLOSED and cleans transport."""
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

        mock_transport.disconnect.assert_called_once()
        assert client.state == MCPState.CLOSED
        assert client._disconnected is True

    async def test_disconnect_idempotent(self):
        """Test disconnect can be called multiple times safely."""
        mock_transport = MagicMock()
        mock_transport.disconnect = AsyncMock()

        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        client = MCPClient(config)
        client._transport = mock_transport

        await client.disconnect()
        await client.disconnect()  # Should not raise

        assert client.state == MCPState.CLOSED


class TestMCPClientContextManager:
    """Tests for MCPClient async context manager."""

    @patch("graphrag_llm.mcp.client._create_transport")
    async def test_async_context_manager(self, mock_create_transport):
        """Test MCPClient as async context manager."""
        mock_transport = MagicMock()
        mock_transport.connect = AsyncMock()
        mock_transport.disconnect = AsyncMock()

        # Provide empty async iterables for read/write streams.
        async def _empty_async_iter():  # noqa: RUF029
            return
            yield  # type: ignore[unreachable]

        mock_transport._read_stream = _empty_async_iter()
        mock_transport._write_stream = _empty_async_iter()
        mock_create_transport.return_value = mock_transport

        # Patch BaseSession.__aenter__ to avoid the real mcp library
        # trying to iterate over our empty async generators.
        from mcp.shared.session import BaseSession

        with patch.object(
            BaseSession, "__aenter__", new=AsyncMock(return_value=MagicMock()),
        ):
            config = MCPConfig(
                transport_type="stdio",
                stdio=MCPStdioConfig(command="python"),
            )

            async with MCPClient(config) as client:
                await client.connect()
                assert client.is_connected

            assert client.state == MCPState.CLOSED


class TestMCPClientFactory:
    """Tests for create_mcp_client factory pattern."""

    def test_create_transport_stdio(self):
        """Test transport creation for stdio config."""
        from graphrag_llm.mcp.transport import StdioTransport

        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python", args=["-m", "server"]),
        )
        transport = _create_transport(config)
        assert isinstance(transport, StdioTransport)
        assert transport._command == "python"

    def test_create_transport_sse(self):
        """Test transport creation for SSE config."""
        from graphrag_llm.mcp.transport import SSETransport

        config = MCPConfig(
            transport_type="sse",
            sse=MCPSSEConfig(url="http://localhost:8080/mcp"),
        )
        transport = _create_transport(config)
        assert isinstance(transport, SSETransport)
        assert transport._url == "http://localhost:8080/mcp"

    def test_create_transport_streamable_http(self):
        """Test transport creation for streamable_http config."""
        from graphrag_llm.mcp.transport import StreamableHTTPTransport

        config = MCPConfig(
            transport_type="streamable_http",
            streamable_http=MCPStreamableHTTPConfig(url="http://localhost:8000/mcp"),
        )
        transport = _create_transport(config)
        assert isinstance(transport, StreamableHTTPTransport)
        assert transport._url == "http://localhost:8000/mcp"
