# Implementation Plan: CLI Index/Update Overrides

**Branch**: `014-index-cli-overrides` | **Date**: 2026-04-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/014-index-cli-overrides/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add `--set key=value` CLI flags to the `index` and `update` commands in GraphRAG, bringing them to parity with the existing `query` command which already supports `--data`-driven config overrides. The implementation adds a variadic `--set` argument to both typer commands, converts the list of `key=value` strings into a nested dict via dot-notation parsing, and passes it to `load_config()` as `cli_overrides`. No new dependencies, no API changes to `load_config()`'s public signature, and zero regressions in existing behavior.

## Technical Context

**Language/Version**: Python 3.11–3.13 (per workspace `requires-python`)  
**Primary Dependencies**: `typer` (CLI framework), `pydantic` (config validation)  
**Storage**: N/A — pure CLI/config manipulation, no new data layer  
**Testing**: `pytest` with `asyncio_mode = "auto"`, gated slow tests via `--run_slow`  
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows)  
**Project Type**: CLI tool / library  
**Performance Goals**: N/A — this is a configuration injection layer with O(n) overhead where n = number of --set flags (typically < 10)  
**Constraints**: Must not modify `load_config()` public API; must not break existing `index`/`update` behavior when no `--set` flags are used  
**Scale/Scope**: 3 files modified (2 CLI handlers + 1 typer command definitions), ~80 lines of new code across CLI layer

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Constitution Principle | Compliance | Notes |
|---|---|---|
| I. Library-First Architecture | PASS | No new library; modifies existing CLI layer in `graphrag` package |
| II. CLI Interface | PASS | Adds flags to existing CLI entry points — enhances, not changes, the interface |
| III. Test-First (NON-NEGOTIABLE) | PASS | Tests will be written before implementation (Red-Green-Refactor cycle) |
| IV. Integration Testing | PASS | Will include unit tests for `--set` parsing + integration test for full `index` flow with overrides |
| V. Versioning & Change Management | PASS | Will include semversioner PATCH entry (backward-compatible addition) |

**Result**: All gates pass. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/014-index-cli-overrides/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (trivial — no unknowns)
├── data-model.md        # Phase 1 output (trivial — override map structure)
├── quickstart.md        # Phase 1 output (usage examples)
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
packages/graphrag/graphrag/cli/
├── main.py              # MODIFIED: Add --set arg to _index_cli and _update_cli
└── index.py             # MODIFIED: Accept cli_overrides param in index_cli() and update_cli()

packages/graphrag/tests/unit/cli/
└── test_cli_overrides.py # CREATED: Unit tests for --set parsing and override application

packages/graphrag/tests/integration/
└── test_index_overrides.py # CREATED: Integration test for index pipeline with --set overrides
```

**Structure Decision**: The feature touches only the `graphrag` package's CLI layer. No new packages are created. The `--set` flag is added to existing typer commands (`_index_cli` and `_update_cli` in `main.py`), and the handler functions (`index_cli` and `update_cli` in `index.py`) are extended to accept and forward `cli_overrides`.

## Complexity Tracking

Not applicable — no constitution violations. This is a minimal, low-risk addition following existing patterns from the `query` command.
