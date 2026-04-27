# Feature Specification: Fix Middleware Exception Logging

**Feature Branch**: `001-middleware-exception-logging`  
**Created**: 2026-04-27  
**Status**: Draft  
**Input**: User description: "P1 — Убрать silent exception swallowing в middleware"

## User Scenarios & Testing

### User Story 1 - Developer debugging a failed cache operation (Priority: P1)

A developer needs to troubleshoot why a cached response failed to parse. Currently, the error is logged with `log.exception()` which includes a full stack trace, but the message format could be more actionable. The developer expects to see exactly what failed, the exception type, and a clear indication that the system recovered by falling back to a live request.

**Why this priority**: Cache failures are silent without proper logging. Developers cannot diagnose issues without visibility into what went wrong.

**Independent Test**: Simulate a cache server that returns corrupted data. Verify that the system logs a warning or error with exception details and continues processing without crashing.

**Acceptance Scenarios**:

1. **Given** a cache server returns corrupted/malformed cached response data, **When** the middleware tries to parse it, **Then** a log entry with exception details is written and the request falls through to a live LLM call
2. **Given** a cache connection is unreachable, **When** a cache read operation fails, **Then** a warning is logged and the request proceeds without cache
3. **Given** a cache write operation fails after a successful LLM call, **When** the exception is raised, **Then** a warning is logged and the response is returned to the caller (cache failure does not affect the response)

### User Story 2 - Developer debugging MCP tool call failures (Priority: P1)

A developer using MCP tools needs to understand why a tool invocation failed. The middleware catches MCP-specific errors with good messages, but catches all other exceptions in a broad `except Exception` block that only stores the error string without logging.

**Why this priority**: When MCP tools fail with unexpected errors, developers have no visibility into root cause.

**Independent Test**: Configure an MCP middleware with a broken tool. Verify that all tool call failures (expected and unexpected) produce log entries.

**Acceptance Scenarios**:

1. **Given** an MCP tool returns an `MCPToolError`, **When** the error is caught, **Then** the error message is included in the result AND logged
2. **Given** an MCP tool raises an unexpected exception (not MCPToolError/MCPConnectionError/MCPTimeoutError), **When** the error is caught, **Then** the error is logged with full details AND included in the result

### User Story 3 - Developer debugging global search failures (Priority: P2)

A developer using global search needs to understand why a map response or reduce response failed. The search module already uses `logger.exception()` for both failure paths, but the fallback behavior (returning empty results) could be more clearly documented and tested.

**Why this priority**: Search failures silently return empty results. Operators cannot distinguish between "no relevant data" and "search crashed."

**Independent Test**: Simulate a map response or reduce response failure. Verify that the error is logged and a fallback result is returned.

**Acceptance Scenarios**:

1. **Given** an LLM completion fails during map phase, **When** the exception is caught, **Then** the error is logged and a fallback SearchResult with empty answer is returned
2. **Given** an LLM completion fails during reduce phase, **When** the exception is caught, **Then** the error is logged and an empty SearchResult is returned

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST log all cache-related exceptions with sufficient detail to identify root cause (exception type, message, stack trace)
- **FR-002**: System MUST log all MCP tool call exceptions including both expected (MCP-specific) and unexpected errors
- **FR-003**: System MUST log all search operation exceptions in both map and reduce phases
- **FR-004**: Cache exceptions MUST NOT prevent the underlying LLM request from executing (graceful degradation)
- **FR-005**: MCP tool call exceptions MUST be reported back to the caller through the results list
- **FR-006**: Search operation exceptions MUST return a fallback SearchResult to prevent pipeline failure
- **FR-007**: The sync and async code paths in `with_cache.py` MUST have consistent exception handling behavior
- **FR-008**: The sync and async code paths in `mcp/middleware.py` MUST have consistent exception handling behavior

### Key Entities

- **Exception context**: The combination of exception type, message, stack trace, and surrounding operation state that determines whether an exception is actionable
- **Graceful degradation**: The behavior of continuing normal operation when a non-critical component (cache, MCP tool) fails

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of exceptions in the three target files are logged with exception details (type, message, or full traceback)
- **SC-002**: Zero silent exception swallowing — no `except Exception` block that does nothing but continue
- **SC-003**: Both sync and async code paths in `with_cache.py` handle exceptions consistently (same log level, same message pattern)
- **SC-004**: All existing tests pass after changes (zero regression)

## Assumptions

- The project uses `logging` module standard library — no external logging framework dependency
- `log = logging.getLogger(__name__)` is already the established logger pattern in all target files
- Exception logging is additive — no behavior changes to control flow, only visibility improvements
- The existing `# noqa: BLE001` suppression on broad `except Exception` blocks is acknowledged but not removed as part of this feature (that would be a separate lint cleanup)
