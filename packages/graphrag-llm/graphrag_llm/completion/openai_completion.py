# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""LLMCompletion based on the OpenAI SDK."""

from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any, Unpack

import openai
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from graphrag_llm.completion.completion import LLMCompletion
from graphrag_llm.config.types import AuthMethod
from graphrag_llm.middleware import (
    with_middleware_pipeline,
)
from graphrag_llm.types import LLMCompletionChunk, LLMCompletionResponse
from graphrag_llm.utils import (
    filter_completion_kwargs,
    structure_completion_response,
)

if TYPE_CHECKING:
    from graphrag_cache import Cache, CacheKeyCreator

    from graphrag_llm.config import ModelConfig
    from graphrag_llm.metrics import MetricsProcessor, MetricsStore
    from graphrag_llm.rate_limit import RateLimiter
    from graphrag_llm.retry import Retry
    from graphrag_llm.tokenizer import Tokenizer
    from graphrag_llm.types import (
        AsyncLLMCompletionFunction,
        LLMCompletionArgs,
        LLMCompletionFunction,
        LLMCompletionMessagesParam,
        Metrics,
        ResponseFormat,
    )


class OpenAICompletion(LLMCompletion):
    """LLMCompletion based on the OpenAI SDK."""

    _model_config: "ModelConfig"
    _model_id: str
    _track_metrics: bool = False
    _metrics_store: "MetricsStore"
    _metrics_processor: "MetricsProcessor | None"
    _cache: "Cache | None"
    _cache_key_creator: "CacheKeyCreator"
    _tokenizer: "Tokenizer"
    _rate_limiter: "RateLimiter | None"
    _retrier: "Retry | None"
    _sync_client: openai.OpenAI | openai.AzureOpenAI
    _async_client: openai.AsyncOpenAI | openai.AsyncAzureOpenAI
    _is_azure: bool

    def __init__(
        self,
        *,
        model_id: str,
        model_config: "ModelConfig",
        tokenizer: "Tokenizer",
        metrics_store: "MetricsStore",
        metrics_processor: "MetricsProcessor | None" = None,
        rate_limiter: "RateLimiter | None" = None,
        retrier: "Retry | None" = None,
        cache: "Cache | None" = None,
        cache_key_creator: "CacheKeyCreator",
        azure_cognitive_services_audience: str = "https://cognitiveservices.azure.com/.default",
        **kwargs: Any,
    ) -> None:
        """Initialize OpenAICompletion.

        Args
        ----
            model_id: str
                The model ID, e.g., "gpt-4o".
            model_config: ModelConfig
                The configuration for the model.
            tokenizer: Tokenizer
                The tokenizer to use.
            metrics_store: MetricsStore
                The metrics store to use.
            metrics_processor: MetricsProcessor | None (default: None)
                The metrics processor to use.
            cache: Cache | None (default: None)
                An optional cache instance.
            cache_key_creator: CacheKeyCreator
                The cache key creator.
            rate_limiter: RateLimiter | None (default: None)
                The rate limiter to use.
            retrier: Retry | None (default: None)
                The retry strategy to use.
            azure_cognitive_services_audience: str (default: "https://cognitiveservices.azure.com/.default")
                The audience for Azure Cognitive Services when using Managed Identity.
        """
        self._model_id = model_id
        self._model_config = model_config
        self._tokenizer = tokenizer
        self._metrics_store = metrics_store
        self._metrics_processor = metrics_processor
        self._cache = cache
        self._track_metrics = metrics_processor is not None
        self._cache_key_creator = cache_key_creator
        self._rate_limiter = rate_limiter
        self._retrier = retrier

        self._is_azure = model_config.model_provider == "azure"

        self._sync_client, self._async_client = _create_clients(
            model_config=model_config,
            azure_cognitive_services_audience=azure_cognitive_services_audience,
        )

        self._completion, self._completion_async = _create_base_completions(
            model_config=model_config,
            azure_cognitive_services_audience=azure_cognitive_services_audience,
        )

        self._completion, self._completion_async = with_middleware_pipeline(
            model_config=self._model_config,
            model_fn=self._completion,
            async_model_fn=self._completion_async,
            request_type="chat",
            cache=self._cache,
            cache_key_creator=self._cache_key_creator,
            tokenizer=self._tokenizer,
            metrics_processor=self._metrics_processor,
            rate_limiter=self._rate_limiter,
            retrier=self._retrier,
        )

    def completion(
        self,
        /,
        **kwargs: Unpack["LLMCompletionArgs[ResponseFormat]"],
    ) -> "LLMCompletionResponse[ResponseFormat] | Iterator[LLMCompletionChunk]":
        """Sync completion method."""
        messages: LLMCompletionMessagesParam = kwargs.pop("messages")
        response_format = kwargs.pop("response_format", None)

        is_streaming = kwargs.get("stream") or False

        if response_format is not None and is_streaming:
            msg = "response_format is not supported for streaming completions."
            raise ValueError(msg)

        request_metrics: Metrics | None = kwargs.pop("metrics", None) or {}
        if not self._track_metrics:
            request_metrics = None

        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        try:
            response = self._completion(
                messages=messages,
                metrics=request_metrics,
                response_format=response_format,
                **kwargs,  # type: ignore
            )
            if response_format is not None:
                structured_response = structure_completion_response(
                    response.content, response_format,
                )
                response.formatted_response = structured_response
            return response
        finally:
            if request_metrics is not None:
                self._metrics_store.update_metrics(metrics=request_metrics)

    async def completion_async(
        self,
        /,
        **kwargs: Unpack["LLMCompletionArgs[ResponseFormat]"],
    ) -> "LLMCompletionResponse[ResponseFormat] | AsyncIterator[LLMCompletionChunk]":
        """Async completion method."""
        messages: LLMCompletionMessagesParam = kwargs.pop("messages")
        response_format = kwargs.pop("response_format", None)

        is_streaming = kwargs.get("stream") or False

        if response_format is not None and is_streaming:
            msg = "response_format is not supported for streaming completions."
            raise ValueError(msg)

        request_metrics: Metrics | None = kwargs.pop("metrics", None) or {}
        if not self._track_metrics:
            request_metrics = None

        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        try:
            response = await self._completion_async(
                messages=messages,
                metrics=request_metrics,
                response_format=response_format,
                **kwargs,  # type: ignore
            )
            if response_format is not None:
                structured_response = structure_completion_response(
                    response.content, response_format,
                )
                response.formatted_response = structured_response
            return response
        finally:
            if request_metrics is not None:
                self._metrics_store.update_metrics(metrics=request_metrics)

    @property
    def metrics_store(self) -> "MetricsStore":
        """Get metrics store."""
        return self._metrics_store

    @property
    def tokenizer(self) -> "Tokenizer":
        """Get tokenizer."""
        return self._tokenizer


