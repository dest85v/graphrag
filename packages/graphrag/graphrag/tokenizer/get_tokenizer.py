# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Get Tokenizer."""

from graphrag_llm.config import ModelConfig, TokenizerConfig, TokenizerType
from graphrag_llm.tokenizer import Tokenizer, create_tokenizer

from graphrag.config.defaults import ENCODING_MODEL

# Model name patterns that indicate OpenAI models → use tiktoken
_OPENAI_MODEL_PATTERNS = (
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
    "gpt-3.5",
    "text-embedding-ada-002",
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding",
    "cl100k_base",
)


def _is_openai_model(model_name: str) -> bool:
    """Check if a model name matches known OpenAI model patterns.

    Args
    ----
    model_name: str
        The model name to check (lowercase).

    Returns
    -------
    bool
        True if the model name matches an OpenAI pattern.
    """
    return any(pattern in model_name for pattern in _OPENAI_MODEL_PATTERNS)


def get_tokenizer(
    model_config: "ModelConfig | None" = None,
    encoding_model: str | None = None,
) -> Tokenizer:
    """
    Get the tokenizer for the given model configuration or fallback to a tiktoken based tokenizer.

    Automatically selects the tokenizer backend based on the model name:
    - OpenAI models → tiktoken (fast, cached encoding)
    - All other models → HuggingFace tokenizer (any model on HuggingFace Hub)

    Args
    ----
        model_config: LanguageModelConfig, optional
            The model configuration. If provided, auto-selects the tokenizer backend
            based on the model name. OpenAI models use tiktoken; all others use
            the HuggingFace tokenizer.
        encoding_model: str, optional
            A tiktoken encoding model to use if no model configuration is provided.
            Only used if a model configuration is not provided.

    Returns
    -------
        An instance of a Tokenizer.
    """
    if model_config is not None:
        model_name = f"{model_config.model_provider}/{model_config.model}".lower()

        if _is_openai_model(model_name):
            return create_tokenizer(
                TokenizerConfig(
                    type=TokenizerType.Tiktoken,
                    model_id=f"{model_config.model_provider}/{model_config.model}",
                )
            )

        # Non-OpenAI model → HuggingFace tokenizer
        return create_tokenizer(
            TokenizerConfig(
                type=TokenizerType.HuggingFace,
                model_id=model_config.model,
            )
        )

    # Fallback: tiktoken with default encoding model
    if encoding_model is None:
        encoding_model = ENCODING_MODEL
    return create_tokenizer(
        TokenizerConfig(
            type=TokenizerType.Tiktoken,
            encoding_name=encoding_model,
        )
    )
