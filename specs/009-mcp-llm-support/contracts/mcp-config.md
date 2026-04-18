# Contract: MCP Configuration Schema

**Feature**: 009-mcp-llm-support
**Date**: 2026-04-18

---

## Overview

This contract documents the MCP configuration schema that integrates with the `graphrag-llm` `ModelConfig` via `model_extra` fields. This is the public configuration interface for enabling MCP tool support.

## Configuration Location

MCP configuration is stored in `ModelConfig.call_args` (a `dict[str, Any]`) under the reserved key `"mcp_config"`:

```python
model_config = ModelConfig(
    model_provider="openai",
    model="gpt-4o",
    api_key="sk-...",
    call_args={
        "mcp_config": { ... },  # <-- MCP config lives here
    },
)
```

## Schema: MCPConfig

The top-level configuration object. All fields except `transport_type` are optional.

```jsonc
{
  "mcp_config": {
    "transport_type": "stdio",        // Required: "stdio" | "sse" | "streamable_http"
    "stdio": { ... },                  // Required if transport_type == "stdio"
    "sse": { ... },                    // Required if transport_type == "sse"
    "streamable_http": { ... },        // Required if transport_type == "streamable_http"
    "init_timeout": 30.0,              // Optional: seconds, default 30.0
    "tool_timeout": 30.0               // Optional: seconds, default 30.0
  }
}
```

## Schema: MCPStdioConfig

Used when `transport_type` is `"stdio"`.

```jsonc
{
  "stdio": {
    "command": "python",               // Required: executable path
    "args": ["-m", "my_server"],       // Optional: arguments, default []
    "env": null                        // Optional: env vars dict or null (inherit)
  }
}
```

## Schema: MCPSSEConfig

Used when `transport_type` is `"sse"` (HTTP+SSE transport, deprecated in MCP spec).

```jsonc
{
  "sse": {
    "url": "http://localhost:8080/mcp",  // Required: SSE endpoint URL
    "headers": {},                        // Optional: extra HTTP headers
    "timeout": 5.0,                       // Optional: HTTP timeout, default 5.0
    "sse_read_timeout": 300.0             // Optional: SSE read timeout, default 300.0
  }
}
```

## Schema: MCPStreamableHTTPConfig

Used when `transport_type` is `"streamable_http"` (current MCP transport).

```jsonc
{
  "streamable_http": {
    "url": "http://localhost:8000/mcp",  // Required: MCP endpoint URL
    "headers": {},                        // Optional: extra HTTP headers
    "timeout": 5.0                        // Optional: HTTP timeout, default 5.0
  }
}
```

## Validation Rules

| Rule | Condition | Error |
|------|-----------|-------|
| `transport_type` is one of the allowed values | Must be `"stdio"`, `"sse"`, or `"streamable_http"` | `ValueError` |
| Transport-specific config is present | The corresponding field (`stdio`, `sse`, or `streamable_http`) must be non-null | `ValueError` |
| `command` is present | Required for stdio transport | `ValueError` |
| `url` is present | Required for sse/streamable_http transport | `ValueError` |
| `timeout` values are positive | `init_timeout` and `tool_timeout` must be > 0 | `ValueError` |

## Behavior Contract

### Initialization

1. On first `completion()` call, the middleware checks for `mcp_config` in `call_args`
2. If present:
   - Creates an `MCPClient` with the specified transport
   - Calls `initialize()` on the MCP server (JSON-RPC handshake)
   - Calls `list_tools()` and caches the result
3. If absent: no MCP behavior; standard completion proceeds

### Tool Discovery

- Discovered tools are converted to OpenAI `ChatCompletionTool` format
- Each tool has `type="function"` with `function={name, description, parameters}`
- `parameters` is the MCP tool's `input_schema` (JSON Schema)

### Tool Invocation

- When the LLM returns `tool_calls` in its response:
  1. The middleware routes each call to the MCP server via `call_tool(name, arguments)`
  2. Results are formatted as `tool_result` messages
  3. Messages (including tool results) are sent back to the LLM
  4. The LLM produces the final response
- Tool calls are executed **sequentially** (same order as in LLM response)

### Error Handling

| Error Type | Behavior |
|------------|----------|
| Tool execution error (MCP server returns `isError=true`) | Text result sent back to LLM for recovery |
| Unknown tool name | Error result listing available tools sent to LLM |
| Connection failure | Exception raised; no fallback |
| Timeout | Exception raised; no fallback |

### Backward Compatibility

- If `mcp_config` is absent from `call_args`: behavior is identical to pre-MCP implementation
- No changes to existing `ModelConfig` fields
- No changes to existing `LLMCompletion` API