def _create_clients(
    *,
    model_config: "ModelConfig",
    azure_cognitive_services_audience: str,
) -> tuple[
    openai.OpenAI | openai.AzureOpenAI,
    openai.AsyncOpenAI | openai.AsyncAzureOpenAI,
]:
    """Create sync and async OpenAI clients."""
    model_provider = model_config.model_provider

    if model_provider == "azure":
        kwargs: dict[str, Any] = {
            "azure_endpoint": model_config.api_base,
            "api_version": model_config.api_version,
        }

        if model_config.auth_method == AuthMethod.AzureManagedIdentity:
            kwargs["azure_ad_token_provider"] = get_bearer_token_provider(
                DefaultAzureCredential(), azure_cognitive_services_audience,
            )
        else:
            kwargs["api_key"] = model_config.api_key

        sync_client: openai.OpenAI | openai.AzureOpenAI = openai.AzureOpenAI(**kwargs)  # type: ignore[call-arg]
        async_client: openai.AsyncOpenAI | openai.AsyncAzureOpenAI = (
            openai.AsyncAzureOpenAI(**kwargs)  # type: ignore[call-arg]
        )
    else:
        kwargs: dict[str, Any] = {
            "api_key": model_config.api_key,
        }
        if model_config.api_base:
            kwargs["base_url"] = model_config.api_base
        kwargs.update(model_config.call_args)

        sync_client = openai.OpenAI(**kwargs)  # type: ignore[call-arg]
        async_client = openai.AsyncOpenAI(**kwargs)  # type: ignore[call-arg]

    return sync_client, async_client


