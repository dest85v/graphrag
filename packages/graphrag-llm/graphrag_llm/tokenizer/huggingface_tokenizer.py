# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""HuggingFace Tokenizer using the HuggingFace `tokenizers` library."""

import logging
from typing import Any

from graphrag_llm.tokenizer.tokenizer import Tokenizer

log = logging.getLogger(__name__)


class HuggingFaceTokenizer(Tokenizer):
    """HuggingFace Tokenizer using the `tokenizers` library.

    Provides tokenization for any model hosted on HuggingFace Hub.
    Uses `add_special_tokens=False` for consistency with tiktoken behavior
    (no BOS/EOS token prepending).
    """

    _tokenizer: Any
    _source: str

    def __init__(self, *, model_id: str, **kwargs: Any) -> None:
        """Initialize the HuggingFace Tokenizer.

        Args
        ----
        model_id: str
            A HuggingFace model repository identifier (e.g., 'meta-llama/Llama-3.1-8B-Instruct')
            or a local path to a tokenizer.json file.
        """
        self._source = model_id
        from tokenizers import Tokenizer as HFTokenizer

        # Check if model_id looks like a local file path (absolute or relative)
        if model_id.startswith("/") or (
            "/" in model_id and model_id.endswith("tokenizer.json")
        ):
            try:
                self._tokenizer = HFTokenizer.from_file(model_id)
            except Exception as e:
                msg = (
                    f"Failed to load tokenizer from local file '{model_id}': {e}. "
                    f"Provide a valid local path or a HuggingFace Hub model ID."
                )
                raise ValueError(msg) from e
        else:
            # Treat as HuggingFace Hub model ID
            try:
                self._tokenizer = HFTokenizer.from_pretrained(model_id)
            except (OSError, ValueError) as e:
                msg = (
                    f"Cannot load tokenizer for '{model_id}' from HuggingFace Hub: {e}. "
                    f"Verify the model_id is correct and the model has a tokenizer.json file. "
                    f"Alternatively, download the tokenizer manually and use a local path."
                )
                raise ValueError(msg) from e

    def encode(self, text: str) -> list[int]:
        """Encode the given text into a list of tokens.

        Args
        ----
        text: str
            The input text to encode.

        Returns
        -------
        list[int]: A list of token IDs representing the encoded text.
        """
        encoding = self._tokenizer.encode(text, add_special_tokens=False)
        return encoding.ids

    def decode(self, tokens: list[int]) -> str:
        """Decode a list of tokens back into a string.

        Args
        ----
        tokens: list[int]
            A list of token IDs to decode.

        Returns
        -------
        str: The decoded string from the list of tokens.
        """
        return self._tokenizer.decode(tokens, skip_special_tokens=True)

    def num_tokens(self, text: str) -> int:
        """Return the number of tokens in the given text.

        Args
        ----
        text: str
            The input text to analyze.

        Returns
        -------
        int: The number of tokens in the input text.
        """
        return len(self.encode(text))
