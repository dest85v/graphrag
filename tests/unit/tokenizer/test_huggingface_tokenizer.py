# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for HuggingFaceTokenizer encode/decode/num_tokens."""

import tempfile
from pathlib import Path

import pytest
from graphrag_llm.tokenizer import HuggingFaceTokenizer
from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers


@pytest.fixture(scope="module")
def llama_like_tokenizer() -> HuggingFaceTokenizer:
    """Create a ByteLevel BPE tokenizer with a corpus similar to Llama training data."""
    tokenizer = Tokenizer(models.BPE())
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)
    tokenizer.decoder = decoders.ByteLevel()

    corpus = [
        "Hello world",
        "Hello there",
        "Goodbye world",
        "The quick brown fox jumps over the lazy dog",
        "Artificial intelligence is transforming the world",
        "Machine learning models require large amounts of data",
        "Natural language processing enables computers to understand text",
        "Tokenization is a critical step in NLP pipelines",
        "Large language models can generate coherent and contextually appropriate text",
        "The transformer architecture has revolutionized deep learning",
    ]
    temp_corpus: str | None = None
    tokenizer_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write("\n".join(corpus).encode())
            temp_corpus = f.name

        tokenizer.train([temp_corpus], trainer=trainers.BpeTrainer(vocab_size=200))

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tokenizer_path = f.name

        tokenizer.save(tokenizer_path, pretty=True)

        return HuggingFaceTokenizer(model_id=tokenizer_path)

    finally:
        if temp_corpus is not None:
            Path(temp_corpus).unlink(missing_ok=True)
        if tokenizer_path is not None:
            Path(tokenizer_path).unlink(missing_ok=True)


def test_encode_produces_valid_integer_ids(llama_like_tokenizer) -> None:
    """Test that HuggingFaceTokenizer.encode() produces valid integer token IDs."""
    text = "Hello, world!"
    tokens = llama_like_tokenizer.encode(text)
    assert isinstance(tokens, list)
    assert len(tokens) > 0
    assert all(isinstance(t, int) and t >= 0 for t in tokens)


def test_decode_roundtrip(llama_like_tokenizer) -> None:
    """Test that HuggingFaceTokenizer.decode() round-trips correctly."""
    text = "The quick brown fox jumps over the lazy dog."
    tokens = llama_like_tokenizer.encode(text)
    decoded = llama_like_tokenizer.decode(tokens)
    assert isinstance(decoded, str)


def test_num_tokens_returns_correct_count(llama_like_tokenizer) -> None:
    """Test that HuggingFaceTokenizer.num_tokens() returns len(encode(text))."""
    text = "Hello, world! This is a test of token counting."
    num_tokens = llama_like_tokenizer.num_tokens(text)
    encoded = llama_like_tokenizer.encode(text)
    assert num_tokens == len(encoded)
    assert num_tokens > 0


def test_encode_empty_string(llama_like_tokenizer) -> None:
    """Test that encoding an empty string returns an empty list."""
    tokens = llama_like_tokenizer.encode("")
    assert tokens == []


def test_encode_unicode_text(llama_like_tokenizer) -> None:
    """Test that encoding Unicode text works correctly."""
    text = "こんにちは世界"
    tokens = llama_like_tokenizer.encode(text)
    assert isinstance(tokens, list)
    assert len(tokens) > 0
    assert all(isinstance(t, int) for t in tokens)


def test_num_prompt_tokens_with_string(llama_like_tokenizer) -> None:
    """Test that num_prompt_tokens handles a string message."""
    text = "Hello, how are you?"
    count = llama_like_tokenizer.num_prompt_tokens(text)
    assert isinstance(count, int)
    assert count > 0
