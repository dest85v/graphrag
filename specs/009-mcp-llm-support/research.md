# Research: MCP Support in graphrag-llm

**Date**: 2026-04-18
**Feature**: 009-mcp-llm-support

---

## Research Tasks

### 1. MCP Python SDK API Surface

**Decision**: Use `mcp>=1.0.0` (v1.x branch) as the primary SDK

**Rationale**: The official MCP Python SDK (modelcontextprotocol/python-sdk) provides:
- `mcp.client.stdio.stdio_client(server_params)` — async context manager yielding `(read_stream, write_stream)` for stdio transport
- `mcp.client.sse.sse_client(url, headers, timeout, sse_read_timeout)` — async context manager yielding `(read_stream, write_stream)` for SSE transport
- `mcp.ClientSession(read_stream, write_stream)` — high-level client session for protocol communication
- `session.initialize()` — protocol handshake (JSON-RPC `initialize` method)
- `await session.list_tools()` — returns `ListToolsResult` with `.tools` list
- `await session.call_tool(name, arguments)` — returns `CallToolResult` with `.content` list
- `mcp.StdioServerParameters(command, args, env)` — stdio server configuration
- `contextlib.AsyncExitStack` — for lifecycle management of multiple transports

The v2 branch (main) is pre-alpha and should be avoided.

**Alternatives considered**:
- Writing a raw JSON-RPC 2.0 client — unnecessary duplication; SDK handles all protocol details
- Using a third-party MCP client — the official SDK is the reference implementation and has 22k+ GitHub stars

### 2. SSE Transport: Old HTTP+SSE vs New Streamable HTTP

**Decision**: Support both Streamable HTTP (v2025-06-18 spec) and HTTP+SSE (v2024-11-05 spec)

**Rationale**: The MCP spec evolved from HTTP+SSE (deprecated in 2025-03-26, removed in 2025-06-18) to Streamable HTTP. The SDK's `sse_client()` implements the old HTTP+SSE transport. However, the SDK also provides `mcp.client.streamable_http.streamable_http_client()` for the new transport.

Implementation: Detect the transport type in config (`sse` vs `streamable_http`) and use the appropriate SDK client. For backward compatibility with existing MCP servers, `sse` should use the HTTP+SSE transport.

**Alternatives considered**:
- Only Streamable HTTP — would break compatibility with servers using the older transport
- Only HTTP+SSE — would be deprecated and lose resumability features

### 3. Middleware Integration Strategy

**Decision**: Add MCP middleware to the `with_middleware_pipeline` chain, BEFORE `with_cache` and AFTER `with_retries`

**Rationale**: The pipeline order in `with_middleware_pipeline.py` is:
1. `with_errors_for_testing`
2. `with_metrics`
3. `with_rate_limiting`
4. `with_retries`
5. `with_cache`
6. `with_request_count`
7. `with_logging`

MCP middleware should be inserted between `with_retries` and `with_cache` because:
- It should be retried on transient MCP server failures (before retries phase)
- It should NOT be cached — MCP tool results may be side-effectful and should not be served from cache
- It should be logged like other middleware steps

The middleware works as a wrapper around the completion function:
1. On first call: initialize MCP client, discover tools
2. On completion call: if response contains tool_calls → invoke via MCP client → append tool_result messages → recurse
3. On disposal: close MCP client, terminate subprocesses

**Alternatives considered**:
- Modifying OpenAICompletion directly — would tightly couple MCP to OpenAI; middleware is more composable
- Creating a separate MCPCompletion class — duplicative; middleware approach reuses existing OpenAICompletion
- Post-processing (after the LLM returns) — too late; we need to intercept the tool_calls in the response

### 4. MCP Client Lifecycle in Middleware

**Decision**: MCPClient is created once per middleware instantiation and lives for the duration of the LLMCompletion instance

**Rationale**: MCP connections (especially stdio subprocesses) are expensive to establish. The middleware should:
1. Create MCPClient on `__init__` of the middleware wrapper
2. Call `initialize()` + `list_tools()` lazily on first completion call (to avoid blocking init)
3. Cache the discovered tools for subsequent calls
4. Close client on `__del__` or via `async with` pattern

