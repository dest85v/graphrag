# Feature Specification: Async Non-Blocking Retry Sleep

**Feature Branch**: `010-async-retry-system`  
**Created**: 2026-04-25  
**Status**: Draft  
**Input**: User description: "Заменить time.sleep() на await asyncio.sleep() в retry системе"

## User Scenarios & Testing

### User Story 1 — Concurrent LLM calls remain responsive under rate limits (Priority: P1)

When multiple LLM API requests are sent concurrently and some hit rate limits or timeouts, the retry backoff delays must not block other concurrent requests. The event loop must remain free to process other in-flight requests, embeddings, or application logic while one request is waiting for retry backoff.

**Why this priority**: P1 — this is the core reliability guarantee of the async pipeline. Blocking the event loop during retry defeats the entire purpose of using async I/O and can cause cascading timeouts across the entire system.

**Independent Test**: Can be fully tested by sending multiple concurrent LLM requests where at least one triggers a retry, and measuring that other requests complete without waiting for the retry delay.

**Acceptance Scenarios**:

1. **Given** an async LLM pipeline with retry enabled, **When** a request fails and enters retry backoff of 10 seconds, **Then** other concurrent requests continue to execute without being blocked for those 10 seconds
2. **Given** N concurrent requests where K requests enter retry backoff, **When** the backoff delays total T seconds, **Then** the non-retrying requests complete in O(T) wall-clock time, not O(N*T)
3. **Given** a high-rate-limit scenario with repeated retries, **When** the system processes 100 concurrent requests with retry, **Then** no request experiences wall-clock latency exceeding 2x its backoff delay (accounting for jitter)

---

### User Story 2 — Sync retry path remains correct for synchronous callers (Priority: P2)

Synchronous LLM callers that go through the retry middleware must continue to use blocking sleep, which is correct for single-threaded synchronous execution. The system must not introduce async/sync mixing bugs.

**Why this priority**: P2 — ensures correctness of the synchronous API surface and prevents regression when both sync and async code paths coexist.

**Independent Test**: Can be tested by invoking the sync completion/embedding API and verifying retry behavior produces correct results.

**Acceptance Scenarios**:

1. **Given** a synchronous LLM caller with retry enabled, **When** a request fails and enters retry backoff, **Then** the caller blocks for the backoff duration and retries successfully
2. **Given** the retry middleware wraps both sync and async LLM functions, **When** each path is invoked independently, **Then** the sync path uses `time.sleep()` and the async path uses `await asyncio.sleep()`

---

### Edge Cases

- What happens when the retry backoff delay is zero or negative due to misconfiguration?
- How does the system handle the case where `asyncio.sleep()` is cancelled (e.g., task cancelled during backoff)?
- What happens under extreme concurrency (hundreds of concurrent requests all retrying simultaneously)?
- How does the jitter parameter interact with very small and very large delay values?

## Requirements

### Functional Requirements

- **FR-001**: The async retry implementation MUST use non-blocking sleep (event-loop-aware) during backoff delays
- **FR-002**: The sync retry implementation MUST use blocking sleep during backoff delays
- **FR-003**: The retry middleware MUST route sync LLM functions through the sync retry path and async LLM functions through the async retry path
- **FR-004**: The async retry implementation MUST respect all existing configuration parameters (base_delay, max_retries, max_delay, jitter, exceptions_to_skip) without behavioral change except for the sleep mechanism
- **FR-005**: Unit and integration tests MUST verify that async retry does not block the event loop during backoff
- **FR-006**: The metrics output (retries, requests_with_retries) MUST remain unchanged

### Key Entities

- **Retry Strategy**: Abstract contract defining sync and async retry behavior with configurable backoff parameters
- **Exponential Backoff**: Retry strategy that increases delay between retries exponentially with optional jitter
- **Immediate Retry**: Retry strategy that retries without delay
- **Retry Middleware**: Wraps LLM functions with retry logic, providing separate sync and async variants

## Success Criteria

### Measurable Outcomes

- **SC-001**: Async retry backoff delays do not block the event loop — measured by confirming that N concurrent non-retrying requests complete within baseline latency (±10% variance) even when M requests are in retry backoff
- **SC-002**: Sync retry behavior remains functionally identical — all existing sync retry tests pass without modification
- **SC-003**: 100% of retry code paths (sync and async) are covered by unit tests
- **SC-004**: An integration test exists that simulates rate limit retries and verifies event loop responsiveness

## Assumptions

- The project uses Python 3.11+ with asyncio for async execution
- LLM providers expose both sync and async client interfaces
- Existing retry configuration (base_delay, max_retries, jitter, etc.) is considered correct and should be preserved
- The async retry path is the primary execution path for the production GraphRAG pipeline
- Existing metrics tracking in the retry layer is accurate and should not change
