# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for HuggingFaceTokenizer with local tokenizer.json files."""

import tempfile
from pathlib import Path

import pytest
from graphrag_llm.tokenizer import HuggingFaceTokenizer

hf = pytest.importorskip("tokenizers", reason="tokenizers library not installed")


def test_load_from_local_tokenizer_json() -> None:
    """Test that HuggingFaceTokenizer loads from a local tokenizer.json file."""
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

    # Create a simple BPE tokenizer in memory
    tokenizer = Tokenizer(models.BPE())
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)
    tokenizer.decoder = decoders.ByteLevel()

    # Train on a small corpus
    corpus = ["Hello world", "Hello there", "Goodbye world"]
    temp_corpus: str | None = None
    tokenizer_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write("\n".join(corpus).encode())
            temp_corpus = f.name

        tokenizer.train([temp_corpus], trainer=trainers.BpeTrainer(vocab_size=100))

        # Save tokenizer
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tokenizer_path = f.name

        tokenizer.save(tokenizer_path, pretty=True)

        # Now load via HuggingFaceTokenizer
        hf_tokenizer = HuggingFaceTokenizer(model_id=tokenizer_path)
        tokens = hf_tokenizer.encode("Hello world")
        assert isinstance(tokens, list)
        assert len(tokens) > 0

        decoded = hf_tokenizer.decode(tokens)
        assert isinstance(decoded, str)
        assert "Hello" in decoded or "hello" in decoded.lower()

        # Verify num_tokens
        count = hf_tokenizer.num_tokens("Hello world")
        assert count == len(tokens)

    finally:
        if temp_corpus is not None:
            Path(temp_corpus).unlink(missing_ok=True)
        if tokenizer_path is not None:
            Path(tokenizer_path).unlink(missing_ok=True)


def test_load_local_file_not_found() -> None:
    """Test that loading a non-existent local file raises ValueError."""
    with pytest.raises(ValueError, match="Failed to load tokenizer"):
        HuggingFaceTokenizer(model_id="/nonexistent/path/to/tokenizer.json")


def test_encode_emoji_text() -> None:
    """Test that encoding text with emojis works without errors."""
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

    tokenizer = Tokenizer(models.BPE())
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)
    tokenizer.decoder = decoders.ByteLevel()

    corpus = ["Hello 🌍", "Hello 🚀", "Emoji test 🔥"]
    temp_corpus: str | None = None
    tokenizer_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write("\n".join(corpus).encode())
            temp_corpus = f.name

        tokenizer.train([temp_corpus], trainer=trainers.BpeTrainer(vocab_size=100))

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tokenizer_path = f.name

        tokenizer.save(tokenizer_path, pretty=True)

        hf_tokenizer = HuggingFaceTokenizer(model_id=tokenizer_path)
        tokens = hf_tokenizer.encode("Hello 🌍")
        assert isinstance(tokens, list)
        assert len(tokens) > 0

    finally:
        if temp_corpus is not None:
            Path(temp_corpus).unlink(missing_ok=True)
        if tokenizer_path is not None:
            Path(tokenizer_path).unlink(missing_ok=True)
