# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tokenizer model configuration."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from graphrag_llm.config.types import TokenizerType


class TokenizerConfig(BaseModel):
    """Configuration for a tokenizer."""

    model_config = ConfigDict(extra="allow")
    """Allow extra fields to support custom LLM provider implementations."""

    type: str = Field(
        default=TokenizerType.Tiktoken,
        description="The type of tokenizer to use. (default: tiktoken).",
    )

    model_id: str | None = Field(
        default=None,
        description="The identifier for the tokenizer model. For Tiktoken: example gpt-4o used to resolve the correct encoding. For HuggingFace: a HuggingFace model repository path (e.g. 'meta-llama/Llama-3.1-8B-Instruct') or a local tokenizer.json file path.",
    )

    encoding_name: str | None = Field(
        default=None,
        description="The encoding name for the tokenizer. Example: cl100k_base.",
    )

    def _validate_huggingface_config(self) -> None:
        """Validate HuggingFace tokenizer configuration."""
        if self.model_id is None or self.model_id.strip() == "":
            msg = "model_id must be specified for HuggingFace tokenizer."
            raise ValueError(msg)

    @model_validator(mode="after")
    def _validate_model(self):
        """Validate the tokenizer configuration based on its type."""
        if self.type == TokenizerType.Tiktoken:
            # Validate empty strings are not allowed
            if self.model_id is not None and self.model_id.strip() == "":
                msg = "Either model_id or encoding_name must be specified for TikToken tokenizer."
                raise ValueError(msg)
            if self.encoding_name is not None and self.encoding_name.strip() == "":
                msg = "Either model_id or encoding_name must be specified for TikToken tokenizer."
                raise ValueError(msg)
            # If at least one field is explicitly set (non-None), ensure at least one is valid
            model_id_valid = self.model_id is not None and self.model_id.strip() != ""
            encoding_name_valid = (
                self.encoding_name is not None and self.encoding_name.strip() != ""
            )
            if (self.model_id is not None or self.encoding_name is not None) and (
                not model_id_valid and not encoding_name_valid
            ):
                msg = "Either model_id or encoding_name must be specified for TikToken tokenizer."
                raise ValueError(msg)
        elif self.type == TokenizerType.HuggingFace:
            self._validate_huggingface_config()
        return self