For stdio transport: the subprocess must remain alive for the entire middleware lifetime. The `AsyncExitStack` from the SDK manages this.

**Alternatives considered**:
- Per-call MCP client creation — too slow; each subprocess launch takes 1-3 seconds
- Singleton pattern — would break in multi-user scenarios; per-middleware-instance is correct
- Eager initialization — would slow down LLMCompletion creation; lazy is better

### 5. Tool Call Result Format

**Decision**: MCP tool results (text content) are formatted as `tool_result` messages with the tool call id from the LLM response

**Rationale**: MCP's `CallToolResult` returns a list of content objects (each with `type` and `text`/`image`/`annotation`). For v1, we only support `type="text"` content. The result text is joined with newlines and placed into a `tool_result` message:

```python
{
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": "\n".join(text for content in result.content if content.type == "text" for text in [content.text] if text)
}
```

MCP tool errors (`result.isError == True`) are treated the same way — the text is sent back as a tool result, allowing the LLM to recover.

**Alternatives considered**:
- Binary/image content support — out of scope for v1; MCP can return images but LLM tool result format doesn't support them
- Structured MCP results — MCP can return structured data but we'd need to serialize it to text for the LLM

### 6. Tool Call Execution: Sequential vs Parallel

**Decision**: Execute tool calls sequentially in v1; add parallel support as an optimization

**Rationale**: Sequential execution:
- Simpler to implement
- Avoids race conditions on shared MCP session state
- MCP servers may not support parallel tool calls
- Most real-world scenarios involve dependent tool calls

The middleware iterates through `tool_calls` in order, executing each, collecting results, then resuming the LLM call.

**Alternatives considered**:
- Parallel execution with `asyncio.gather` — useful for independent tools, but adds complexity
- User-configurable — could add a `parallel_tool_calls` config option later

### 7. Configuration: Per-Launch vs Global

**Decision**: MCP configuration is passed per-completion-call via `mcp_config` kwarg (similar to how `tools` is passed)

**Rationale**: The existing completion API accepts `tools: list[Tool] | None`. MCP tools are discovered at runtime, not passed directly. The middleware needs a way to know which MCP server to connect to:

Option A: MCP config in ModelConfig (global, per-model)
- Pros: Simple, no API changes
- Cons: Only one MCP server per model; not flexible for multi-server scenarios

Option B: MCP config in completion kwargs (per-call)
- Pros: Flexible; different calls can use different servers
- Cons: Requires changes to how kwargs flow through the pipeline

Decision: Use ModelConfig extra fields (Option A) for v1. MCPConfig is stored in `model_config.model_extra` under a reserved key `"mcp_config"`. This is consistent with how `failure_rate_for_testing` is handled. Future versions can support multiple servers or per-call config.

### 8. Error Handling Strategy

**Decision**: MCP errors are returned as tool result messages; connection errors raise exceptions

**Rationale**:
- **Tool execution errors** (server returns `isError=True`): Format as text tool result → LLM can recover
- **Unknown tool name** (LLM hallucinates): Return error tool result listing available tools
- **Connection errors** (server down, timeout): Raise `MCPConnectionError` — cannot recover, LLM needs to know
- **Timeout**: Per-call timeout from config (default 30s); raised as `TimeoutError`

---

## Summary of Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| SDK version | mcp>=1.0.0, v1.x branch | Stable, official, well-documented |
| Transports | stdio + HTTP+SSE + Streamable HTTP | Full coverage of MCP transport spec |
| Middleware placement | Between retries and cache | Retriable, not cachable |
| Client lifecycle | One per middleware, lazy init | Avoid per-call overhead |
| Tool results | Text, formatted as tool_result messages | Compatible with OpenAI tool calling |
| Parallel tools | Sequential in v1 | Simplicity, avoids race conditions |
| Config location | ModelConfig extra fields | Consistent with existing pattern |
| Error handling | Tool errors → results; connection errors → exceptions | LLM recovery vs hard failures |
