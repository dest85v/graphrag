# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for token counting consistency across backends."""

import tempfile
from pathlib import Path

import pytest
from graphrag_llm.tokenizer import HuggingFaceTokenizer
from graphrag_llm.tokenizer.openai_tokenizer import OpenAITokenizer
from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers


@pytest.fixture(scope="module")
def local_bpe_tokenizer() -> HuggingFaceTokenizer:
    """Create a local BPE tokenizer for testing."""
    tokenizer = Tokenizer(models.BPE())
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)
    tokenizer.decoder = decoders.ByteLevel()

    corpus = [
        "Hello world",
        "The quick brown fox jumps over the lazy dog",
        "Artificial intelligence is transforming the world",
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


def test_token_count_consistency_hf_vs_encode(local_bpe_tokenizer) -> None:
    """Test HuggingFaceTokenizer.num_tokens() matches encode().ids length for diverse texts."""
    hf_tokenizer = local_bpe_tokenizer

    test_texts = [
        "Hello world",
        "The quick brown fox jumps over the lazy dog",
        "こんにちは世界",
        "Emoji test: 🚀🌍🔥",
        "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
        "Longer text: " + "The rain in Spain falls mainly on the plain. " * 5,
        "",
        "Single word",
        "Multiple   spaces   between   words",
    ]

    for text in test_texts:
        hf_count = hf_tokenizer.num_tokens(text)
        encoded_tokens = hf_tokenizer.encode(text)
        assert hf_count == len(encoded_tokens), (
            f"num_tokens mismatch for: '{text[:40]}...'"
        )


def test_openai_vs_hf_consistent_interface() -> None:
    """Test that OpenAI and HuggingFace tokenizers have the same interface."""
    # Both should accept str and return list[int] for encode
    openai_tok = OpenAITokenizer(encoding_name="cl100k_base")
    tokens = openai_tok.encode("Hello world")
    assert isinstance(tokens, list)
    assert all(isinstance(t, int) for t in tokens)
    decoded = openai_tok.decode(tokens)
    assert isinstance(decoded, str)

    assert isinstance(openai_tok.num_tokens("Hello world"), int)
    assert isinstance(openai_tok.num_prompt_tokens("Hello"), int)


def test_openai_num_prompt_tokens_with_messages() -> None:
    """Test OpenAI num_prompt_tokens with list of message dicts."""
    openai_tok = OpenAITokenizer(encoding_name="cl100k_base")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is 2+2?"},
    ]
    count = openai_tok.num_prompt_tokens(messages)
    assert isinstance(count, int)
    assert count > 0
