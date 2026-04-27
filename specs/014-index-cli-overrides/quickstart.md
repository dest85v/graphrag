# Quickstart: CLI Index/Update Overrides

## Overview

Use `--set key=value` to override any configuration field for a single `graphrag index` or `graphrag update` run, without editing `settings.yaml`.

## Basic Usage

### Override a single config field

```bash
graphrag index --set completion_models.default.model=gpt-4o
```

This runs the indexing pipeline with `gpt-4o` instead of whatever model is in `settings.yaml`.

### Override multiple fields

```bash
graphrag index \
  --set completion_models.default.model=gpt-4o \
  --set output_storage.base_dir=/tmp/my_index \
  --set cache.type=Noop
```

All overrides are applied simultaneously.

### Use with `update` command

```bash
graphrag update --set output_storage.base_dir=./update_output
```

### Override nested config paths

```bash
graphrag index --set chunking.size=5000 --set chunking.overlap=200
```

## Key Rules

- **Split on first `=`**: `--set api_key=sk=test=value` sets the key `api_key` to `sk=test=value`
- **Empty key is an error**: `--set =value` produces an error message
- **Empty value is allowed**: `--set key=` sets the field to an empty string
- **Last flag wins**: `--set a.b=1 --set a.b=2` → the final value is `2`
- **All values are strings**: Type coercion is handled by the config model during validation

## No Overrides (Default Behavior)

Running `graphrag index` or `graphrag update` without any `--set` flags uses the config from `settings.yaml` exactly as before. There is no regression in existing behavior.

## Help

```bash
graphrag index --help
graphrag update --help
```

Both commands display the `--set` flag with description and examples.
