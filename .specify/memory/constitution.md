<!--
  SYNC IMPACT REPORT
  ===================
  Version change: 1.0.0 (initial)
  Modified principles: N/A (initial creation)
  Added sections: Core Principles (5), Security & Responsible AI, Development Workflow, Governance
  Removed sections: None
  Templates requiring updates:
    - .specify/templates/plan-template.md: Constitution Check gate references align (no changes needed)
    - .specify/templates/spec-template.md: No constitution-driven constraints added (no changes needed)
    - .specify/templates/tasks-template.md: Test-first principle reflected in task conventions (no changes needed)
  Follow-up TODOs: None
-->

# GraphRAG Constitution

## Core Principles

### I. Library-First Architecture

Every feature starts as an independently usable library within the monorepo.
All libraries MUST be self-contained, independently testable, and documented.

The GraphRAG workspace contains eight packages (`graphrag`, `graphrag-common`,
`graphrag-chunking`, `graphrag-input`, `graphrag-storage`, `graphrag-cache`,
`graphrag-llm`, `graphrag-vectors`). Each package MUST have a clear, single
responsibility and MUST communicate with other packages through well-defined
interfaces (public APIs, CLI contracts, or shared schema).

Organizational-only libraries with no independent purpose are prohibited.

### II. CLI Interface

Every library MUST expose its functionality via a CLI entry point.

Text in/out protocol: stdin/args → stdout; errors → stderr.
Support JSON and human-readable output formats.

All GraphRAG features (`index`, `query`, `prompt_tune`, etc.) MUST be
callable through the `graphrag` CLI. This ensures reproducibility, scripting
capability, and a consistent developer experience across all tools.

### III. Test-First (NON-NEGOTIABLE)

Tests MUST be written before implementation code. The Red-Green-Refactor cycle
is strictly enforced.

- **Red**: Tests written and failing before any implementation.
- **Green**: Minimal implementation to make tests pass.
- **Refactor**: Clean up code while keeping all tests green.

All pull requests MUST pass `uv run poe check` (format + lint + typecheck) and
all applicable test suites before merge. The project uses pytest with
`asyncio_mode = "auto"`, with gated slow tests via `--run_slow`.

### IV. Integration Testing

New libraries, contract changes, inter-package communication, and shared
schemas MUST have integration tests.

The GraphRAG monorepo uses five test suites: `unit`, `integration`, `smoke`,
`notebook`, and `verbs`. Integration tests validate that package boundaries
are respected and that cross-package workflows produce correct results.

Azurite-emulated Azure storage tests MUST use `./scripts/start-azurite.sh`
before execution.

### V. Versioning & Change Management

Every code change MUST include a semversioner change entry before merge.

- **MAJOR**: Backward-incompatible governance changes or principle removals.
- **MINOR**: New principles, sections, or materially expanded guidance.
- **PATCH**: Clarifications, wording fixes, non-semantic refinements.

The project uses semversioner (`uv run semversioner add-change`). CI validates
semversioner JSON entries in `.semversioner/`. Between minor version bumps,
`graphrag init --root [path] --force` MUST be run to update config formats.

## Security & Responsible AI

GraphRAG processes unstructured text through LLMs to extract knowledge graphs.
Security and responsible AI practices are mandatory.

- All LLM interactions MUST respect rate limits and cost boundaries.
- Users MUST be warned about indexing costs before large operations.
- Prompt tuning MUST follow the documented Prompt Tuning Guide.
- The Responsible AI FAQ (`RAI_TRANSPARENCY.md`) MUST be kept current.
- No secrets, credentials, or API keys MAY appear in code or configuration files.

## Development Workflow

All PRs MUST pass the full CI check gate before merge.

- **Pre-merge**: `uv run poe check` (Ruff format + lint + pyright typecheck).
- **Testing**: `uv run poe test` for full coverage; individual suites via
  `poe test_unit`, `test_integration`, `test_smoke`, `test_notebook`, `test_verbs`.
- **Smoke tests**: Azurite-based tests require `./scripts/start-azurite.sh`.
- **Docs**: `uv run poe serve_docs` to preview documentation changes.
- **Contributing**: Fork → branch → changes → `poe check` + tests →
  `semversioner add-change` → PR. See `CONTRIBUTING.md` for full process.

Complexity MUST be justified. Start simple and apply YAGNI principles.

## Governance

This Constitution supersedes all other development practices and guidelines
within the GraphRAG repository.

**Amendment process**:
1. Propose amendment as a PR to `.specify/memory/constitution.md`.
2. Document the change with a semversioner entry.
3. All PRs and reviews MUST verify compliance with current principles.
4. Complexity beyond established patterns MUST be justified in the PR description.

**Versioning policy**: Semantic versioning per semversioner. The constitution
version is tracked in the footer of this file. MAJOR bumps for backward-
incompatible governance changes; MINOR for new principles/sections; PATCH for
clarifications and wording refinements.

**Compliance**: All contributors MUST follow this constitution. The `/speckit.plan`
command enforces a Constitution Check gate before Phase 0 research begins,
and a second check after Phase 1 design.

**Version**: 1.0.0 | **Ratified**: 2026-04-17 | **Last Amended**: 2026-04-17
