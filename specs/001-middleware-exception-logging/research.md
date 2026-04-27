# Research: Exception Logging Patterns in Python Middleware

## Decision: Use `logger.exception()` for all caught exceptions

### Rationale
- `logger.exception()` automatically appends the full traceback, equivalent to `logger.error(..., exc_info=True)` but more concise
- All three target files already use `log = logging.getLogger(__name__)` — no new logger creation needed
- Python standard library `logging` is universally available, no dependency changes

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| `logger.exception(msg)` | Automatic traceback, standard | Logs at ERROR level by default |
| `logger.error(msg, exc_info=True)` | Explicit control | More verbose |
| `logger.warning(msg, exc_info=True)` | Lower severity | Traceback at warning level may be ignored |
| Third-party (structlog, loguru) | Rich formatting | Adds dependency, overkill for this fix |

**Chosen**: `logger.exception()` — matches existing patterns in the codebase, zero dependency changes.

### Best Practices Applied

1. **Log before continuing** — every `except` block that does not re-raise MUST log
2. **Include exception info** — use `exc_info=True` or `logger.exception()` so traceback is captured
3. **Preserve graceful degradation** — logging is additive, no behavior change
4. **Consistent sync/async** — both paths in each middleware must use identical patterns

### Findings per File

#### with_cache.py
- Lines 94-95 (sync parse): Already logs `log.exception("Failed to parse cached response, making request")` — **OK**
- Lines 139-140 (async parse): Already logs same message — **OK**
- Cache write failure (lines 102, 147): No explicit try/except around `cache.set()` calls — if an exception occurs, it propagates to the caller. This is intentional (cache failure should not affect the response), but should be wrapped in try/except + warning log for observability.

#### mcp/middleware.py
- Line 245-247 (async unexpected): Catches `Exception`, appends to results AND exceptions — **OK for tracking, missing logger call**
- Line 426-427 (sync unexpected): Catches `Exception`, appends to results — **missing logger call AND missing exceptions list**
- Lines 311-312 (async extract tool_calls): Already logs `log.exception("Failed to extract tool_calls from response")` — **OK**
- Lines 390-391 (sync extract tool_calls): Already logs same message — **OK**

#### search.py
- Line 267 (map phase): Already logs `logger.exception("Exception in _map_response_single_batch")` — **OK**
- Line 424 (reduce phase): Already logs `logger.exception("Exception in reduce_response")` — **OK**

### Conclusion

The primary actionable gap is MCP middleware sync path (line 426-427) missing both a logger call and the exceptions list tracking. The `with_cache.py` cache write operations could benefit from explicit try/except + warning logging, but are currently acceptable as they propagate naturally.
