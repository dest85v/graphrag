# Research: CLI Index/Update Overrides

## Decision: Reuse existing `cli_overrides` mechanism

**Rationale**: The `query` command already passes `cli_overrides` to `load_config()`. The `load_config()` function in `graphrag_common/config/load_config.py` accepts an optional `overrides: dict[str, Any]` parameter and merges it via `_recursive_merge_dicts()`. The only missing piece is the CLI flag parsing in `main.py` and the handler function signatures in `index.py`.

**Alternatives considered**:
1. **New CLI flag (`--override` vs `--set`)**: Evaluated both names. `--set` follows the convention of Docker, Helm, and Pulumi — more widely recognized. Adopted `--set`.
2. **JSON override file (`--overrides-file`)**: Would require file I/O and JSON parsing. Overkill for simple single-value overrides. Can be added later as an enhancement.
3. **Separate `--model`, `--api-key`, etc. flags**: Would require hardcoding every overrideable config field. `--set` with dot-notation is infinitely extensible.

## Decision: Dot-notation key parsing

**Rationale**: Dot-notation (`completion_models.default.model=gpt-4o`) is the simplest way to represent nested config paths. The existing `_recursive_merge_dicts()` already handles nested dict merging. A single helper function splits on `.` and builds the nested structure.

**Implementation approach**:
```python
def parse_set_args(args: list[str]) -> dict[str, Any]:
    result = {}
    for arg in args:
        if "=" not in arg:
            raise click.BadParameter(f"Invalid --set format: {arg!r}. Expected key=value.")
        key, _, value = arg.partition("=")
        if not key:
            raise click.BadParameter("Override key must not be empty.")
        keys = key.split(".")
        # Build nested dict: ["a", "b", "c"] = "val" → {"a": {"b": {"c": "val"}}}
        nested = value
        for k in reversed(keys):
            nested = {k: nested}
        # Merge into result
        result = _recursive_merge_dicts(result, nested)
    return result
```

**Note**: `typer` uses `click` under the hood; error handling will use `typer`'s built-in error messages.

## Decision: No changes to `load_config()` public API

**Rationale**: The `load_config()` function already accepts `overrides: dict[str, Any] | None`. No changes needed. The `index_cli()` and `update_cli()` functions currently call `load_config(root_dir=root_dir)` with no overrides — they will be updated to accept a `cli_overrides: dict[str, Any] | None = None` parameter and forward it.

## No additional dependencies

**Rationale**: The feature uses only existing dependencies: `typer` (for `--set` argument parsing) and the existing `_recursive_merge_dicts()` utility. No new packages needed.
