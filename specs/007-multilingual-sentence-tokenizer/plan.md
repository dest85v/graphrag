# Implementation Plan: NLTK Multilingual Sentence Tokenizer

**Branch**: `007-multilingual-sentence-tokenizer` | **Date**: 2026-04-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-multilingual-sentence-tokenizer/spec.md`

## Summary

Add `nltk_language` configuration field to the GraphRAG chunking pipeline so that `SentenceChunker` uses the correct NLTK PUNKT model for non-English text. The change spans two packages: `graphrag-chunking` (adds field to config and chunker) and `graphrag` (adds default and config template). Default is `"english"` for zero regression.

## Technical Context

**Language/Version**: Python 3.11–3.13 (per workspace `requires-python`)  
**Primary Dependencies**: `nltk~=3.9` (already in `packages/graphrag/pyproject.toml:49`), `pydantic~=2.10` (in `graphrag-chunking`)  
**Storage**: N/A (no data layer changes)  
**Testing**: `pytest` with `asyncio_mode = "auto"`, suites: `unit`, `integration`, `smoke`, `notebook`, `verbs`  
**Target Platform**: Linux server, any OS with Python 3.11–3.13  
**Project Type**: Library (monorepo with 8 packages)  
**Performance Goals**: No performance regression vs. current `nltk.sent_tokenize()` — zero overhead (one extra `__init__` attribute assignment)  
**Constraints**: Must preserve backward compatibility with existing `config.yaml` files that lack `nltk_language`. NLTK Punkt language models auto-download on first use, cached in `~/.nltk/`.  
**Scale/Scope**: Affects only users who set `chunking.type: sentence`. Default `chunking.type: tokens` is unaffected. ~10+ languages supported via `punkt_tab` (NLTK 3.9+).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Compliance | Notes |
|-----------|-----------|-------|
| **I. Library-First** | ✅ PASS | Changes are scoped to `graphrag-chunking` (pure library) and `graphrag` config layer. `ChunkingConfig` and `SentenceChunker` are independently usable. |
| **II. CLI Interface** | ✅ PASS | No CLI changes. Config field flows through existing YAML config → CLI. |
| **III. Test-First** | ✅ PASS | Tests will be written before implementation (Red-Green-Refactor). |
| **IV. Integration Testing** | ✅ PASS | Integration test for full pipeline with `chunking.type: sentence` + `nltk_language: russian`. |
| **V. Versioning & Change Management** | ✅ PASS | semversioner PATCH entry will be added before merge. |

**Result**: ALL GATES PASS. No violations. No complexity justification needed.

## Project Structure

### Documentation (this feature)

```text
specs/007-multilingual-sentence-tokenizer/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (not created by /speckit.plan)
```

### Source Code (repository root)

```text
packages/graphrag-chunking/graphrag_chunking/
├── chunking_config.py          # MODIFIED: add nltk_language field
├── sentence_chunker.py         # MODIFIED: accept nltk_language, pass to nltk.sent_tokenize()
├── chunker_factory.py          # NO CHANGE: **kwargs already passes through

packages/graphrag/graphrag/config/
├── defaults.py                 # MODIFIED: add nltk_language to ChunkingDefaults
├── init_content.py             # MODIFIED: add nltk_language to chunking section
└── models/graph_rag_config.py  # NO CHANGE: passes ChunkingConfig through

packages/graphrag/graphrag-chunking/  (tests)
tests/unit/indexing/chunking/         # NEW: test_sentence_chunker_nltk_language.py
```

**Structure Decision**: Minimal change surface. Only 4 files modified, 0 files created (source), 1 test file created. The `extra="allow"` on `ChunkingConfig` means pydantic will pass through `nltk_language` without validation errors — no schema migration needed.

## Complexity Tracking

Not applicable — no constitution violations, simple additive change.

## Phase 0: Research

All technical unknowns from the spec are already resolved by assumptions:

| Assumption | Verification |
|---|---|
| NLTK 3.9+ supports `sent_tokenize(language=...)` | Confirmed: `nltk~=3.9` in `pyproject.toml:49`; `sent_tokenize(language=...)` added in NLTK 3.8.2 |
| `punkt_tab` contains multilingual models | Confirmed: NLTK 3.9+ `punkt_tab` includes Russian, German, French, Spanish, Chinese, Arabic, etc. |
| `ChunkingConfig.extra="allow"` passes through `nltk_language` | Confirmed: `ChunkingConfig.model_config = ConfigDict(extra="allow")` at line 14 |
| `create_chunker()` passes `**kwargs` to chunker `__init__` | Confirmed: `config.model_dump()` creates dict with all fields, unpacked via `init_args=config_model` in factory |
| Bootstrap already downloads `punkt_tab` | Confirmed: `bootstrap_nltk.py:23` calls `nltk.download("punkt_tab")` |

**Research Decision**: No additional research needed. The implementation path is clear and low-risk. All unknowns resolved by existing codebase inspection.

## Phase 1: Design & Contracts

### Data Model

See `data-model.md` (generated below).

### Interface Contracts

See `contracts/` directory (generated below).

### Quickstart

See `quickstart.md` (generated below).

### Agent Context Update

Will be run after plan artifacts are generated.
