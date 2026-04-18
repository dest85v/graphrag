# Feature Specification: MCP Support in graphrag-llm

**Feature Branch**: `009-mcp-llm-support`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: User description: "Надо реализовать задачу 'P1 — Реализовать MCP (Model Context Protocol) поддержку в graphrag-llm'"

## User Scenarios & Testing

### User Story 1 - Configure and discover MCP tools from a local server (Priority: P1)

A data scientist wants to extend the GraphRAG LLM pipeline with custom tools (e.g., code execution, file system access, external APIs) by connecting to an MCP server. They need to configure the server connection and discover available tools without writing any protocol code.

**Why this priority**: This is the foundational capability — without tool discovery, the rest of the MCP integration is useless. It enables every other user story.

**Independent Test**: A user can configure an MCP server (via command + args for stdio transport), run a discovery call, and receive a structured list of available tools with names, descriptions, and input schemas.

**Acceptance Scenarios**:

1. **Given** a user has configured an MCP stdio server (command `python -m mcp_server`, args `["--mode", "fast"]`), **When** the system initializes the MCP client, **Then** the client connects to the server, negotiates the protocol version, and returns a list of discovered tools with names, descriptions, and JSON Schema input definitions
2. **Given** a user has configured an MCP SSE server (URL `http://localhost:8080/mcp`), **When** the system initializes the MCP client, **Then** the client connects via HTTP SSE, negotiates the protocol, and returns the list of discovered tools
3. **Given** an MCP server command fails to start or times out during initialization, **When** the system attempts to initialize the client, **Then** the system raises a clear error within the configured timeout (default 30s) describing the failure
4. **Given** the MCP server returns no tools, **When** the system completes initialization, **Then** the client reports zero available tools and the completion pipeline falls back to standard tool-free operation

---

### User Story 2 - Use MCP tools in LLM completions with automatic tool calling (Priority: P1)

A developer building a GraphRAG pipeline wants the LLM to automatically decide when to invoke MCP tools during a conversation. They configure MCP tools once, then use normal LLM completion calls — the pipeline transparently handles tool discovery, LLM tool choice, tool invocation, and result formatting.

**Why this priority**: This is the core value proposition — enabling LLMs to dynamically invoke external tools discovered from MCP servers. It transforms the LLM from a pure text generator into a tool-using agent.

**Independent Test**: A user configures MCP tools, sends a completion request with a user message that requires tool use (e.g., "Run the command `ls -la`"), and receives a final response that incorporates the tool output.

**Acceptance Scenarios**:

1. **Given** MCP tools are configured and discovered (e.g., tools: `run_command`, `read_file`), **When** a user sends a completion request with message "List files in /tmp", **Then** the LLM response includes a tool call for `run_command` with appropriate arguments
2. **Given** the LLM returns a tool call, **When** the MCP middleware processes the tool call, **Then** the middleware invokes the MCP server's `tools/call` method with the tool name and arguments, receives the result, and formats it as a tool result message
3. **Given** the tool result is sent back to the LLM, **When** the LLM produces the final answer, **Then** the final response incorporates the tool output (e.g., lists the files from `/tmp`)
4. **Given** a tool call fails (e.g., MCP server returns an error), **When** the middleware handles the error, **Then** the error is formatted as a tool result message and sent back to the LLM for recovery
5. **Given** multiple tool calls are returned in a single LLM response, **When** the middleware processes them, **Then** all tool calls are executed sequentially (or in parallel if supported) and all results are included in subsequent LLM messages

---

### User Story 3 - Manage MCP server lifecycle and graceful shutdown (Priority: P2)

A production operator needs to ensure that MCP server connections are properly managed — servers should be started, kept alive for the duration of use, and cleanly shut down when the LLM client is disposed of, without leaving orphaned processes.

**Why this priority**: Important for production reliability and resource management, but not blocking for the core functionality.

**Independent Test**: A user creates and disposes of an MCP-backed LLM client, and verifies that the MCP subprocess terminates cleanly (no zombie processes) and that connections can be re-established after a disconnect.

**Acceptance Scenarios**:

1. **Given** an MCP client with a stdio transport is created, **When** the client is disposed, **Then** the subprocess is terminated gracefully and the process exits cleanly
2. **Given** an MCP connection is lost unexpectedly, **When** the client attempts a tool call, **Then** the client raises a connection error with a clear message
3. **Given** a stdio MCP server crashes, **When** the system detects the crash (e.g., subprocess exits), **Then** subsequent tool calls fail fast with a descriptive error instead of hanging

