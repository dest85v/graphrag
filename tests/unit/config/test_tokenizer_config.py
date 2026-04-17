# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Test tokenizer configuration loading."""

import pytest
from graphrag_llm.config import TokenizerConfig, TokenizerType


def test_tiktoken_tokenizer_validation() -> None:
    """Test that missing required parameters raise validation errors."""

    # Empty strings should raise
    with pytest.raises(
        ValueError,
        match="Either model_id or encoding_name must be specified for TikToken tokenizer\\.",
    ):
        _ = TokenizerConfig(
            type=TokenizerType.Tiktoken,
            model_id="",
            encoding_name="",
        )

    # Empty model_id alone should raise
    with pytest.raises(
        ValueError,
        match="Either model_id or encoding_name must be specified for TikToken tokenizer\\.",
    ):
        _ = TokenizerConfig(
            type=TokenizerType.Tiktoken,
            model_id="",
        )

    # Empty encoding_name alone should raise
    with pytest.raises(
        ValueError,
        match="Either model_id or encoding_name must be specified for TikToken tokenizer\\.",
    ):
        _ = TokenizerConfig(
            type=TokenizerType.Tiktoken,
            encoding_name="",
        )

    # passes validation - model_id provided
    _ = TokenizerConfig(
        type=TokenizerType.Tiktoken,
        model_id="openai/gpt-4o",
    )

    # passes validation - encoding_name provided
    _ = TokenizerConfig(
        type=TokenizerType.Tiktoken,
        encoding_name="o200k-base",
    )


def test_default_tokenizer_type() -> None:
    """Test that the default tokenizer type is Tiktoken."""
    config = TokenizerConfig()
    assert config.type == TokenizerType.Tiktoken
