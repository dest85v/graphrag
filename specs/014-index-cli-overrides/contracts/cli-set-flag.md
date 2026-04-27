# Contract: `graphrag index --set` Flag

## Interface

CLI flag added to `graphrag index` and `graphrag update` commands.

## Signature

```
--set KEY=VALUE   Override a configuration value (repeatable)
```

## Arguments

| Argument | Type | Required | Repeatable | Default |
|---|---|---|---|---|
| `KEY` | string (dot-notation path) | Yes | N/A | N/A |
| `VALUE` | string | Yes | N/A | N/A |

## Behavior

- Each `--set` flag produces one entry in the config override map
- Multiple `--set` flags accumulate into a single override map
- The override map is merged into the loaded config before Pydantic validation
- Dot-notation in KEY creates nested config structure (e.g., `a.b.c` → `{"a": {"b": {"c": VALUE}}}`)

## Examples

```bash
# Override a top-level field
graphrag index --set cache.type=Noop

# Override a nested field
graphrag index --set completion_models.default.model=gpt-4o

# Multiple overrides
graphrag update --set output_storage.base_dir=./out --set cache.type=Noop

# Value containing = sign
graphrag index --set completion_models.default.api_key=sk=test=value123

# Empty value
graphrag index --set some_field=
```

## Error Cases

| Input | Error |
|---|---|
| `--set =value` | "Override key must not be empty" |
| `--set noequals` | "Invalid --set format: expected key=value" |
| `--set a.b.c=invalid_value` | Passes CLI parsing; Pydantic validation error if type mismatch |

## Compatibility

- Backward-compatible: no `--set` flags → identical behavior to pre-feature
- Works with all existing `graphrag index` and `graphrag update` flags
- Does not affect `graphrag query` (which has its own override mechanism via `--data`)
