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


def test_huggingface_tokenizer_validation_valid_model_id() -> None:
    """Test that HuggingFace tokenizer with valid model_id passes validation."""
    config = TokenizerConfig(
        type=TokenizerType.HuggingFace,
        model_id="meta-llama/Llama-3.1-8B-Instruct",
    )
    assert config.type == TokenizerType.HuggingFace
    assert config.model_id == "meta-llama/Llama-3.1-8B-Instruct"


def test_huggingface_tokenizer_validation_empty_model_id_raises() -> None:
    """Test that HuggingFace tokenizer with empty model_id raises ValueError."""
    with pytest.raises(
        ValueError,
        match="model_id must be specified for HuggingFace tokenizer",
    ):
        _ = TokenizerConfig(
            type=TokenizerType.HuggingFace,
            model_id="",
        )


def test_huggingface_tokenizer_validation_missing_model_id_raises() -> None:
    """Test that HuggingFace tokenizer without model_id raises ValueError."""
    with pytest.raises(
        ValueError,
        match="model_id must be specified for HuggingFace tokenizer",
    ):
        _ = TokenizerConfig(type=TokenizerType.HuggingFace)


def test_huggingface_tokenizer_whitespace_model_id_raises() -> None:
    """Test that HuggingFace tokenizer with whitespace-only model_id raises ValueError."""
    with pytest.raises(
        ValueError,
        match="model_id must be specified for HuggingFace tokenizer",
    ):
        _ = TokenizerConfig(
            type=TokenizerType.HuggingFace,
            model_id="   ",
        )


def test_huggingface_tokenizer_local_file_path() -> None:
    """Test that HuggingFace tokenizer accepts a local tokenizer.json path."""
    config = TokenizerConfig(
        type=TokenizerType.HuggingFace,
        model_id="/path/to/tokenizer.json",
    )
    assert config.model_id == "/path/to/tokenizer.json"
