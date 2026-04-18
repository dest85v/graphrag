# Quickstart: MCP Support in graphrag-llm

**Date**: 2026-04-18
**Feature**: 009-mcp-llm-support

---

## What This Feature Does

MCP (Model Context Protocol) support enables the GraphRAG LLM pipeline to discover and invoke external tools from MCP servers during completions. When enabled, the LLM can automatically decide to use MCP tools (like running commands, reading files, or calling APIs) and the pipeline transparently handles the tool discovery, invocation, and result formatting.

## Prerequisites

- Python 3.11 or 3.12
- `graphrag-llm` package with MCP support installed
- An MCP server (e.g., `@modelcontextprotocol/server-memory` from npm, or a custom Python server)

## Installation

```bash
uv add "mcp>=1.0.0"
```

The MCP SDK is an optional dependency of `graphrag-llm`. Install with:
```bash
uv add "graphrag-llm[mcp]>=1.0.0"
```

## Basic Example: Stdio Transport

Connect to an MCP server running as a subprocess:

```python
import asyncio
from openai import AsyncOpenAI
from graphrag_llm.completion import OpenAICompletionFactory
from graphrag_llm.config import ModelConfig

# 1. Configure the MCP server
mcp_config = {
    "mcp_config": {
        "transport_type": "stdio",
        "stdio": {
            "command": "python",
            "args": ["-m", "my_mcp_server"],
            "env": None,  # inherit parent env
        },
        "init_timeout": 30.0,
        "tool_timeout": 30.0,
    }
}

# 2. Create model config with MCP enabled
model_config = ModelConfig(
    model_provider="openai",
    model="gpt-4o",
    api_key="sk-...",
    call_args=mcp_config,
)

# 3. Create completion client
completion = OpenAICompletionFactory(
    model_id="gpt-4o",
    model_config=model_config,
    # ... tokenizer, metrics_store, cache_key_creator, etc.
)

# 4. Make a completion call — MCP tools are used automatically
response = completion.completion(
    messages=[{"role": "user", "content": "What files are in /tmp?"}],
)

# The LLM will automatically:
# - Discover available MCP tools from the server
# - Choose to call the appropriate tool (e.g., "list_files")
# - The pipeline invokes the tool via the MCP server
# - Sends the result back to the LLM
# - Returns the final answer
print(response.content)
```

## Basic Example: SSE Transport

Connect to a remote MCP server via HTTP SSE:

```python
mcp_config = {
    "mcp_config": {
        "transport_type": "sse",
        "sse": {
            "url": "http://localhost:8080/mcp",
            "headers": {},
            "timeout": 5.0,
            "sse_read_timeout": 300.0,
        },
        "init_timeout": 30.0,
        "tool_timeout": 30.0,
    }
}
```

## Basic Example: Streamable HTTP Transport

Connect to a Streamable HTTP MCP server:

```python
mcp_config = {
    "mcp_config": {
        "transport_type": "streamable_http",
        "streamable_http": {
            "url": "http://localhost:8000/mcp",
            "headers": {},
            "timeout": 5.0,
        },
        "init_timeout": 30.0,
        "tool_timeout": 30.0,
    }
}
```

## Running a Test MCP Server

Install the MCP memory server for testing:

```bash
npx -y @modelcontextprotocol/server-memory
```

Then connect to it via stdio:

```python
mcp_config = {
    "mcp_config": {
        "transport_type": "stdio",
        "stdio": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
        },
    }
}
```

## Disabling MCP

To disable MCP, simply omit the `mcp_config` from `call_args`:

```python
model_config = ModelConfig(
    model_provider="openai",
    model="gpt-4o",
    api_key="sk-...",
    # No mcp_config — works exactly the same, no MCP involved
)
```

The system is fully backward compatible — removing MCP configuration reverts to standard LLM-only behavior.

## Troubleshooting

**Server fails to start**: Check that the command is correct and the executable exists. Verify args match what the server expects.

**Timeout during initialization**: Increase `init_timeout`. Some MCP servers take time to start up.

**Tool not found**: Verify the tool name matches what the server exposes. The LLM may hallucinate tool names; the middleware returns an error listing available tools.

**Connection lost**: The middleware raises a connection error. For stdio, check that the subprocess is still running. For SSE/HTTP, check network connectivity.
