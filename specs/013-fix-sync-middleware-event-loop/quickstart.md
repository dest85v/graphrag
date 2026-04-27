# Quickstart: Verify sync middleware event loop fix

**Feature**: 013-fix-sync-middleware-event-loop  
**Date**: 2026-04-26

## Setup

```bash
cd /home/dest85v/Projects/graphrag
uv sync
git checkout 013-fix-sync-middleware-event-loop
```

## Verification Tests

### Test 1: MCP middleware from async context (P1 - critical)

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock
from graphrag_llm.mcp.middleware import MCPCompletionMiddleware
from graphrag_llm.mcp.types import MCPTool

async def test_from_async_context():
    """MCPMiddleware._wrap_completion() must not crash when called from async context."""
    mw = MCPCompletionMiddleware(
        mcp_config={"transport_type": "stdio", "stdio": {"command": "python"}}
    )
    mw._base_sync = MagicMock(return_value=MagicMock(choices=[]))
    mw._initialized = True
    mw._mcp_tools = [MCPTool(name="test", description="Test", input_schema={})]
    
    # This should NOT raise RuntimeError: This event loop is already running
    result = mw._wrap_completion(messages=[{"role": "user", "content": "hi"}])
    assert result is not None
    print("PASS: MCP middleware works from async context")

asyncio.run(test_from_async_context())
```

### Test 2: Cache middleware no loop accumulation

```python
import gc
import asyncio
from unittest.mock import AsyncMock
from graphrag_llm.middleware.with_cache import with_cache

async def test_no_loop_accumulation():
    """Cache middleware should not leak event loops under repeated sync calls."""
    # ... setup cache, call sync wrapper 100 times, verify loop count stable
    pass
```

### Test 3: Backward compatibility (sync entry point)

```python
def test_sync_entry_point():
    """Pure sync callers must see no behavioral change."""
    mw = MCPCompletionMiddleware(mcp_config={"transport_type": "stdio", "stdio": {"command": "python"}})
    # Call from truly sync context — should create and destroy its own loop
    result = mw._wrap_completion(messages=[{"role": "user", "content": "hi"}])
    assert result is not None
    print("PASS: Backward compatible with sync entry points")

test_sync_entry_point()
```

### Test 4: Full test suite

```bash
uv run poe test_unit -- -k "mcp or middleware"
uv run poe test_integration -- -k "mcp"
uv run poe check  # format + lint + typecheck
```

## Expected Outcomes

- All existing MCP middleware tests pass (zero regression)
- New tests for async-context sync calls pass
- No `RuntimeError` when calling sync middleware from async context
- No event loop accumulation under load
- `uv run poe check` passes
