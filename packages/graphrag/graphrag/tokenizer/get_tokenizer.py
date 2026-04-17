# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Get Tokenizer."""

from graphrag_llm.config import ModelConfig, TokenizerConfig, TokenizerType
from graphrag_llm.tokenizer import Tokenizer, create_tokenizer

from graphrag.config.defaults import ENCODING_MODEL


def get_tokenizer(
    model_config: "ModelConfig | None" = None,
    encoding_model: str | None = None,
) -> Tokenizer:
    """
    Get the tokenizer for the given model configuration or fallback to a tiktoken based tokenizer.

    Args
    ----
        model_config: LanguageModelConfig, optional
            The model configuration. If provided, use an OpenAI tokenizer based on the model name.
            Otherwise, use a tiktoken tokenizer with the specified encoding model.
        encoding_model: str, optional
            A tiktoken encoding model to use if no model configuration is provided. Only used if a
            model configuration is not provided.

    Returns
    -------
        An instance of a Tokenizer.
    """
    if model_config is not None:
        return create_tokenizer(
            TokenizerConfig(
                type=TokenizerType.Tiktoken,
                model_id=f"{model_config.model_provider}/{model_config.model}",
            )
        )

    if encoding_model is None:
        encoding_model = ENCODING_MODEL
    return create_tokenizer(
        TokenizerConfig(
            type=TokenizerType.Tiktoken,
            encoding_name=encoding_model,
        )
    )
