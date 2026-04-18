---

description: "Task list for MCP support in graphrag-llm"
---

# Tasks: MCP Support in graphrag-llm

**Input**: Design documents from `/specs/009-mcp-llm-support/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-config.md

**Tests**: Unit and integration tests following the Test-First constitution principle.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create `mcp/` package directory structure in `packages/graphrag-llm/graphrag_llm/mcp/`
- [X] T002 Create `packages/graphrag-llm/graphrag_llm/mcp/__init__.py` with placeholder public exports

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types, configuration models, and transport layer that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Implement `MCPTool` dataclass in `packages/graphrag-llm/graphrag_llm/mcp/types.py` with `name`, `description`, `input_schema` fields and `to_openai_tool()` method that converts to OpenAI `ChatCompletionTool` format (type="function")
- [X] T004 Implement `MCPConfig`, `MCPStdioConfig`, `MCPSSEConfig`, `MCPStreamableHTTPConfig` pydantic models in `packages/graphrag-llm/graphrag_llm/config/mcp_config.py` following the contract in `contracts/mcp-config.md` (validation rules: transport_type enum, conditional required fields, positive timeouts)
- [X] T005 [P] Export `MCPConfig` and related models from `packages/graphrag-llm/graphrag_llm/config/__init__.py`
- [X] T006 Implement `MCPTransport` abstract base class in `packages/graphrag-llm/graphrag_llm/mcp/transport.py` defining async `connect()`, `send()`, `receive()`, `disconnect()` methods using anyio context streams
- [X] T007 [P] Implement `StdioTransport` in `packages/graphrag-llm/graphrag_llm/mcp/transport.py` using `mcp.client.stdio.stdio_client()` — launches subprocess via `mcp.StdioServerParameters`, manages `AsyncExitStack` for lifecycle
- [X] T008 [P] Implement `SSETransport` in `packages/graphrag-llm/graphrag_llm/mcp/transport.py` using `mcp.client.sse.sse_client()` — connects to HTTP SSE endpoint with configurable headers and timeouts
- [X] T009 [P] Implement `StreamableHTTPTransport` in `packages/graphrag-llm/graphrag_llm/mcp/transport.py` using `mcp.client.streamable_http.streamable_http_client()` — connects to Streamable HTTP endpoint
- [X] T010 Update `packages/graphrag-llm/pyproject.toml` — add `mcp>=1.0.0` to `[project.optional-dependencies]` under `mcp` extra group (with `mcp[cli]` for CLI tooling)

**Checkpoint**: Foundation ready — types, config models, all 3 transports, and pyproject.toml updated. User story implementation can now begin.

---

## Phase 3: User Story 1 - Configure and Discover MCP Tools (Priority: P1) 🎯 MVP

**Goal**: Users can configure an MCP server (stdio or SSE) and discover available tools — receiving a structured list with names, descriptions, and input schemas.

**Independent Test**: A user configures an MCP stdio server (command + args), initializes the MCP client, and receives a list of discovered tools with names, descriptions, and JSON Schema input definitions.

### Tests for User Story 1

> **NOTE**: Write these tests FIRST, ensure they FAIL before implementation (Constitution Principle III — Test-First)

- [X] T011 [P] [US1] Unit test for `MCPTool.to_openai_tool()` in `tests/unit/mcp/test_types.py` — verifies MCPTool converts to OpenAI ChatCompletionTool format correctly (name, description, parameters from input_schema)
- [X] T012 [P] [US1] Unit test for `MCPConfig` validation in `tests/unit/mcp/test_config_models.py` — tests transport_type enum, conditional required fields (stdio config required for stdio transport, etc.), positive timeout validation
- [X] T013 [P] [US1] Unit test for `StdioTransport` initialization in `tests/unit/mcp/test_transport.py` — mocks `mcp.client.stdio.stdio_client()` to verify subprocess parameters are passed correctly
- [X] T014 [P] [US1] Unit test for `StdioTransport` send/receive in `tests/unit/mcp/test_transport.py` — mocks async streams to verify JSON-RPC messages are sent and received correctly

### Implementation for User Story 1

- [X] T015 [US1] Implement `MCPClient` class in `packages/graphrag-llm/graphrag_llm/mcp/client.py` with state machine (DISCONNECTED → CONNECTING → INITIALIZED → TOOLS_DISCOVERED → ERROR → CLOSED states), `connect(transport)` method, and `disconnect()` method using `AsyncExitStack` for resource management
- [X] T016 [US1] Implement `MCPClient.initialize()` method in `packages/graphrag-llm/graphrag_llm/mcp/client.py` — calls `session.initialize()` via the MCP SDK, handles timeout per config `init_timeout`
- [X] T017 [US1] Implement `MCPClient.list_tools()` method in `packages/graphrag-llm/graphrag_llm/mcp/client.py` — calls `session.list_tools()`, returns `list[MCPTool]`, caches results for subsequent calls
- [X] T018 [US1] Implement `MCPClient` factory helper in `packages/graphrag-llm/graphrag_llm/mcp/client.py` — `create_mcp_client(config)` that selects transport and returns configured client
- [X] T019 [US1] Unit test for `MCPClient` initialization and tool discovery in `tests/unit/mcp/test_client.py` — mocks MCP SDK `ClientSession` to verify initialize() + list_tools() flow, verifies tool caching behavior

**Checkpoint**: At this point, MCP stdio server connection, initialization, and tool discovery work independently. MVP is deliverable.

---

## Phase 4: User Story 2 - Use MCP Tools in LLM Completions (Priority: P1)

**Goal**: The LLM automatically decides when to invoke MCP tools during completions — the pipeline transparently handles tool discovery, LLM tool choice, tool invocation via MCP server, and result formatting.

**Independent Test**: A user configures MCP tools, sends a completion request with a user message that requires tool use, and receives a final response that incorporates the tool output from the MCP server.

### Tests for User Story 2

> **NOTE**: Write these tests FIRST, ensure they FAIL before implementation (Constitution Principle III — Test-First)

- [X] T020 [P] [US2] Unit test for SSETransport initialization in `tests/unit/mcp/test_transport.py` — mocks `mcp.client.sse.sse_client()` to verify URL, headers, and timeouts
- [X] T021 [P] [US2] Unit test for StreamableHTTPTransport initialization in `tests/unit/mcp/test_transport.py` — mocks `mcp.client.streamable_http.streamable_http_client()` to verify URL and headers
- [X] T022 [P] [US2] Unit test for `MCPClient.call_tool()` in `tests/unit/mcp/test_client.py` — mocks `session.call_tool()` to verify tool invocation with name/arguments, returns CallToolResult content as text
- [X] T023 [P] [US2] Unit test for `MCPClient` error handling in `tests/unit/mcp/test_client.py` — verifies timeout errors, connection errors, and unknown tool errors are raised with descriptive messages

### Implementation for User Story 2

- [X] T024 [US2] Implement `MCPClient.call_tool(name, arguments)` method in `packages/graphrag-llm/graphrag_llm/mcp/client.py` — calls `session.call_tool(name, arguments)`, extracts text content from `CallToolResult`, respects per-call `tool_timeout`, handles `isError` flag
- [X] T025 [US2] Implement `MCPCompletionMiddleware` in `packages/graphrag-llm/graphrag_llm/mcp/middleware.py` — wraps the completion function, intercepts LLM tool_calls, delegates to MCP client, formats results as tool_result messages
- [X] T026 [US2] Implement the middleware tool call cycle in `packages/graphrag-llm/graphrag_llm/mcp/middleware.py` — on completion response with tool_calls: (1) route each call to MCP client via `call_tool()`, (2) format results as `{"role": "tool", "tool_call_id": ..., "content": ...}` messages, (3) recurse with tool results appended to messages
- [X] T027 [US2] Implement lazy MCP client initialization in `packages/graphrag-llm/graphrag_llm/mcp/middleware.py` — MCP client is created and initialized on first `completion()` call (not during middleware `__init__`)
- [X] T028 [US2] Integrate MCP middleware into `packages/graphrag-llm/graphrag_llm/middleware/with_middleware_pipeline.py` — insert MCP step between `with_retries` and `with_cache`, reads MCP config from `model_config.model_extra.get("mcp_config")`, skips if absent
- [X] T029 [US2] Handle LLM-hallucinated tool names in `packages/graphrag-llm/graphrag_llm/mcp/middleware.py` — if tool name not in discovered tools, return error tool result listing available tool names
- [X] T030 [US2] Integration test for middleware tool call cycle in `tests/integration/mcp/test_middleware_tool_call.py` — uses mocked MCP client to verify end-to-end: completion call → tool call discovery → tool invocation → LLM final response

**Checkpoint**: User Stories 1 AND 2 both work independently. The LLM can discover and invoke MCP tools during completions.

---

## Phase 5: User Story 3 - Manage MCP Server Lifecycle and Graceful Shutdown (Priority: P2)

**Goal**: MCP server connections are properly managed — servers are started, kept alive, and cleanly shut down without orphaned processes.

**Independent Test**: A user creates and disposes of an MCP-backed LLM client, and verifies that the MCP subprocess terminates cleanly (no zombie processes).

### Tests for User Story 3

> **NOTE**: Write these tests FIRST, ensure they FAIL before implementation (Constitution Principle III — Test-First)

- [X] T031 [P] [US3] Integration test for stdio subprocess termination in `tests/integration/mcp/test_graceful_shutdown.py` — starts MCP stdio server subprocess, creates client, calls disconnect(), verifies subprocess PID exits cleanly
- [X] T032 [P] [US3] Integration test for connection lost handling in `tests/integration/mcp/test_graceful_shutdown.py` — kills MCP subprocess mid-call, verifies subsequent tool call raises descriptive connection error

### Implementation for User Story 3

- [X] T033 [US3] Implement graceful shutdown in `packages/graphrag-llm/graphrag_llm/mcp/client.py` — `disconnect()` terminates subprocess for stdio transport, closes SSE connections, uses `AsyncExitStack.aclose()` for cleanup
- [X] T034 [US3] Implement subprocess crash detection in `packages/graphrag-llm/graphrag_llm/mcp/client.py` — on tool call, check subprocess is alive; if dead, raise descriptive error instead of hanging
- [X] T035 [US3] Implement middleware disposal cleanup in `packages/graphrag-llm/graphrag_llm/mcp/middleware.py` — add `__del__` or context manager to ensure MCP client is disconnected when middleware is garbage collected

**Checkpoint**: All user stories complete. MCP lifecycle management is production-ready.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T036 [P] Add `__all__` exports to all MCP module `__init__.py` files (`packages/graphrag-llm/graphrag_llm/mcp/__init__.py`, `packages/graphrag-llm/graphrag_llm/config/__init__.py`)
- [X] T037 Run `uv run poe check` (format + lint + typecheck) and fix any issues
- [X] T038 Run `uv run poe test_unit` to verify all unit tests pass
- [X] T039 [P] Add semversioner PATCH entry for the feature: `uv run semversioner add-change -t patch -d "Add MCP (Model Context Protocol) support to graphrag-llm with stdio, SSE, and Streamable HTTP transports."`
- [X] T040 Update `AGENTS.md` in repo root with MCP SDK dependency (already done by update-agent-context script, verify it's correct)
- [X] T041 Validate quickstart.md examples work — ensure all code snippets are syntactically correct
- [X] T042 Add docstrings to all public classes and methods in `packages/graphrag-llm/graphrag_llm/mcp/` following existing project style

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — **BLOCKS all user stories**
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 (Phase 3) and US2 (Phase 4) can proceed in parallel (US2 depends on US1's client foundation)
  - US3 (Phase 5) depends on US1 + US2 completion (lifecycle management for both)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — no dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) — depends on US1's `MCPClient` foundation (client.py T015-T017) before implementing middleware
- **User Story 3 (P2)**: Can start after US1 + US2 — builds on client and middleware lifecycle patterns

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Test-First constitution)
- Models before services
- Services before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T007 (StdioTransport), T008 (SSETransport), T009 (StreamableHTTPTransport) can run in parallel (Phase 2)
- T011-T014 (US1 tests) can run in parallel (Phase 3)
- T020-T023 (US2 tests) can run in parallel (Phase 4)
- T031-T032 (US3 tests) can run in parallel (Phase 5)
- T036-T040 (Polish) can run in parallel where possible

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together:
Task: "Unit test for MCPTool.to_openai_tool() in tests/unit/mcp/test_types.py"
Task: "Unit test for MCPConfig validation in tests/unit/mcp/test_config_models.py"
Task: "Unit test for StdioTransport in tests/unit/mcp/test_transport.py"

# Launch all US1 implementations together after tests fail:
Task: "Implement MCPClient class in packages/graphrag-llm/graphrag_llm/mcp/client.py"
Task: "Implement MCPClient.initialize() in packages/graphrag-llm/graphrag_llm/mcp/client.py"
Task: "Implement MCPClient.list_tools() in packages/graphrag-llm/graphrag_llm/mcp/client.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently — stdio server connects, tools discovered
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (client foundation)
   - Developer B: User Story 2 (middleware, SSE + StreamableHTTP transports)
3. After US1 + US2:
   - Developer C: User Story 3 (lifecycle management)
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (Test-First)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- All code paths to follow existing project patterns (pydantic config, async/await, OpenAI SDK types)