---

### Edge Cases

- **MCP server returns tool name not matching LLM tool format**: The system converts MCP tool schemas to the format expected by the LLM, but tool invocation uses the original MCP tool name
- **LLM hallucinates a tool name**: If the LLM requests a tool that wasn't discovered, the middleware returns a clear error to the LLM asking it to use a valid tool
- **Tool execution exceeds timeout**: Each tool call respects a per-call timeout; exceeded calls fail with a timeout error message
- **Mixed stdio and SSE servers in one pipeline**: Users can configure multiple MCP servers, and the system routes tool calls to the appropriate server based on tool name
- **Very large tool schemas**: JSON Schema input definitions may be large; the system handles schemas up to the LLM's context window limits

## Requirements

### Functional Requirements

- **FR-001**: Users MUST configure MCP servers with connection parameters (command + args for stdio, or URL for SSE) through a declarative configuration object
- **FR-002**: The system MUST support stdio transport — launching an MCP server as a subprocess and communicating via standard input/output streams
- **FR-003**: The system MUST support SSE transport — connecting to an MCP server via HTTP with Server-Sent Events for receiving responses
- **FR-004**: The system MUST support Streamable HTTP transport — connecting to an MCP server via HTTP with streaming JSON-RPC
- **FR-005**: The system MUST implement MCP protocol handshake to negotiate protocol version and capabilities with the server
- **FR-006**: The system MUST discover available tools from the MCP server and return them as structured objects with name, description, and input schema
- **FR-007**: The system MUST invoke discovered tools via the MCP server when the LLM selects them during completion
- **FR-008**: The system MUST convert MCP tool definitions to the format expected by the LLM's tool calling interface
- **FR-009**: The system MUST handle MCP tool call errors gracefully and return error messages to the LLM for recovery
- **FR-010**: The system MUST support graceful shutdown of MCP server connections, terminating subprocesses for stdio transport
- **FR-011**: The system MUST enforce configurable timeouts for MCP initialization and individual tool calls
- **FR-012**: Users MUST be able to enable MCP tool support optionally — the system MUST work identically with or without MCP configuration (backward compatible)

### Key Entities

- **MCP Server Configuration**: Declarative configuration describing how to connect to an MCP server — includes transport type (stdio/SSE/streamable_http), server command and arguments (stdio), server URL (SSE), optional environment variables, and timeout settings
- **MCP Tool**: A tool discovered from an MCP server, consisting of a name (string), description (string), and input_schema (JSON Schema object defining required and optional parameters)
- **MCP Client**: The runtime component that manages the connection to an MCP server — handles initialization, tool discovery, tool invocation, and lifecycle management
- **MCP Transport**: The communication layer between the MCP client and server — stdio (subprocess IPC), SSE (HTTP with Server-Sent Events), or Streamable HTTP (HTTP with JSON-RPC streaming)

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can configure and connect to an MCP stdio server and discover tools within 5 seconds of initialization
- **SC-002**: End-to-end MCP tool calling (LLM → tool call → MCP invocation → result → LLM final response) completes within 10 seconds for a simple tool (e.g., echo, read file)
- **SC-003**: 100% of configured MCP tools are discoverable and invokable without manual protocol handling
- **SC-004**: Users can switch between MCP-enabled and MCP-disabled configurations without any code changes to their completion calls
- **SC-005**: Graceful shutdown terminates MCP subprocesses within 3 seconds of client disposal

## Assumptions

- The `mcp` Python SDK (official Model Context Protocol SDK, version 1.0.0+) is available and stable for Python 3.11+
- MCP servers follow the MCP specification (2024-11-05) for JSON-RPC 2.0 communication
- LLMs used with the MCP middleware support OpenAI-compatible tool calling format (which all major models do)
- The MCP stdio server is a separate process that the user provides (e.g., `@modelcontextprotocol/server-memory`, custom Python server)
- Users have the necessary permissions to execute the MCP server command on their system
- Existing OpenAI SDK integration (after the 001-litellm-to-openai task) remains the underlying transport for LLM API calls
- Tool call results are limited to text output compatible with the LLM's message format (binary data, images, etc. are out of scope for v1)
- Configuration is provided via the existing `graphrag_llm` configuration system (pydantic-based config models)
