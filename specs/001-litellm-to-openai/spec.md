# Feature Specification: Replace LiteLLM with OpenAI SDK

**Feature Branch**: `001-litellm-to-openai`
**Created**: 2026-04-17
**Status**: Draft
**Input**: Replace `litellm` dependency with native `openai` SDK in `graphrag-llm` package

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Seamless Migration for GraphRAG Indexing Users (Priority: P1)

GraphRAG users run indexing and querying pipelines that depend on `graphrag-llm` for LLM
completions and embeddings. After this migration, their pipelines MUST work identically —
same configuration format, same API responses, same error behavior — with no changes to
their `config.yaml` or calling code.

**Why this priority**: This is a core infrastructure change affecting every GraphRAG user.
Any breakage would block all indexing and querying operations.

**Independent Test**: Run a complete GraphRAG indexing pipeline (entities, claims, communities)
against OpenAI and Azure OpenAI models with the new backend and verify results match the
expected quality thresholds.

**Acceptance Scenarios**:

1. **Given** a valid GraphRAG configuration with `type: litellm`, **When** the user runs
   `graphrag index`, **Then** completions and embeddings are produced successfully
2. **Given** a configuration with `type: litellm` and Azure auth, **When** the user runs
   `graphrag index`, **Then** Azure Managed Identity authentication works correctly
3. **Given** a configuration with mock responses, **When** the user runs tests, **Then**
   all mock response behavior is identical

---

### User Story 2 - Test Developers Need Reliable Error Simulation (Priority: P1)

Integration and unit test suites use `with_errors_for_testing` middleware to simulate
LLM failures (rate limits, connection errors, auth failures). After migration, test
 suites MUST continue to produce the same error types and behavior.

**Why this priority**: Without working error simulation, the test suite cannot validate
 retry logic, error handling, and middleware resilience.

**Independent Test**: Run the full integration test suite with the new backend and verify
 all `with_errors_for_testing` scenarios produce expected exceptions.

**Acceptance Scenarios**:

1. **Given** `with_errors_for_testing` middleware with `failure_rate=0.5`, **When**
   a completion is called, **Then** ~50% of calls raise the configured exception type
2. **Given** `exception_type="RateLimitError"`, **When** failure is triggered, **Then**
   the raised exception is the OpenAI SDK equivalent of RateLimitError

---

### User Story 3 - Tool Calling and Structured Output Work Identically (Priority: P2)

Users who rely on tool calling (function calling) and structured output (response_format)
in their GraphRAG prompts MUST see the same behavior after migration. This includes
`FunctionToolManager` integration and Pydantic response parsing.

**Why this priority**: Tool calling is used for noun phrase extraction, entity resolution,
 and other GraphRAG graph operations. Structured output is used for claim extraction.

**Independent Test**: Run a GraphRAG indexing run with tool calling enabled and verify
 tool definitions are passed correctly and LLM responses with `tool_calls` are handled
 properly.

**Acceptance Scenarios**:

1. **Given** `tools=[...]` in completion args, **When** completion is called, **Then**
   tool definitions are passed to the OpenAI SDK and LLM responses include tool calls
2. **Given** `response_format=MyModel`, **When** completion returns content, **Then**
   the content is parsed into `MyModel` instance correctly

---

### Edge Cases

- What happens when a user specifies a model ID in `openai/<model>` format — should it
  be normalized to just `<model>` for the OpenAI SDK?
- How are unsupported parameters (e.g., `thinking`, `web_search_options`) handled —
  silently dropped, logged, or raise an error?
- What happens with streaming responses — are chunk types compatible?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide `OpenAICompletion` class that implements the same
  `LLMCompletion` interface as `LiteLLMCompletion`
- **FR-002**: System MUST provide `OpenAIEmbedding` class that implements the same
  `LLMEmbedding` interface as `LiteLLMEmbedding`
