# Data Model: CLI Override Map

## Overview

The CLI override map is the internal data structure that holds configuration overrides passed via `--set key=value` flags. It is a nested dictionary built from dot-notation keys and passed to the config loader for merging.

## Entity: CLIOverrideMap

**Purpose**: Represents the parsed result of all `--set` arguments on a single CLI invocation.

### Structure

```
CLIOverrideMap = dict[str, Any]
```

The type is a nested dictionary where keys are config field paths and values are strings (CLI arguments are always strings — type coercion is handled by the Pydantic config model during instantiation).

### Example

Input: `--set a.b=1 --set a.c=2 --set x.y.z=hello`

```json
{
  "a": {
    "b": "1",
    "c": "2"
  },
  "x": {
    "y": {
      "z": "hello"
    }
  }
}
```

### Validation Rules

| Rule | Description |
|---|---|
| Non-empty key | `--set =value` or `--set =` is rejected with error |
| Contains `=` | `--set key_without_equals` is rejected with error |
| Split on first `=` | `--set api_key=sk=test=value` → key=`api_key`, value=`sk=test=value` |
| Empty value allowed | `--set key=` → key maps to empty string `""` |
| Last-wins for same key | `--set a.b=1 --set a.b=2` → `{"a": {"b": "2"}}` |

### Relationship to Config Loading

The `CLIOverrideMap` is passed as the `overrides` parameter to `load_config()`, which merges it into the parsed YAML/JSON config using `_recursive_merge_dicts()`. The merged dict is then passed to `GraphRagConfig(**merged_dict)` for Pydantic validation.

### State Transitions

Not applicable. The override map is immutable after construction — it is created once at CLI argument parsing time, passed through the handler functions, and consumed by `load_config()`.
