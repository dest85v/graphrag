# Research: CI Pre-existing Errors

**Feature**: 008-fix-ci-errors  
**Date**: 2026-04-18  
**Status**: Complete — all NEEDS CLARIFICATION resolved

## Research Findings

### 1. tokenizers not resolved by pyright

**Unknown resolved**: Why pyright cannot resolve `import tokenizers` when it's listed in `graphrag-llm/pyproject.toml`.

**Decision**: Move `tokenizers` from `[project.optional-dependencies]` (huggingface extra) to base `dependencies` in `packages/graphrag-llm/pyproject.toml`.

**Rationale**:
- `tokenizers` is listed at `pyproject.toml:48` under `[project.optional-dependencies]` with key `huggingface`
- `uv sync` (without `--extra huggingface`) does not install optional extras
- 6 files import `tokenizers` directly (huggingface_tokenizer.py, test files)
- Moving to base deps ensures `uv sync` always installs it, and pyright can resolve it
- `sentencepiece` and `protobuf` remain in the `huggingface` optional extra (only needed for specific tokenizer types)

**Alternatives considered**:
- Run `uv sync --extra huggingface` — works but inconsistent with documented workflow (`uv sync` only)
- Add `graphrag-llm[huggingface]` to workspace `[tool.uv.sources]` — adds complexity to workspace config
- Configure pyright `extraPaths` — band-aid, doesn't fix the install gap

### 2. SLF001 on `_nltk_language` in test

**Unknown resolved**: Best way to suppress SLF001 for legitimate test access to private members.

**Decision**: Add `SLF001` to per-file-ignores for `tests/*` in `pyproject.toml`.

**Rationale**:
- `SLF001` (private member access) fires on `tests/unit/chunking/test_sentence_chunker_nltk_language.py:112`
- Tests accessing private attributes is a common and legitimate pattern for verifying internal state defaults
- `tests/*` already has broad ignores (`S`, `D`, `ANN`, `T201`, `ASYNC`, `ARG`, `PTH`, `TRY`)
- Adding `SLF001` keeps this consistent with the existing test file ignore pattern
- More maintainable than adding individual `# noqa` comments to each test

**Alternatives considered**:
- `# noqa: SLF001` on each affected line — works but repetitive, one per test
- Expose a public getter method — over-engineering for a test-only concern

### 3. RUF001 Cyrillic false-positives in test

**Unknown resolved**: Best way to suppress RUF001 for test files with intentional Cyrillic strings.

**Decision**: Add `RUF001` to per-file-ignores for `tests/*` in `pyproject.toml`.

**Rationale**:
- RUF001 fires on 3 Cyrillic characters: `Н`, `А`, `И` in `tests/unit/indexing/operations/test_noun_phrase_factory.py:65-67`
- These are intentional test assertions for Cyrillic stop words (`"И"`, `"НА"`, `"ЧТО"`, `"ИЛИ"`) — not copy-paste errors
- The `stop_words.py` file already has `RUF001` in per-file-ignores (`pyproject.toml:232`)
- Adding to `tests/*` is consistent and covers all future Cyrillic test assertions
- More maintainable than Unicode escapes or per-line noqa comments

**Alternatives considered**:
- `# noqa: RUF001` on each affected line — repetitive
- Unicode escapes (`\u041d`) — less readable, hurts maintainability
- Exclude all of `tests/` from RUF001 — same as per-file-ignores approach, more explicit
- Don't suppress — forces test changes that make assertions harder to read

### 4. graphrag-cache and graphrag-llm pyright type errors

**Status**: Not present in current CI. The 27 errors originally documented in `packages_todos.md` (graphrag-cache missing, pyright type expressions in graphrag-llm) have already been resolved by prior feature work (P2 LiteLLM→OpenAI, P3 HuggingFace tokenizer).

**Verification**: `uv run pyright` shows only 6 errors (all tokenizers), confirming these were auto-fixed.

## Summary

| Error | Root Cause | Fix |
|---|---|---|
| 6× `reportMissingImports: tokenizers` | `tokenizers` in optional extra, not installed by `uv sync` | Move to base `dependencies` in `graphrag-llm/pyproject.toml` |
| 1× `SLF001` on `_nltk_language` | Test accesses private member of SentenceChunker | Add `SLF001` to `tests/*` per-file-ignores in root `pyproject.toml` |
| 2× `RUF001` Cyrillic | Test assertions contain Cyrillic stop words | Add `RUF001` to `tests/*` per-file-ignores in root `pyproject.toml` |
