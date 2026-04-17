# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Model cost registry module."""

from typing import Any, ClassVar, TypedDict

from typing_extensions import Self


class ModelCosts(TypedDict):
    """Model costs."""

    input_cost_per_token: float
    output_cost_per_token: float


_MODEL_COST_MAP: dict[str, ModelCosts] = {
    # GPT-4o
    "gpt-4o": {
        "input_cost_per_token": 0.0000025,
        "output_cost_per_token": 0.000010,
    },
    "gpt-4o-2024-05-13": {
        "input_cost_per_token": 0.000005,
        "output_cost_per_token": 0.000015,
    },
    "gpt-4o-2024-08-06": {
        "input_cost_per_token": 0.0000025,
        "output_cost_per_token": 0.000010,
    },
    "gpt-4o-2024-11-20": {
        "input_cost_per_token": 0.0000025,
        "output_cost_per_token": 0.000010,
    },
    # GPT-4o mini
    "gpt-4o-mini": {
        "input_cost_per_token": 0.00000015,
        "output_cost_per_token": 0.0000006,
    },
    "gpt-4o-mini-2024-07-18": {
        "input_cost_per_token": 0.00000015,
        "output_cost_per_token": 0.0000006,
    },
    # GPT-4
    "gpt-4": {
        "input_cost_per_token": 0.00003,
        "output_cost_per_token": 0.00006,
    },
    "gpt-4-0613": {
        "input_cost_per_token": 0.00003,
        "output_cost_per_token": 0.00006,
    },
    "gpt-4-32k": {
        "input_cost_per_token": 0.00006,
        "output_cost_per_token": 0.00012,
    },
    "gpt-4-32k-0613": {
        "input_cost_per_token": 0.00006,
        "output_cost_per_token": 0.00012,
    },
    # GPT-4 Turbo
    "gpt-4-turbo": {
        "input_cost_per_token": 0.00001,
        "output_cost_per_token": 0.00003,
    },
    "gpt-4-turbo-2024-04-09": {
        "input_cost_per_token": 0.00001,
        "output_cost_per_token": 0.00003,
    },
    "gpt-4-1106-preview": {
        "input_cost_per_token": 0.00001,
        "output_cost_per_token": 0.00003,
    },
    "gpt-4-0125-preview": {
        "input_cost_per_token": 0.00001,
        "output_cost_per_token": 0.00003,
    },
    "gpt-4-vision-preview": {
        "input_cost_per_token": 0.00001,
        "output_cost_per_token": 0.00003,
    },
    # GPT-3.5 Turbo
    "gpt-3.5-turbo": {
        "input_cost_per_token": 0.0000015,
        "output_cost_per_token": 0.000002,
    },
    "gpt-3.5-turbo-0125": {
        "input_cost_per_token": 0.0000005,
        "output_cost_per_token": 0.0000015,
    },
    "gpt-3.5-turbo-1106": {
        "input_cost_per_token": 0.000001,
        "output_cost_per_token": 0.000002,
    },
    "gpt-3.5-turbo-instruct": {
        "input_cost_per_token": 0.0000015,
        "output_cost_per_token": 0.000002,
    },
    # Embeddings
    "text-embedding-ada-002": {
        "input_cost_per_token": 0.0000001,
        "output_cost_per_token": 0.0,
    },
    "text-embedding-3-small": {
        "input_cost_per_token": 0.00000002,
        "output_cost_per_token": 0.0,
    },
    "text-embedding-3-large": {
        "input_cost_per_token": 0.00000013,
        "output_cost_per_token": 0.0,
    },
    # Azure OpenAI deployments (same model costs, prefixed for routing)
    "azure/gpt-4o": {
        "input_cost_per_token": 0.0000025,
        "output_cost_per_token": 0.000010,
    },
    "azure/gpt-4o-mini": {
        "input_cost_per_token": 0.00000015,
        "output_cost_per_token": 0.0000006,
    },
    "azure/gpt-4": {
        "input_cost_per_token": 0.00003,
        "output_cost_per_token": 0.00006,
    },
    "azure/gpt-35-turbo": {
        "input_cost_per_token": 0.0000015,
        "output_cost_per_token": 0.000002,
    },
    "azure/text-embedding-ada-002": {
        "input_cost_per_token": 0.0000001,
        "output_cost_per_token": 0.0,
    },
    "azure/text-embedding-3-small": {
        "input_cost_per_token": 0.00000002,
        "output_cost_per_token": 0.0,
    },
    "azure/text-embedding-3-large": {
        "input_cost_per_token": 0.00000013,
        "output_cost_per_token": 0.0,
    },
}


class ModelCostRegistry:
    """Registry for model costs."""

    _instance: ClassVar["Self | None"] = None
    _model_costs: dict[str, ModelCosts]

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        """Create a new instance of ModelCostRegistry if it does not exist."""
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._model_costs = dict(_MODEL_COST_MAP)
            self._initialized = True

    def register_model_costs(self, model: str, costs: ModelCosts) -> None:
        """Register the cost per unit for a given model.

        Args
        ----
            model: str
                The model id, e.g., "openai/gpt-4o".
            costs: ModelCosts
                The costs associated with the model.
        """
        self._model_costs[model] = costs

    def get_model_costs(self, model: str) -> ModelCosts | None:
        """Retrieve the cost per unit for a given model.

        Args
        ----
            model: str
                The model id, e.g., "openai/gpt-4o".

        Returns
        -------
            ModelCosts | None
                The costs associated with the model, or None if not found.
        """
        return self._model_costs.get(model)


model_cost_registry = ModelCostRegistry()
