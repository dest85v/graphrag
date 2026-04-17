# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for get_tokenizer() automatic tokenizer routing."""

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from graphrag.tokenizer.get_tokenizer import _is_openai_model, get_tokenizer
from graphrag_llm.config import TokenizerType
from graphrag_llm.tokenizer.openai_tokenizer import OpenAITokenizer

if TYPE_CHECKING:
    from graphrag_llm.config import ModelConfig


def _make_model_config(model_name: str, provider: str = "openai") -> "ModelConfig":
    """Helper to create a ModelConfig with a test API key."""
    from graphrag_llm.config import ModelConfig

    return ModelConfig(
        model_provider=provider,
        model=model_name,
        api_key="test-key-for-unit-tests",
    )


def test_is_openai_model_gpt4o() -> None:
    """Test OpenAI model detection for gpt-4o."""
    assert _is_openai_model("gpt-4o") is True
    assert _is_openai_model("openai/gpt-4o") is True
    assert _is_openai_model("azure/gpt-4o") is True


def test_is_openai_model_gpt4() -> None:
    """Test OpenAI model detection for gpt-4."""
    assert _is_openai_model("gpt-4") is True
    assert _is_openai_model("openai/gpt-4") is True


def test_is_openai_model_gpt35() -> None:
    """Test OpenAI model detection for gpt-3.5."""
    assert _is_openai_model("gpt-3.5-turbo") is True
    assert _is_openai_model("gpt-3.5") is True
    assert _is_openai_model("openai/gpt-3.5-turbo") is True


def test_is_openai_model_embedding() -> None:
    """Test OpenAI model detection for embedding models."""
    assert _is_openai_model("text-embedding-3-large") is True
    assert _is_openai_model("text-embedding-ada-002") is True
    assert _is_openai_model("text-embedding-3-small") is True


def test_is_openai_model_not_openai() -> None:
    """Test non-OpenAI model detection."""
    assert _is_openai_model("meta-llama/Llama-3.1-8B-Instruct") is False
    assert _is_openai_model("mistralai/Mistral-7B-Instruct-v0.3") is False
    assert _is_openai_model("Qwen/Qwen2.5-7B-Instruct") is False
    assert _is_openai_model("google/gemma-2-2b-it") is False


# ---- Integration: get_tokenizer() routing ----


def test_get_tokenizer_openai_gpt4o_returns_tiktoken() -> None:
    """Test that gpt-4o model returns tiktoken tokenizer."""
    config = _make_model_config("gpt-4o")
    tokenizer = get_tokenizer(model_config=config)
    assert isinstance(tokenizer, OpenAITokenizer)


def test_get_tokenizer_openai_text_embedding_returns_tiktoken() -> None:
    """Test that text-embedding-3-large returns tiktoken tokenizer."""
    config = _make_model_config("text-embedding-3-large")
    tokenizer = get_tokenizer(model_config=config)
    assert isinstance(tokenizer, OpenAITokenizer)


def test_get_tokenizer_llama_routes_to_huggingface_config() -> None:
    """Test that Llama model routes to HuggingFace config (mocks actual Hub download)."""
    config = _make_model_config("meta-llama/Llama-3.1-8B-Instruct")

    with patch("graphrag.tokenizer.get_tokenizer.create_tokenizer") as mock_create:
        mock_create.return_value = MagicMock()
        get_tokenizer(model_config=config)
        # Verify create_tokenizer was called with HuggingFace config
        call_args = mock_create.call_args
        assert call_args is not None
        args = call_args.args if call_args.args else []
        called_config = args[0] if args else call_args.kwargs.get("tokenizer_config")
        assert called_config is not None
        assert called_config.type == TokenizerType.HuggingFace
        assert "Llama" in called_config.model_id


def test_get_tokenizer_unknown_routes_to_huggingface_config() -> None:
    """Test that unknown models route to HuggingFace config (mocks actual Hub download)."""
    config = _make_model_config("unknown-model-xyz")

    with patch("graphrag.tokenizer.get_tokenizer.create_tokenizer") as mock_create:
        mock_create.return_value = MagicMock()
        get_tokenizer(model_config=config)
        call_args = mock_create.call_args
        assert call_args is not None
        args = call_args.args if call_args.args else []
        called_config = args[0] if args else call_args.kwargs.get("tokenizer_config")
        assert called_config is not None
        assert called_config.type == TokenizerType.HuggingFace
        assert called_config.model_id == "unknown-model-xyz"


def test_get_tokenizer_no_model_config_uses_default_encoding() -> None:
    """Test that no model config falls back to default encoding model."""
    tokenizer = get_tokenizer()
    assert isinstance(tokenizer, OpenAITokenizer)


def test_get_tokenizer_custom_encoding_model() -> None:
    """Test that custom encoding_model uses tiktoken with specified encoding."""
    tokenizer = get_tokenizer(encoding_model="r50k_base")
    assert isinstance(tokenizer, OpenAITokenizer)
