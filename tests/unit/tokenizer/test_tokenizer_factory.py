# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for create_tokenizer() factory with HuggingFace backend."""

import tempfile
from pathlib import Path

import graphrag_llm.tokenizer.huggingface_tokenizer  # noqa: F401
from graphrag_llm.config import TokenizerConfig, TokenizerType
from graphrag_llm.tokenizer import HuggingFaceTokenizer, create_tokenizer
from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers


def _create_local_tokenizer_json():
    """Helper to create a temporary tokenizer.json file."""
    tokenizer = Tokenizer(models.BPE())
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)
    tokenizer.decoder = decoders.ByteLevel()

    corpus = ["Hello world test"]
    temp_corpus: str | None = None
    tokenizer_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write("\n".join(corpus).encode())
            temp_corpus = f.name

        tokenizer.train([temp_corpus], trainer=trainers.BpeTrainer(vocab_size=50))

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tokenizer_path = f.name

        tokenizer.save(tokenizer_path, pretty=True)
        return tokenizer_path, temp_corpus
    except Exception:
        if temp_corpus is not None:
            Path(temp_corpus).unlink(missing_ok=True)
        raise


def test_create_huggingface_tokenizer_from_local_json() -> None:
    """Test that create_tokenizer with HuggingFace type returns a HuggingFaceTokenizer."""
    tokenizer_path, temp_corpus = _create_local_tokenizer_json()

    try:
        config = TokenizerConfig(
            type=TokenizerType.HuggingFace,
            model_id=tokenizer_path,
        )
        tokenizer_instance = create_tokenizer(config)

        assert isinstance(tokenizer_instance, HuggingFaceTokenizer)
        tokens = tokenizer_instance.encode("Hello world")
        assert isinstance(tokens, list)
        assert len(tokens) > 0

    finally:
        Path(temp_corpus).unlink(missing_ok=True)
        Path(tokenizer_path).unlink(missing_ok=True)


def test_create_huggingface_tokenizer_returns_singleton() -> None:
    """Test that create_tokenizer returns the same instance for the same config (singleton scope)."""
    tokenizer_path, temp_corpus = _create_local_tokenizer_json()

    try:
        config = TokenizerConfig(
            type=TokenizerType.HuggingFace,
            model_id=tokenizer_path,
        )
        instance1 = create_tokenizer(config)
        instance2 = create_tokenizer(config)

        # Singleton scope — same instance
        assert instance1 is instance2

    finally:
        Path(temp_corpus).unlink(missing_ok=True)
        Path(tokenizer_path).unlink(missing_ok=True)
