# Implementation Plan: MCP Support in graphrag-llm

**Branch**: `009-mcp-llm-support` | **Date**: 2026-04-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-mcp-llm-support/spec.md`

## Summary

Add MCP (Model Context Protocol) support to the `graphrag-llm` package, enabling the LLM completion pipeline to discover and invoke external tools from MCP servers during chat completions. The implementation adds three transport types (stdio, SSE, Streamable HTTP), an MCP client for server communication, and a middleware component that intercepts LLM tool calls, delegates them to the MCP server, and feeds results back to the LLM. The feature is fully optional — removing MCP configuration reverts to standard LLM-only behavior.

## Technical Context

**Language/Version**: Python 3.11–3.13 (per workspace `requires-python = ">=3.11,<3.14"`)  
**Primary Dependencies**: `mcp>=1.0.0` (official MCP Python SDK, v1.x branch), `anyio`, `httpx`, `httpx-sse` (transitive from `mcp`)  
**Storage**: N/A (no persistent storage; runtime-only)  
**Testing**: `pytest` with `asyncio_mode = "auto"`, 1000s default timeout; unit tests in `tests/unit/`, integration tests in `tests/integration/`  
**Target Platform**: Linux server (primary), macOS/Windows (development)  
**Project Type**: Python library (monorepo package `graphrag-llm`)  
**Performance Goals**: Tool discovery within 5 seconds of first call (SC-001); end-to-end MCP tool calling within 10 seconds for simple tools (SC-002)  
**Constraints**: Tool call results limited to text output (binary/data out of scope for v1); MCP subprocess must not be left as orphan; backward compatible — no config = no MCP behavior  
**Scale/Scope**: Single MCP server per model; sequential tool execution in v1; tool schemas up to LLM context window limits

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Library-First Architecture ✅
This feature is implemented entirely within the existing `graphrag-llm` package. It is self-contained, independently testable, and communicates with other packages through the existing `ModelConfig.call_args` mechanism (dict pass-through). No new package is created; all code lives under `graphrag_llm/mcp/`.

### II. CLI Interface ✅
Not applicable — this is an internal library feature. MCP configuration is provided via `ModelConfig.call_args`, which is used by the existing CLI pipeline. No new CLI entry point is needed.

### III. Test-First (NON-NEGOTIABLE) ✅
All implementation tasks will follow the Red-Green-Refactor cycle. Unit tests for transport classes, MCP client, and middleware will be written before implementation. Tests will pass `uv run poe test_unit`.

### IV. Integration Testing ✅
Integration tests will verify MCP client connectivity to a real MCP server (e.g., `@modelcontextprotocol/server-memory` via npx). Cross-package workflows (MCP tools used in GraphRAG indexing) will be validated.

### V. Versioning & Change Management ✅
A `semversioner` PATCH entry will be added before merge, as the feature is backward-compatible (optional feature, no API breaking changes).

### Second Check Post-Design ✅
Post-Phase 1 design review confirms no constitution violations. The feature:
- Stays within `graphrag-llm` package (library-first)
- Uses existing configuration patterns (`call_args` pass-through)
- Is fully optional (backward compatible)
- No new CLI entry point needed

## Project Structure

### Documentation (this feature)

```text
specs/009-mcp-llm-support/
├── plan.md              # This file
├── research.md          # Phase 0 output — research findings and decisions
├── data-model.md        # Phase 1 output — entity models and relationships
├── quickstart.md        # Phase 1 output — usage examples
├── contracts/           # Phase 1 output — configuration contract
│   └── mcp-config.md    # MCPConfig schema contract for ModelConfig
└── tasks.md             # Phase 2 output (not created by /speckit.plan)
```

### Source Code (repository root)

```text
packages/graphrag-llm/graphrag_llm/
├── mcp/                          # NEW: MCP module
│   ├── __init__.py               # Public exports: MCPClient, MCPTool, etc.
│   ├── types.py                  # MCPTool dataclass, MCPTransportType enum
│   ├── transport.py              # MCPTransport ABC, StdioTransport, SSETransport, StreamableHTTPTransport
│   ├── client.py                 # MCPClient — connection management, tool discovery, invocation
│   └── middleware.py             # MCPCompletionMiddleware — wraps completion, handles tool cycle
├── config/
│   ├── __init__.py               # Export MCPConfig (added)
│   └── mcp_config.py             # NEW: MCPConfig, MCPStdioConfig, MCPSSEConfig, MCPStreamableHTTPConfig
├── completion/
│   └── completion_factory.py     # MODIFIED: Pass mcp_config to middleware
└── middleware/
    └── with_middleware_pipeline.py  # MODIFIED: Add mcp_middleware step
```

**Test files**:
```text
tests/unit/mcp/
├── test_types.py
├── test_transport.py
├── test_client.py
└── test_middleware.py

tests/integration/mcp/
├── test_stdio_transport.py       # Real stdio MCP server
├── test_middleware_tool_call.py  # End-to-end LLM → MCP tool → LLM response
└── test_graceful_shutdown.py     # Subprocess termination
```

**Configuration**:
```text
packages/graphrag-llm/pyproject.toml  # MODIFIED: Add mcp>=1.0.0 to [project.optional-dependencies]
```

**Structure Decision**: The feature is implemented as a new `mcp/` subpackage within `graphrag-llm`, following the existing package layout convention (e.g., `middleware/`, `retry/`, `rate_limit/`). The middleware pattern is reused — MCP integration is a middleware wrapper around the completion function, consistent with existing middleware (cache, retries, rate limiting, metrics). Configuration uses the existing `call_args` pass-through pattern.

## Complexity Tracking

> No constitution violations — all gates passed.
