# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""MCP configuration models for graphrag-llm."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MCPStdioConfig(BaseModel):
    """Configuration for stdio transport (subprocess-based)."""

    model_config = ConfigDict(extra="forbid")

    command: str = Field(
        description="Executable to launch (e.g., 'python', 'node').",
    )
    args: list[str] = Field(
        default_factory=list,
        description="Arguments to pass to the executable.",
    )
    env: dict[str, str] | None = Field(
        default=None,
        description="Environment variables for the subprocess. If None, inherits parent process environment.",
    )


class MCPSSEConfig(BaseModel):
    """Configuration for HTTP+SSE transport (legacy MCP transport)."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(
        description="SSE endpoint URL.",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Additional HTTP headers for requests.",
    )
    timeout: float = Field(
        default=5.0,
        ge=0.1,
        description="HTTP timeout for regular operations (seconds).",
    )
    sse_read_timeout: float = Field(
        default=300.0,
        ge=0.1,
        description="SSE read timeout before disconnect (seconds).",
    )


class MCPStreamableHTTPConfig(BaseModel):
    """Configuration for Streamable HTTP transport (current MCP transport)."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(
        description="MCP endpoint URL.",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Additional HTTP headers for requests.",
    )
    timeout: float = Field(
        default=5.0,
        ge=0.1,
        description="HTTP timeout for regular operations (seconds).",
    )


class MCPConfig(BaseModel):
    """Configuration for connecting to an MCP server.

    Attributes
    ----------
    transport_type : Literal["stdio", "sse", "streamable_http"]
        The transport protocol to use.
    stdio : MCPStdioConfig | None
        Stdio transport config. Required if transport_type == "stdio".
    sse : MCPSSEConfig | None
        SSE transport config. Required if transport_type == "sse".
    streamable_http : MCPStreamableHTTPConfig | None
        Streamable HTTP transport config. Required if transport_type == "streamable_http".
    init_timeout : float
        Seconds to wait for MCP server initialization handshake. Default 30.0.
    tool_timeout : float
        Seconds to wait for individual tool call execution. Default 30.0.
    """

    model_config = ConfigDict(extra="forbid")

    transport_type: Literal["stdio", "sse", "streamable_http"] = Field(
        description="Transport protocol to use: 'stdio', 'sse', or 'streamable_http'.",
    )
    stdio: MCPStdioConfig | None = Field(
        default=None,
        description="Stdio transport configuration. Required if transport_type is 'stdio'.",
    )
    sse: MCPSSEConfig | None = Field(
        default=None,
        description="SSE transport configuration. Required if transport_type is 'sse'.",
    )
    streamable_http: MCPStreamableHTTPConfig | None = Field(
        default=None,
        description="Streamable HTTP transport configuration. Required if transport_type is 'streamable_http'.",
    )
    init_timeout: float = Field(
        default=30.0,
        ge=0.1,
        description="Seconds to wait for MCP server initialization handshake.",
    )
    tool_timeout: float = Field(
        default=30.0,
        ge=0.1,
        description="Seconds to wait for individual tool call execution.",
    )

    @model_validator(mode="after")
    def _validate_transport_config(self) -> MCPConfig:
        """Validate transport-specific config is present."""
        if self.transport_type == "stdio" and self.stdio is None:
            msg = "stdio config is required when transport_type is 'stdio'"
            raise ValueError(msg)
        if self.transport_type == "sse" and self.sse is None:
            msg = "sse config is required when transport_type is 'sse'"
            raise ValueError(msg)
        if self.transport_type == "streamable_http" and self.streamable_http is None:
            msg = "streamable_http config is required when transport_type is 'streamable_http'"
            raise ValueError(msg)
        return self
