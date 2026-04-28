# Feature Specification: Safe Prompt Templating

**Feature Branch**: `015-safe-prompt-templating`  
**Created**: 2026-04-27  
**Status**: Draft  
**Input**: User description: "P2 — Заменить `str.format()` на безопасную template engine для промптов"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Safe document ingestion with special characters (Priority: P1)

A user uploads documents containing characters that break Python's `str.format()` — such as `}}` (double closing brace) or `{entity_types}` (strings that look like format placeholders). Currently, these documents cause prompt formatting errors or silently inject unintended directives into LLM prompts.

**Why this priority**: This is the core security and reliability issue. Without this, any document with special characters can crash the indexing pipeline or be exploited for prompt injection.

**Independent Test**: Can be fully tested by providing sample documents with `}}`, `{input_text}`, and `{entity_types}` in the content, running the indexing pipeline, and verifying documents are processed without errors and no injected directives reach the LLM.

**Acceptance Scenarios**:

1. **Given** a document containing `}}` in its text, **When** the graph extractor processes it, **Then** the prompt renders correctly without a `InvalidFormatStringError`
2. **Given** a document containing `{entity_types}` as literal text, **When** the graph extractor formats the prompt, **Then** the literal text appears in the prompt as-is, not substituted as a variable
3. **Given** a document containing `{input_text}` as literal text, **When** the prompt is rendered, **Then** no injection occurs and the text is passed through safely

---

### User Story 2 - Developer-authored prompts with existing placeholders (Priority: P1)

Authors write custom prompt templates using `{variable_name}` placeholders (the current convention throughout the codebase). These prompts must continue to work with variable substitution, but without the security risks of `str.format()`.

**Why this priority**: Existing prompts across 23 files use this convention. A breaking change here would require manual migration of every prompt file.

**Independent Test**: Can be tested by loading existing prompt templates from the codebase and rendering them with context dicts — verifying output matches current behavior for valid inputs.

**Acceptance Scenarios**:

1. **Given** an existing prompt template with `{input_text}` and `{entity_types}` placeholders, **When** rendered with a context dict containing those keys, **Then** the output matches the expected substituted text
2. **Given** a prompt template with `{max_length}` placeholder, **When** rendered with `{"max_length": "1000"}`, **Then** the output contains `1000` in place of the placeholder

---

### User Story 3 - Backward-compatible prompt loading (Priority: P2)

Existing prompt files (plain `.txt` files loaded as strings) continue to work without modification. The template engine must support the existing `{variable}` syntax natively, without requiring authors to rewrite their prompts.

**Why this priority**: Minimizes migration effort and prevents regression in custom prompt configurations.

**Independent Test**: Can be tested by loading all existing prompt `.txt` files from the codebase and rendering them with the same context dicts used today.

**Acceptance Scenarios**:

1. **Given** all existing prompt files in `packages/graphrag/graphrag/prompts/`, **When** loaded and rendered via the new template engine, **Then** the output is functionally equivalent to the current `str.format()` output
2. **Given** a prompt file from `prompt_tune/generator/` directory, **When** rendered with dynamic context, **Then** all `{placeholder}` values are correctly substituted

---

### Edge Cases

- What happens when a prompt template contains literal `{` or `}` that are not placeholders? (Must be escaped or preserved)
- How does the system handle a prompt template with a `{` followed by text that is not a valid key? (Should raise a clear error rather than crashing unpredictably)
- How does the system handle empty context dicts for templates that expect variables?
- How are binary or null bytes in document text handled during rendering?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST replace all `str.format()` prompt rendering calls with a template engine that does not interpret user-controlled input as template syntax
- **FR-002**: System MUST support `{variable}` placeholder syntax (single curly braces) to maintain compatibility with existing prompt files — no prompt file rewrites required
- **FR-003**: System MUST escape or neutralize `{` and `}` characters in user-controlled input (document content, query text, context data) so they cannot interfere with template rendering
- **FR-004**: System MUST raise a clear, actionable error when a template references a key that does not exist in the provided context
- **FR-005**: System MUST cover all 23 affected files across indexing operations, query engines, and prompt tuning generators
- **FR-006**: System MUST preserve the existing template string format in prompt files — no conversion to `{% %}` or `{{ }}` syntax required in prompt source files
- **FR-007**: System MUST not introduce new runtime dependencies beyond `jinja2` (already present as a transitive dependency via `graphrag-llm`)

### Key Entities *(include if feature involves data)*

- **Prompt Template**: A string (loaded from `.txt` files or defined inline) containing `{variable_name}` placeholders that get substituted at render time
- **Template Engine**: The rendering layer that processes prompt templates with context dicts, safe from user input injection
- **Context Dict**: A mapping of variable names to values, provided by the caller (e.g., `{"input_text": "...", "entity_types": "..."}`)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 36 `str.format()` calls across 23 files are replaced with the new template engine — zero remaining `.format()` calls on prompt strings
- **SC-002**: 100% of existing prompt files render identically to current `str.format()` output when given the same context (verified via diff)
- **SC-003**: Documents containing `}}`, `{input_text}`, or `{entity_types}` as literal text are processed without errors or injection
- **SC-004**: All existing unit and integration tests pass after the migration, with no regressions in prompt rendering behavior
- **SC-005**: New test coverage for edge cases (special characters in input, missing keys, empty context) reaches at least 80% on the template engine module

## Assumptions

- `jinja2` will be promoted to a direct dependency of the `graphrag` package (it is currently only a dependency of `graphrag-llm`)
- The template engine uses a custom Jinja2 `Environment` with `variable_start_string="{"` and `variable_end_string="}"` to support single-brace syntax
- Literal `{` and `}` in user input are escaped by the template engine automatically (via `escape_user_input()` pre-processing), not by modifying prompt templates
- The existing prompt file loading mechanism (reading `.txt` files as raw strings) is unchanged
- Custom prompt overrides (user-provided prompt files via config) must also support the `{variable}` syntax
