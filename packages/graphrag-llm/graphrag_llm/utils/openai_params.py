# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""OpenAI SDK parameter filtering utilities."""

import logging

log = logging.getLogger(__name__)

# OpenAI SDK supported params for chat.completions.create()
CHAT_COMPLETION_PARAMS: set[str] = {
    "model",
    "messages",
    "temperature",
    "top_p",
    "frequency_penalty",
    "presence_penalty",
    "max_tokens",
    "stop",
    "stream",
    "stream_options",
    "n",
    "logprobs",
    "top_logprobs",
    "response_format",
    "seed",
    "tools",
    "tool_choice",
    "parallel_tool_calls",
    "service_tier",
    "max_completion_tokens",
    "modalities",
    "prediction",
    "audio",
    "user",
    "reasoning_effort",
    "extra_headers",
}

# OpenAI SDK supported params for embeddings.create()
EMBEDDING_PARAMS: set[str] = {
    "model",
    "input",
    "encoding_format",
    "dimensions",
    "user",
}


def filter_completion_kwargs(kwargs: dict, model_id: str) -> dict:
    """Filter out params not supported by OpenAI SDK for this model.

    Replaces litellm's drop_params=True behavior. Unknown params are silently
    dropped and logged at debug level.

    Args
    ----
        kwargs: The keyword arguments to filter.
        model_id: The model identifier (for potential model-specific filtering).

    Returns
    -------
        dict: Filtered kwargs containing only OpenAI SDK supported params.
    """
    filtered = {k: v for k, v in kwargs.items() if k in CHAT_COMPLETION_PARAMS}
    dropped = set(kwargs.keys()) - CHAT_COMPLETION_PARAMS
    if dropped:
        log.debug(
            "Dropped unsupported completion params for model %s: %s",
            model_id,
            sorted(dropped),
        )
    return filtered


def filter_embedding_kwargs(kwargs: dict) -> dict:
    """Filter out params not supported by OpenAI SDK embedding endpoint.

    Args
    ----
        kwargs: The keyword arguments to filter.

    Returns
    -------
        dict: Filtered kwargs containing only OpenAI SDK supported params.
    """
    return {k: v for k, v in kwargs.items() if k in EMBEDDING_PARAMS}
