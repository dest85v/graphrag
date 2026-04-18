# Implementation Plan: Fix CI Pre-existing Errors

**Branch**: `008-fix-ci-errors` | **Date**: 2026-04-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-fix-ci-errors/spec.md`

## Summary

Fix 9 pre-existing CI errors blocking `poe check` in CI. Three ruff errors (1 SLF001 on `_nltk_language` private member access, 2 RUF001 Cyrillic false-positives) and six pyright `reportMissingImports` for `tokenizers` not installed in the dev environment. No new functionality — pure maintenance.

## Technical Context

**Language/Version**: Python 3.11–3.13 (workspace `requires-python = ">=3.11,<3.14"`)  
**Primary Dependencies**: `ruff` (lint/format), `pyright` (type checking), `tokenizers` (HuggingFace, via `graphrag-llm`)  
**Storage**: N/A — no data layer changes  
**Testing**: `pytest` with `asyncio_mode = "auto"`, suites: `unit`, `integration`, `smoke`, `notebook`, `verbs`  
**Target Platform**: Linux server (CI), standard Linux/macOS development machines  
**Project Type**: Monorepo library (8 uv workspace packages)  
**Performance Goals**: N/A — CI fix only  
**Constraints**: Fixes must not change runtime behavior, API surfaces, or test semantics. Zero regressions.  
**Scale/Scope**: 9 CI errors across 3 files in 2 packages (`graphrag-llm`, `graphrag-chunking`) + 1 test file in root `tests/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Notes |
|---|---|---|
| **I. Library-First** | ✅ PASS | No new libraries; fixes existing packages |
| **II. CLI Interface** | ✅ PASS | No CLI changes |
| **III. Test-First** | ✅ PASS | Fixes are not new features; existing tests remain unchanged |
| **IV. Integration Testing** | ✅ PASS | `poe test` will be run post-fix to verify zero regressions |
| **V. Versioning & Change Management** | ✅ PASS | PATCH semversioner entry will be added before merge |
| **Security & Responsible AI** | ✅ PASS | No security impact |
| **Development Workflow** | ✅ PASS | Fix purpose: make `poe check` pass (the workflow gate itself) |

**All gates passed — no violations requiring justification.**

## Project Structure

### Documentation (this feature)

```text
specs/008-fix-ci-errors/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (N/A — no entities)
├── quickstart.md        # Phase 1 output (N/A — no features)
├── contracts/           # Phase 1 output (N/A — no interfaces)
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
packages/graphrag-llm/graphrag_llm/tokenizer/huggingface_tokenizer.py  ← tokenizers import
packages/graphrag-llm/pyproject.toml                                    ← dependency fix
tests/unit/chunking/test_sentence_chunker_nltk_language.py              ← SLF001 fix
tests/unit/indexing/operations/test_noun_phrase_factory.py              ← RUF001 fix
```

**Structure Decision**: Minimal change scope — 3 files to modify, 1 config update. No new files, no new directories.

## Complexity Tracking

N/A — no constitution violations.