def _create_base_completions(
    *,
    model_config: "ModelConfig",
    azure_cognitive_services_audience: str,
) -> tuple["LLMCompletionFunction", "AsyncLLMCompletionFunction"]:
    """Create base completion functions using OpenAI SDK.

    Wraps the OpenAI SDK completion calls, removing graphrag_llm-specific params
    (like metrics) and applying parameter filtering before the API call.
    """
    model = model_config.azure_deployment_name or model_config.model

    # Build client-level args that don't change per-call
    call_kwargs: dict[str, Any] = {
        "model": model,
        **model_config.call_args,
    }

    def _base_completion(
        **kwargs: Any,
    ) -> LLMCompletionResponse | Iterator[LLMCompletionChunk]:
        kwargs.pop("metrics", None)
        mock_response: str | None = kwargs.pop("mock_response", None)
        json_object: bool | None = kwargs.pop("response_format_json_object", None)

        # Merge per-call kwargs with base kwargs
        merged = {**call_kwargs, **kwargs}

        # Handle mock responses (for testing)
        if model_config.mock_responses and mock_response is not None:
            from graphrag_llm.utils import create_completion_response

            response = create_completion_response(mock_response)
            if response_format := kwargs.get("response_format"):
                structured = structure_completion_response(
                    response.content, response_format,
                )
                response.formatted_response = structured
            return response

        # Handle response_format_json_object convenience param
        if json_object and "response_format" not in merged:
            merged["response_format"] = {"type": "json_object"}

        # Filter out unsupported params (replaces litellm's drop_params=True)
        filtered = filter_completion_kwargs(merged, model)

        response = _get_sync_client(
            model_config, azure_cognitive_services_audience,
        ).chat.completions.create(
            **filtered,
        )
        return LLMCompletionResponse.model_validate(response.model_dump())

    async def _base_completion_async(
        **kwargs: Any,
    ) -> LLMCompletionResponse | AsyncIterator[LLMCompletionChunk]:
        kwargs.pop("metrics", None)
        mock_response: str | None = kwargs.pop("mock_response", None)
        json_object: bool | None = kwargs.pop("response_format_json_object", None)

        merged = {**call_kwargs, **kwargs}

        if model_config.mock_responses and mock_response is not None:
            from graphrag_llm.utils import create_completion_response

            response = create_completion_response(mock_response)
            if response_format := kwargs.get("response_format"):
                structured = structure_completion_response(
                    response.content, response_format,
                )
                response.formatted_response = structured
            return response

        if json_object and "response_format" not in merged:
            merged["response_format"] = {"type": "json_object"}

        filtered = filter_completion_kwargs(merged, model)

        response = await _get_async_client(
            model_config, azure_cognitive_services_audience,
        ).chat.completions.create(
            **filtered,
        )
        return LLMCompletionResponse.model_validate(response.model_dump())

    return (_base_completion, _base_completion_async)


def _get_sync_client(
    model_config: "ModelConfig",
    azure_cognitive_services_audience: str,
) -> openai.OpenAI | openai.AzureOpenAI:
    """Get the sync OpenAI client.

    Creates a new client if not yet initialized (for factory pattern usage).
    """
    return _create_clients(
        model_config=model_config,
        azure_cognitive_services_audience=azure_cognitive_services_audience,
    )[0]


def _get_async_client(
    model_config: "ModelConfig",
    azure_cognitive_services_audience: str,
) -> openai.AsyncOpenAI | openai.AsyncAzureOpenAI:
    """Get the async OpenAI client."""
    return _create_clients(
        model_config=model_config,
        azure_cognitive_services_audience=azure_cognitive_services_audience,
    )[1]
