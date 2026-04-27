# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for the CLI overrides parser."""

import pytest
from graphrag.cli.overrides import parse_set_args


def test_parse_set_args_dot_notation_nesting():
    """Test that dot-notation keys create nested dict structure."""
    result = parse_set_args(["a.b.c=value"])
    assert result == {"a": {"b": {"c": "value"}}}


def test_parse_set_args_multiple_flags():
    """Test that multiple --set flags are merged into one nested dict."""
    result = parse_set_args(["a.b=1", "a.c=2", "x.y.z=hello"])
    assert result == {"a": {"b": "1", "c": "2"}, "x": {"y": {"z": "hello"}}}


def test_parse_set_args_equals_in_value():
    """Test that only the first = splits key from value."""
    result = parse_set_args(["api_key=sk=test=value123"])
    assert result == {"api_key": "sk=test=value123"}


def test_parse_set_args_empty_key_rejected():
    """Test that empty key produces a clear error."""
    with pytest.raises(SystemExit):
        parse_set_args(["=value"])


def test_parse_set_args_missing_equals_rejected():
    """Test that missing = produces a clear error."""
    with pytest.raises(SystemExit):
        parse_set_args(["noequals"])


def test_parse_set_args_last_wins_conflict():
    """Test that duplicate keys: last flag wins."""
    result = parse_set_args(["a.b=1", "a.b=2"])
    assert result == {"a": {"b": "2"}}


def test_parse_set_args_empty_value_allowed():
    """Test that empty value is allowed (key maps to empty string)."""
    result = parse_set_args(["key="])
    assert result == {"key": ""}


def test_parse_set_args_single_level_keys():
    """Test that single-level keys work without nesting."""
    result = parse_set_args(["cache.type=Noop", "output_storage.base_dir=/tmp/out"])
    assert result == {"cache": {"type": "Noop"}, "output_storage": {"base_dir": "/tmp/out"}}
