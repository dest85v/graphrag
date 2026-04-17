# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Test tokenizer type enum values."""

from graphrag_llm.config import TokenizerType


def test_tokenizer_type_tiktoken() -> None:
    """Test Tiktoken tokenizer type enum value."""
    assert TokenizerType.Tiktoken == "tiktoken"
    assert TokenizerType.Tiktoken.value == "tiktoken"


def test_tokenizer_type_huggingface() -> None:
    """Test HuggingFace tokenizer type enum value."""
    assert TokenizerType.HuggingFace == "huggingface"
    assert TokenizerType.HuggingFace.value == "huggingface"


def test_tokenizer_type_is_str_enum() -> None:
    """Test that tokenizer types are string enums."""
    assert isinstance(TokenizerType.Tiktoken, str)
    assert isinstance(TokenizerType.HuggingFace, str)


def test_tokenizer_type_comparison() -> None:
    """Test string comparison works with tokenizer types."""
    assert TokenizerType.Tiktoken == "tiktoken"
    assert TokenizerType.HuggingFace == "huggingface"
    assert TokenizerType.Tiktoken == "tiktoken"
    assert TokenizerType.HuggingFace == "huggingface"
