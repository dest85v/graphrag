# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""LLMEmbedding based on the OpenAI SDK."""

from typing import TYPE_CHECKING, Any, Unpack

import openai
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from graphrag_llm.config.types import AuthMethod
from graphrag_llm.embedding.embedding import LLMEmbedding
from graphrag_llm.middleware import with_middleware_pipeline
from graphrag_llm.types import LLMEmbeddingResponse

if TYPE_CHECKING:
    from graphrag_cache import Cache, CacheKeyCreator

    from graphrag_llm.config import ModelConfig
    from graphrag_llm.metrics import MetricsProcessor, MetricsStore
    from graphrag_llm.rate_limit import RateLimiter
    from graphrag_llm.retry import Retry
    from graphrag_llm.tokenizer import Tokenizer
    from graphrag_llm.types import (
        AsyncLLMEmbeddingFunction,
        LLMEmbeddingArgs,
        LLMEmbeddingFunction,
        Metrics,
    )


class OpenAIEmbedding(LLMEmbedding):
    """LLMEmbedding based on the OpenAI SDK."""

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
        """Initialize OpenAIEmbedding.

        Args
        ----
            model_id: str
                The model ID, e.g., "text-embedding-ada-002".
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
        self._track_metrics = metrics_processor is not None
        self._cache = cache
        self._cache_key_creator = cache_key_creator
        self._rate_limiter = rate_limiter
        self._retrier = retrier

        self._embedding, self._embedding_async = _create_base_embeddings(
            model_config=model_config,
            azure_cognitive_services_audience=azure_cognitive_services_audience,
        )

        self._embedding, self._embedding_async = with_middleware_pipeline(
            model_config=self._model_config,
            model_fn=self._embedding,
            async_model_fn=self._embedding_async,
            request_type="embedding",
            cache=self._cache,
            cache_key_creator=self._cache_key_creator,
            tokenizer=self._tokenizer,
            metrics_processor=self._metrics_processor,
            rate_limiter=self._rate_limiter,
            retrier=self._retrier,
        )

    def embedding(
        self, /, **kwargs: Unpack["LLMEmbeddingArgs"],
    ) -> "LLMEmbeddingResponse":
        """Sync embedding method."""
        request_metrics: Metrics | None = kwargs.pop("metrics", None) or {}
        if not self._track_metrics:
            request_metrics = None

        try:
            return self._embedding(metrics=request_metrics, **kwargs)
        finally:
            if request_metrics:
                self._metrics_store.update_metrics(metrics=request_metrics)

    async def embedding_async(
        self, /, **kwargs: Unpack["LLMEmbeddingArgs"],
    ) -> "LLMEmbeddingResponse":
        """Async embedding method."""
        request_metrics: Metrics | None = kwargs.pop("metrics", None) or {}
        if not self._track_metrics:
            request_metrics = None

        try:
            return await self._embedding_async(metrics=request_metrics, **kwargs)
        finally:
            if request_metrics:
                self._metrics_store.update_metrics(metrics=request_metrics)

    @property
    def metrics_store(self) -> "MetricsStore":
        """Get metrics store."""
        return self._metrics_store

    @property
    def tokenizer(self) -> "Tokenizer":
        """Get tokenizer."""
        return self._tokenizer


def _create_base_embeddings(
    *,
    model_config: "ModelConfig",
    azure_cognitive_services_audience: str,
) -> tuple["LLMEmbeddingFunction", "AsyncLLMEmbeddingFunction"]:
    """Create base embedding functions using OpenAI SDK."""
    model_provider = model_config.model_provider
    model = model_config.azure_deployment_name or model_config.model

    call_kwargs: dict[str, Any] = {
        "model": model,
        **model_config.call_args,
    }

    def _base_embedding(**kwargs: Any) -> LLMEmbeddingResponse:
        kwargs.pop("metrics", None)
        merged = {**call_kwargs, **kwargs}

        # Filter unsupported params (replaces litellm's drop_params=True)
        filtered = _filter_embedding_kwargs(merged)

        if model_provider == "azure":
            client = _get_azure_client(model_config, azure_cognitive_services_audience)
            response = client.embeddings.create(**filtered)
        else:
            client = _get_openai_client(model_config)
            response = client.embeddings.create(**filtered)

        return LLMEmbeddingResponse.model_validate(response.model_dump())

    async def _base_embedding_async(**kwargs: Any) -> LLMEmbeddingResponse:
        kwargs.pop("metrics", None)
        merged = {**call_kwargs, **kwargs}

        filtered = _filter_embedding_kwargs(merged)

        if model_provider == "azure":
            client = _get_async_azure_client(
                model_config, azure_cognitive_services_audience,
            )
            response = await client.embeddings.create(**filtered)
        else:
            client = _get_async_openai_client(model_config)
            response = await client.embeddings.create(**filtered)

        return LLMEmbeddingResponse.model_validate(response.model_dump())

    return _base_embedding, _base_embedding_async


def _filter_embedding_kwargs(kwargs: dict) -> dict:
    """Filter out params not supported by OpenAI SDK embedding endpoint."""
    from graphrag_llm.utils import filter_embedding_kwargs

    return filter_embedding_kwargs(kwargs)


def _get_openai_client(model_config: "ModelConfig") -> openai.OpenAI:
    """Get sync OpenAI client."""
    kwargs: dict[str, Any] = {"api_key": model_config.api_key}
    if model_config.api_base:
        kwargs["base_url"] = model_config.api_base
    kwargs.update(model_config.call_args)
    return openai.OpenAI(**kwargs)  # type: ignore[call-arg]


def _get_async_openai_client(model_config: "ModelConfig") -> openai.AsyncOpenAI:
    """Get async OpenAI client."""
    kwargs: dict[str, Any] = {"api_key": model_config.api_key}
    if model_config.api_base:
        kwargs["base_url"] = model_config.api_base
    kwargs.update(model_config.call_args)
    return openai.AsyncOpenAI(**kwargs)  # type: ignore[call-arg]


def _get_azure_client(
    model_config: "ModelConfig",
    azure_cognitive_services_audience: str,
) -> openai.AzureOpenAI:
    """Get sync Azure OpenAI client."""
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
    kwargs.update(model_config.call_args)
    return openai.AzureOpenAI(**kwargs)  # type: ignore[call-arg]


def _get_async_azure_client(
    model_config: "ModelConfig",
    azure_cognitive_services_audience: str,
) -> openai.AsyncAzureOpenAI:
    """Get async Azure OpenAI client."""
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
    kwargs.update(model_config.call_args)
    return openai.AsyncAzureOpenAI(**kwargs)  # type: ignore[call-arg]
