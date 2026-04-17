# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""OpenAI Tokenizer using tiktoken directly."""

from typing import Any

import tiktoken

from graphrag_llm.tokenizer.tokenizer import Tokenizer


class OpenAITokenizer(Tokenizer):
    """OpenAI Tokenizer using tiktoken directly.

    Resolves the correct encoding from the model ID at runtime,
    providing a drop-in replacement for LiteLLMTokenizer.
    """

    _model_id: str
    _encoding: tiktoken.Encoding

    def __init__(
        self,
        *,
        model_id: str | None = None,
        encoding_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the OpenAI Tokenizer.

        Args
        ----
            model_id: str | None
                The model ID, e.g., "gpt-4o", "text-embedding-ada-002".
            encoding_name: str | None
                Fallback encoding name if model_id is not provided.
        """
        if model_id:
            self._model_id = model_id
            # Strip provider prefix (e.g., "openai/" or "azure/") if present
            model_name = model_id.rsplit("/", maxsplit=1)[-1]
            try:
                self._encoding = tiktoken.encoding_for_model(model_name)
            except KeyError:
                # Unknown model — fall back to cl100k_base (GPT-4 / GPT-3.5 encoding)
                self._encoding = tiktoken.get_encoding("cl100k_base")
        elif encoding_name:
            self._model_id = f"custom/{encoding_name}"
            self._encoding = tiktoken.get_encoding(encoding_name)
        else:
            msg = "Either model_id or encoding_name must be provided."
            raise ValueError(msg)

    def encode(self, text: str) -> list[int]:
        """Encode the given text into a list of tokens.

        Args
        ----
            text: str
                The input text to encode.

        Returns
        -------
            list[int]: A list of tokens representing the encoded text.
        """
        return self._encoding.encode(text)

    def decode(self, tokens: list[int]) -> str:
        """Decode a list of tokens back into a string.

        Args
        ----
            tokens: list[int]
                A list of tokens to decode.

        Returns
        -------
            str: The decoded string from the list of tokens.
        """
        return self._encoding.decode(tokens)