- **FR-003**: System MUST support OpenAI models (gpt-4o, gpt-4o-mini, text-embedding-3-*)
  via `openai.OpenAI` / `openai.AsyncOpenAI`
- **FR-004**: System MUST support Azure OpenAI via `openai.AzureOpenAI` /
  `openai.AsyncAzureOpenAI` with both API Key and Azure Managed Identity authentication
- **FR-005**: System MUST provide `OpenAITokenizer` that replaces `LiteLLMTokenizer`
  using `tiktoken` directly, producing identical encode/decode results
- **FR-006**: System MUST update `MockLLMCompletion` and `MockLLMEmbedding` to remove
  all `import litellm` dependencies
- **FR-007**: System MUST update `with_errors_for_testing` middleware to use `openai`
  exceptions instead of `litellm.exceptions`
- **FR-008**: System MUST support tool calling (function calling) through the same
  `tools=[...]` parameter pattern
- **FR-009**: System MUST support structured output through `response_format` parameter
- **FR-010**: System MUST support streaming completions with chunk iteration
- **FR-011**: System MUST maintain backward compatibility — configs with `type: litellm`
  MUST continue to work during a deprecation period
- **FR-012**: System MUST filter out parameters not supported by the OpenAI SDK before
  making API calls (replacing `drop_params: True` from LiteLLM)
- **FR-013**: System MUST provide equivalent exception mapping — OpenAI exceptions must
  map to the same error handling behavior as LiteLLM exceptions

### Key Entities *(include if feature involves data)*

- **OpenAICompletion**: New completion class replacing `LiteLLMCompletion`, wrapping
  `openai.OpenAI` / `openai.AsyncOpenAI` clients
- **OpenAIEmbedding**: New embedding class replacing `LiteLLMEmbedding`, wrapping
  `openai.OpenAI` / `openai.AsyncOpenAI` embedding endpoints
- **OpenAITokenizer**: New tokenizer class replacing `LiteLLMTokenizer`, using `tiktoken`
  directly
- **AzureCompletion**: Azure-specific completion class using `AzureOpenAI` with
  Managed Identity token provider
- **LLMProviderType**: Enum values — `LiteLLM` becomes deprecated alias for `OpenAI`,
  `MockLLM` remains unchanged
- **SupportedParams**: Internal parameter whitelist mapping OpenAI SDK parameters to
  replace LiteLLM's automatic `drop_params` filtering

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All existing unit and integration tests in `graphrag-llm` pass without
  modification (100% test suite pass rate)
- **SC-002**: Zero `import litellm` statements remain in any production source file
  under `graphrag_llm/`
- **SC-003**: Tokenization output is byte-identical between `LiteLLMTokenizer` and
  `OpenAITokenizer` for all supported models (verified via comparison tests)
- **SC-004**: Azure OpenAI completion latency within 5% of the previous `litellm`-based
  implementation (measured against same endpoint)
- **SC-005**: Configuration migration is transparent — existing `config.yaml` files with
  `type: litellm` work without modification and emit a deprecation warning

## Assumptions

- The project's primary LLM providers remain OpenAI and Azure OpenAI. Support for
  Anthropic, Groq, Bedrock, and other LiteLLM-provided providers is intentionally
  out of scope — this is a conscious trade-off to reduce complexity.
- `tiktoken` is already a transitive dependency through `litellm` and will become a
  direct dependency. Tokenization behavior via `tiktoken` matches `litellm`'s internal
  usage (both use the same `tiktoken` encodings).
- The `openai` SDK version `1.60+` provides all features needed: streaming, tool
  calling, structured output (response_format), Azure OpenAI support, and exception
  hierarchy.
- `azure-identity` remains a dependency for Azure Managed Identity authentication and
  is not affected by this migration.
- The `LLMCompletionResponse` type already extends `openai.types.chat.ChatCompletion`
  and `LLMEmbeddingResponse` extends `openai.types.CreateEmbeddingResponse` — these
  types remain compatible.
