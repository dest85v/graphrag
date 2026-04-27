# Feature Specification: CLI Index/Update Overrides

**Feature Branch**: `014-index-cli-overrides`  
**Created**: 2026-04-27  
**Status**: Draft  
**Input**: User description: "P1 — Добавить CLI overrides для index/update команд"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Override config values at index time (Priority: P1)

A user wants to run the indexing pipeline without modifying the `settings.yaml` file, for example to temporarily change the model, API key, or output directory for a single run.

**Why this priority**: This is the core use case — it brings `index`/`update` commands to parity with `query` commands, which already support `--data`-driven overrides. Without this, users must edit config files or create wrapper scripts for every configuration variation.

**Independent Test**: Can be fully tested by running `graphrag index --set <key>=<value>` on a project with a valid `settings.yaml` and verifying the override is applied to the loaded config before pipeline execution.

**Acceptance Scenarios**:

1. **Given** a project with `settings.yaml` containing `completion_models.default.model: gpt-3.5-turbo`, **When** user runs `graphrag index --set completion_models.default.model=gpt-4o`, **Then** the pipeline executes with `gpt-4o` as the model
2. **Given** a project with `settings.yaml`, **When** user runs `graphrag index --set output_storage.base_dir=/tmp/custom_output --set cache.type=Noop`, **Then** both overrides are applied simultaneously
3. **Given** a project with `settings.yaml`, **When** user runs `graphrag index --set` with a non-existent nested path like `nonexistent.deep.path=value`, **Then** the override creates/merges the nested structure recursively

---

### User Story 2 — Override config values at update time (Priority: P1)

A user wants to run an incremental update with different config values (e.g., different embedding model or output directory) without changing the base configuration.

**Why this priority**: `update` is a distinct workflow from `index` (it applies to an existing graph). Users need the same override flexibility for updates as they do for full indexing.

**Independent Test**: Can be fully tested by running `graphrag update --set <key>=<value>` on an existing indexed project and verifying the override is applied.

**Acceptance Scenarios**:

1. **Given** an existing index at `./output`, **When** user runs `graphrag update --set output_storage.base_dir=./update_output`, **Then** the update writes results to `./update_output` instead of the config's default
2. **Given** an existing index, **When** user runs `graphrag update` without overrides, **Then** the behavior is unchanged from current (no regression)

---

### User Story 3 — Discover available overrides via help (Priority: P2)

A user wants to understand what override keys are supported without reading source code or documentation.

**Why this priority**: Improves discoverability and reduces support burden. Users can run `--help` and see the new flag with examples.

**Independent Test**: Can be tested by running `graphrag index --help` and `graphrag update --help` and verifying the `--set` flag appears with a descriptive help string.

**Acceptance Scenarios**:

1. **Given** the feature is implemented, **When** user runs `graphrag index --help`, **Then** output includes `--set` flag with description and example usage
2. **Given** the feature is implemented, **When** user runs `graphrag update --help`, **Then** output includes `--set` flag with description and example usage

---

### Edge Cases

- What happens when `--set` is used with a value containing `=` signs (e.g., `--set api_key=sk=test=value`)? → Only the first `=` splits key from value; remaining `=` are part of the value.
- What happens when `--set` references a deeply nested key that doesn't exist in config and intermediate dicts are missing? → The config merge creates intermediate structures automatically.
- What happens when multiple `--set` flags conflict (e.g., `--set foo.bar=1 --set foo.bar=2`)? → Last flag wins (subsequent merges overwrite earlier values for the same leaf key).
- What happens when `--set` is used with an empty key or empty value? → Empty key is rejected with a clear error; empty value is allowed (sets the key to an empty string).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `index` CLI command MUST accept one or more `--set key=value` flags
- **FR-002**: The `update` CLI command MUST accept one or more `--set key=value` flags
- **FR-003**: Override keys MUST support dot-notation for nested config paths (e.g., `completion_models.default.model=gpt-4o`)
- **FR-004**: Multiple `--set` flags MUST be supported in a single command invocation
- **FR-005**: Overrides MUST be recursively merged into the loaded config, creating nested structures as needed
- **FR-006**: The `--set` flag MUST split on the first `=` only, preserving `=` characters in values
- **FR-007**: Empty override keys MUST produce a clear error message
- **FR-008**: The `index` and `update` command handlers MUST receive the overrides dict and pass it to the configuration loader
- **FR-009**: The CLI framework MUST parse `--set` arguments into a structured dict before passing to command handlers

### Key Entities *(include if feature involves data)*

- **CLI Override Map**: A nested dict structure built from `--set key=value` flags, using dot-notation keys to produce nested dicts for config merging. Example: `--set a.b=1 --set a.c=2` → `{"a": {"b": "1", "c": "2"}}`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can override any nested config field via a single `--set` flag on `index` or `update` commands
- **SC-002**: Multiple `--set` flags applied simultaneously produce the correct merged config (verified by dry-run output)
- **SC-003**: Existing `index` and `update` workflows produce identical results with and without overrides (no regression)
- **SC-004**: `graphrag index --help` and `graphrag update --help` display the `--set` flag with clear documentation

## Assumptions

- The existing config loading mechanism correctly handles nested dict merging for all config field types
- Override values are treated as strings (consistent with CLI argument semantics); the config validation layer handles type coercion during model instantiation
- The feature does not modify the config loading function's public API — only the command callers and the CLI layer
- The `--set` flag follows the same pattern as other CLI override mechanisms (e.g., Docker `--env`, Helm `--set`)
