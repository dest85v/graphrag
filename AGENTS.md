# GraphRAG — Developer Quick Reference

## Repo at a Glance

- **Monorepo** managed by `uv` (workspace members in `packages/`): 8 packages: `graphrag`, `graphrag-common`, `graphrag-chunking`, `graphrag-input`, `graphrag-storage`, `graphrag-cache`, `graphrag-llm`, `graphrag-vectors`.
- **Python 3.11–3.13** only. Install deps with `uv sync`.
- **Task runner**: `poe` (poethepoet), invoked via `uv run poe <task>`.

## Commands

| Purpose | Command |
|---|---|
| Install deps | `uv sync` |
| Full check (format + lint + typecheck) | `uv run poe check` |
| Fix lint / formatting | `uv run poe fix` or `uv run poe fix_unsafe` |
| Run formatter only | `uv run poe format` |
| Build packages | `uv build --all-packages` |
| All tests + coverage | `uv run poe test` |
| Unit / integration / smoke / notebook / verbs | `uv run poe test_unit`, `test_integration`, `test_smoke`, `test_notebook`, `test_verbs` |
| Run a single test | `uv run poe test_only "<pattern>"` |
| Run GraphRAG CLI | `uv run poe index`, `poe query`, `poe prompt_tune`, etc. |
| Serve docs | `uv run poe serve_docs` |

## Testing

- `pytest` with `asyncio_mode = "auto"`, 1000s default timeout.
- Test suites: `tests/unit`, `tests/integration`, `tests/smoke`, `tests/notebook`, `tests/verbs`.
- Smoke and some unit tests use **Azurite** (emulated Azure storage). Start with `./scripts/start-azurite.sh`.
- Slow tests are gated behind `--run_slow` CLI option.

## Linting / Formatting / Types

- **Ruff** for lint and format (`target-version = "py310"`, docstring code in format).
- **pyright** for type checking. Configured in `[tool.pyright]` in root `pyproject.toml`.
- Run `uv run poe check` before committing — CI runs this exact sequence.

## Versioning / Releases

- Uses **semversioner**. Every PR must include a semversioner change entry:
  ```
  uv run semversioner add-change -t <major|minor|patch> -d "<description>."
  ```
- CI validates semversioner JSON in `.semversioner/`.
- Between minor version bumps, run `graphrag init --root [path] --force` to update config formats.

## Contributing

- Fork → branch → make changes → pass `poe check` + tests → `semversioner add-change` → PR.
- See `CONTRIBUTING.md` for full process and CLA info.
- Security issues → report to MSRC, not GitHub issues (`SECURITY.md`).

## Active Technologies
- Python 3.11–3.13 (per project `requires-python = ">=3.11,<3.14"`) + `openai~=1.60` (replaces `litellm==1.82.6`), `tiktoken~=0.8` (already transitive, make direct), `azure-identity~=1.25` (unchanged) (001-litellm-to-openai)
- N/A — pure library package (001-litellm-to-openai)
- Python 3.11–3.13 (per project `requires-python = ">=3.11,<3.14"`) + `qdrant-client>=1.7.0,<1.18.0` (optional `qdrant` extra in `graphrag-vectors`) (003-003-qdrant-vector)
- Qdrant (external, remote or local via Docker) (003-003-qdrant-vector)
- Python 3.11–3.13 (per `requires-python = ">=3.11,<3.14"`) + `spacy~=3.8` (already in `packages/graphrag/pyproject.toml:54`), `nltk~=3.9` (already in pyproject.toml, will be reduced) (004-textblob-to-spacy)
- Python 3.11–3.13 (per project `requires-python = ">=3.11,<3.14"`) + `spacy~=3.8` (NLP-модели), `pydantic` (config validation) (006-language-aware-nlp-factory)
- N/A — чистая бизнес-логика (006-language-aware-nlp-factory)
- Python 3.11–3.13 (per workspace `requires-python`) + `nltk~=3.9` (already in `packages/graphrag/pyproject.toml:49`), `pydantic~=2.10` (in `graphrag-chunking`) (007-multilingual-sentence-tokenizer)
- N/A (no data layer changes) (007-multilingual-sentence-tokenizer)

## Recent Changes
- 001-litellm-to-openai: Added Python 3.11–3.13 (per project `requires-python = ">=3.11,<3.14"`) + `openai~=1.60` (replaces `litellm==1.82.6`), `tiktoken~=0.8` (already transitive, make direct), `azure-identity~=1.25` (unchanged)
