# Data Model: MCP Support in graphrag-llm

**Date**: 2026-04-18
**Feature**: 009-mcp-llm-support

---

## Entities

### MCPConfig

Declarative configuration for connecting to an MCP server.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `transport_type` | `Literal["stdio", "sse", "streamable_http"]` | Yes | — | Transport protocol to use |
| `stdio` | `MCPStdioConfig \| None` | Conditional | `None` | Stdio transport config (required if `transport_type == "stdio"`) |
| `sse` | `MCPSSEConfig \| None` | Conditional | `None` | SSE transport config (required if `transport_type == "sse"`) |
| `streamable_http` | `MCPSstreamableHTTPConfig \| None` | Conditional | `None` | Streamable HTTP transport config (required if `transport_type == "streamable_http"`) |
| `init_timeout` | `float` | No | `30.0` | Seconds to wait for MCP server initialization handshake |
| `tool_timeout` | `float` | No | `30.0` | Seconds to wait for individual tool call execution |

### MCPStdioConfig

Configuration for stdio transport (subprocess-based).

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `command` | `str` | Yes | — | Executable to launch (e.g., `"python"`, `"node"`) |
| `args` | `list[str]` | No | `[]` | Arguments to pass to the executable |
| `env` | `dict[str, str] \| None` | No | `None` | Environment variables for the subprocess; if `None`, inherits parent process environment |

### MCPSSEConfig

Configuration for HTTP+SSE transport (legacy MCP transport).

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | `str` | Yes | — | SSE endpoint URL |
| `headers` | `dict[str, str]` | No | `{}` | Additional HTTP headers for requests |
| `timeout` | `float` | No | `5.0` | HTTP timeout for regular operations (seconds) |
| `sse_read_timeout` | `float` | No | `300.0` | SSE read timeout before disconnect (seconds) |

### MCPStreamableHTTPConfig

Configuration for Streamable HTTP transport (current MCP transport).

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | `str` | Yes | — | MCP endpoint URL |
| `headers` | `dict[str, str]` | No | `{}` | Additional HTTP headers for requests |
| `timeout` | `float` | No | `5.0` | HTTP timeout for regular operations (seconds) |

### MCPTool

A tool discovered from an MCP server. Immutable representation of the tool schema.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Unique tool name (used for invocation) |
| `description` | `str` | Human-readable description of what the tool does |
| `input_schema` | `dict[str, Any]` | JSON Schema object defining required/optional parameters |

**Relationships**:
- One `MCPTool` per tool discovered from one MCP server
- Referenced by `MCPClient` for tool discovery and invocation
- Converted to OpenAI `Tool` format for LLM tool calling

### MCPClient

Runtime component managing the connection to an MCP server. Not a data model per se, but a state machine.

**States**:
1. `DISCONNECTED` — Initial state; no transport established
2. `CONNECTING` — Transport being established
3. `INITIALIZED` — Handshake complete; capabilities negotiated
4. `TOOLS_DISCOVERED` — `tools/list` completed; tools cached
5. `ERROR` — Connection lost or error occurred
6. `CLOSED` — Clean shutdown

**State Transitions**:
```
DISCONNECTED → CONNECTING → INITIALIZED → TOOLS_DISCOVERED
TOOLS_DISCOVERED → ERROR (on disconnect)
TOOLS_DISCOVERED → CLOSED (on graceful shutdown)
ERROR → DISCONNECTED (on reconnect attempt)
CLOSED → (terminal, no transitions)
```

---

## Configuration Integration

MCPConfig is stored in the `graphrag_llm` configuration system via the `ModelConfig.model_extra` dict under the reserved key `"mcp_config"`.

```
ModelConfig
    └── model_extra: dict
        └── "mcp_config": MCPConfig
```

This is consistent with the existing pattern for `failure_rate_for_testing`.

---

## Tool Discovery and Conversion

The conversion pipeline from MCPTool to OpenAI Tool format:

```
MCPTool (name, description, input_schema)
    → MCPTool.to_openai_tool() 
    → openai.types.chat.ChatCompletionTool (type="function", function={name, description, parameters})
```

The `parameters` field in the OpenAI tool format is directly the `input_schema` from MCP (both are JSON Schema objects).
