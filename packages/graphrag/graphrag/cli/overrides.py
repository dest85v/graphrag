# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""CLI override parsing utilities.

Provides dot-notation key parsing for --set CLI flags, converting
list of "key=value" strings into nested dicts compatible with
_recursive_merge_dicts in the config loading layer.
"""

from typing import Any


def parse_set_args(set_args: list[str]) -> dict[str, Any]:
    """Parse --set CLI arguments into a nested override dict.

    Each argument is a "key=value" string where key supports dot-notation
    for nested paths (e.g., "a.b.c") and value is everything after the
    first '=' sign (preserving additional '=' characters in the value).

    Empty keys are rejected with a SystemExit. Missing '=' produces an error.

    Parameters
    ----------
    set_args : list[str]
        List of "key=value" strings from CLI --set flags.

    Returns
    -------
    dict[str, Any]
        Nested dict structure for config merging.

    Examples
    --------
    >>> parse_set_args(["cache.type=Noop"])
    {'cache': {'type': 'Noop'}}
    >>> parse_set_args(["a.b=1", "a.c=2"])
    {'a': {'b': '1', 'c': '2'}}
    >>> parse_set_args(["api_key=sk=test=value"])
    {'api_key': 'sk=test=value'}
    """
    result: dict[str, Any] = {}

    for arg in set_args:
        if "=" not in arg:
            import typer

            typer.echo(f"Error: Invalid --set format: {arg!r}. Expected key=value.")
            raise SystemExit(1)

        key, _, value = arg.partition("=")
        if not key:
            import typer

            typer.echo("Error: Override key must not be empty.")
            raise SystemExit(1)

        # Build nested dict from dot-notation keys
        # ["a", "b", "c"] = "val" -> {"a": {"b": {"c": "val"}}}
        keys = key.split(".")
        nested: Any = value
        for k in reversed(keys):
            nested = {k: nested}

        # Merge into result (recursive merge for nested structures)
        result = _recursive_merge_dicts(result, nested)

    return result


def _recursive_merge_dicts(dest: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge src into dest, returning the merged dict.

    This is a non-destructive version of the _recursive_merge_dicts from
    graphrag_common.config.load_config — it returns a new dict rather than
    modifying in place.
    """
    merged = dict(dest)
    for key, value in src.items():
        if isinstance(value, dict):
            if key in merged and isinstance(merged[key], dict):
                merged[key] = _recursive_merge_dicts(merged[key], value)
            else:
                merged[key] = value
        else:
            merged[key] = value
    return merged
