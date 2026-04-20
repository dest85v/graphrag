# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for MCP config models."""

import pytest
from graphrag_llm.config.mcp_config import (
    MCPConfig,
    MCPSSEConfig,
    MCPStdioConfig,
    MCPStreamableHTTPConfig,
)
from pydantic import ValidationError


class TestMCPStdioConfig:
    """Tests for MCPStdioConfig."""

    def test_stdio_config_minimal(self):
        """Test stdio config with only required command."""
        config = MCPStdioConfig(command="python")
        assert config.command == "python"
        assert config.args == []
        assert config.env is None

    def test_stdio_config_full(self):
        """Test stdio config with all fields."""
        config = MCPStdioConfig(
            command="python",
            args=["-m", "mcp_server"],
            env={"MY_VAR": "value"},
        )
        assert config.command == "python"
        assert config.args == ["-m", "mcp_server"]
        assert config.env == {"MY_VAR": "value"}


class TestMCPSSEConfig:
    """Tests for MCPSSEConfig."""

    def test_sse_config_defaults(self):
        """Test SSE config with defaults."""
        config = MCPSSEConfig(url="http://localhost:8080/mcp")
        assert config.url == "http://localhost:8080/mcp"
        assert config.headers == {}
        assert config.timeout == 5.0
        assert config.sse_read_timeout == 300.0

    def test_sse_config_custom(self):
        """Test SSE config with custom values."""
        config = MCPSSEConfig(
            url="http://localhost:8080/mcp",
            headers={"Authorization": "Bearer token"},
            timeout=10.0,
            sse_read_timeout=600.0,
        )
        assert config.timeout == 10.0
        assert config.sse_read_timeout == 600.0

    def test_sse_config_invalid_timeout(self):
        """Test SSE config with invalid timeout (zero)."""
        with pytest.raises(ValidationError):
            MCPSSEConfig(url="http://localhost:8080/mcp", timeout=0.0)


class TestMCPStreamableHTTPConfig:
    """Tests for MCPStreamableHTTPConfig."""

    def test_streamable_http_config_defaults(self):
        """Test streamable HTTP config with defaults."""
        config = MCPStreamableHTTPConfig(url="http://localhost:8000/mcp")
        assert config.url == "http://localhost:8000/mcp"
        assert config.headers == {}
        assert config.timeout == 5.0

    def test_streamable_http_config_invalid_timeout(self):
        """Test streamable HTTP config with invalid timeout."""
        with pytest.raises(ValidationError):
            MCPStreamableHTTPConfig(url="http://localhost:8000/mcp", timeout=-1.0)


class TestMCPConfig:
    """Tests for MCPConfig."""

    def test_mcp_config_stdio(self):
        """Test stdio transport config."""
        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python", args=["-m", "server"]),
        )
        assert config.transport_type == "stdio"
        assert config.stdio is not None
        assert config.stdio.command == "python"

    def test_mcp_config_sse(self):
        """Test SSE transport config."""
        config = MCPConfig(
            transport_type="sse",
            sse=MCPSSEConfig(url="http://localhost:8080/mcp"),
        )
        assert config.transport_type == "sse"
        assert config.sse is not None
        assert config.sse.url == "http://localhost:8080/mcp"

    def test_mcp_config_streamable_http(self):
        """Test streamable HTTP transport config."""
        config = MCPConfig(
            transport_type="streamable_http",
            streamable_http=MCPStreamableHTTPConfig(url="http://localhost:8000/mcp"),
        )
        assert config.transport_type == "streamable_http"
        assert config.streamable_http is not None

    def test_mcp_config_stdio_missing_config(self):
        """Test stdio transport without config raises error."""
        with pytest.raises(ValidationError) as exc_info:
            MCPConfig(transport_type="stdio")
        assert "stdio" in str(exc_info.value).lower()

    def test_mcp_config_sse_missing_config(self):
        """Test SSE transport without config raises error."""
        with pytest.raises(ValidationError) as exc_info:
            MCPConfig(transport_type="sse")
        assert "sse" in str(exc_info.value).lower()

    def test_mcp_config_streamable_http_missing_config(self):
        """Test streamable HTTP without config raises error."""
        with pytest.raises(ValidationError) as exc_info:
            MCPConfig(transport_type="streamable_http")
        assert "streamable_http" in str(exc_info.value).lower()

    def test_mcp_config_default_timeouts(self):
        """Test default timeout values."""
        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
        )
        assert config.init_timeout == 30.0
        assert config.tool_timeout == 30.0

    def test_mcp_config_custom_timeouts(self):
        """Test custom timeout values."""
        config = MCPConfig(
            transport_type="stdio",
            stdio=MCPStdioConfig(command="python"),
            init_timeout=60.0,
            tool_timeout=10.0,
        )
        assert config.init_timeout == 60.0
        assert config.tool_timeout == 10.0

    def test_mcp_config_invalid_init_timeout(self):
        """Test invalid init_timeout (zero)."""
        with pytest.raises(ValidationError):
            MCPConfig(
                transport_type="stdio",
                stdio=MCPStdioConfig(command="python"),
                init_timeout=0.0,
            )

    def test_mcp_config_invalid_tool_timeout(self):
        """Test invalid tool_timeout (zero)."""
        with pytest.raises(ValidationError):
            MCPConfig(
                transport_type="stdio",
                stdio=MCPStdioConfig(command="python"),
                tool_timeout=0.0,
            )

    def test_mcp_config_extra_fields_rejected(self):
        """Test that extra config fields are rejected."""
        with pytest.raises(ValidationError):
            MCPConfig(
                transport_type="stdio",
                stdio=MCPStdioConfig(command="python"),
                invalid_field="should_fail",  # type: ignore[call-arg]
            )
