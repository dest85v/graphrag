# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Functions to analyze text data using SpaCy."""

from typing import Any

from graphrag.index.operations.build_noun_graph.np_extractors.base import (
    BaseNounPhraseExtractor,
)
from graphrag.index.operations.build_noun_graph.np_extractors.np_validator import (
    has_valid_token_length,
    is_compound,
)


class RegexENNounPhraseExtractor(BaseNounPhraseExtractor):
    """spaCy-based noun phrase extractor for English.

    Uses spaCy's noun_chunks and POS tagging to detect noun phrases.
    Much faster than the syntactic parser-based extractor with no external
    corpora dependencies.
    """

    def __init__(
        self,
        model_name: str,
        max_word_length: int,
        exclude_nouns: list[str],
        word_delimiter: str,
    ):
        """
        Noun phrase extractor for English based on spaCy's noun_chunks and POS tagging.

        Uses spaCy's built-in pipeline to detect noun phrases and proper nouns,
        then applies filtering heuristics to select valid noun phrase entities.

        Args:
            model_name: SpaCy model name (e.g., "en_core_web_sm").
            max_word_length: Maximum length (in character) of each extracted word.
            exclude_nouns: List of stop words to exclude from noun phrases.
            word_delimiter: Delimiter for joining words.
        """
        super().__init__(
            model_name=model_name,
            max_word_length=max_word_length,
            exclude_nouns=exclude_nouns,
            word_delimiter=word_delimiter,
        )
        # Load spaCy model with tagger and parser (needed for noun_chunks)
        # Exclude lemmatizer and NER to reduce overhead (not needed for this extractor)
        self.nlp = self.load_spacy_model(model_name, exclude=["lemmatizer", "ner"])

    def extract(
        self,
        text: str,
    ) -> list[str]:
        """
        Extract noun phrases from text using spaCy noun_chunks and POS tags.

        Args:
            text: Text.

        Returns: List of noun phrases.
        """
        doc = self.nlp(text)

        # Identify proper nouns via POS tag
        proper_nouns = {token.text.upper() for token in doc if token.pos_ == "PROPN"}

        # Extract noun chunks, filtering out leading determiners for parity with textblob
        noun_phrase_texts = []
        for chunk in doc.noun_chunks:
            tokens = list(chunk)
            # Strip leading determiners (DET) to match textblob behavior
            start = 0
            while start < len(tokens) and tokens[start].pos_ == "DET":
                start += 1
            if start < len(tokens):
                noun_phrase_texts.append(
                    self.word_delimiter.join(t.text for t in tokens[start:])
                )

        tagged_noun_phrases = [
            self._tag_noun_phrases(chunk, proper_nouns) for chunk in noun_phrase_texts
        ]

        filtered_noun_phrases = set()
        for tagged_np in tagged_noun_phrases:
            if (
                tagged_np["has_proper_nouns"]
                or len(tagged_np["cleaned_tokens"]) > 1
                or tagged_np["has_compound_words"]
            ) and tagged_np["has_valid_tokens"]:
                filtered_noun_phrases.add(tagged_np["cleaned_text"])
        return list(filtered_noun_phrases)

    def _tag_noun_phrases(
        self, noun_phrase: str, all_proper_nouns: set[str] | None = None
    ) -> dict[str, Any]:
        """Extract attributes of a noun chunk, to be used for filtering."""
        if all_proper_nouns is None:
            all_proper_nouns = set()
        tokens = [
            token for token in noun_phrase.split(self.word_delimiter) if len(token) > 0
        ]
        cleaned_tokens = [
            token for token in tokens if token.upper() not in self.exclude_nouns
        ]
        has_proper_nouns = any(
            token.upper() in all_proper_nouns for token in cleaned_tokens
        )
        has_compound_words = is_compound(cleaned_tokens)
        has_valid_tokens = has_valid_token_length(
            cleaned_tokens, self.max_word_length
        ) and all(self._is_valid_token(token) for token in cleaned_tokens)
        return {
            "cleaned_tokens": cleaned_tokens,
            "cleaned_text": self.word_delimiter
            .join(token for token in cleaned_tokens)
            .replace("\n", "")
            .upper(),
            "has_proper_nouns": has_proper_nouns,
            "has_compound_words": has_compound_words,
            "has_valid_tokens": has_valid_tokens,
        }

    def _is_valid_token(self, token: str) -> bool:
        """Check if a token contains only valid characters (alphanumeric, hyphens, Unicode letters)."""
        import re

        return bool(re.match(r"^[\w\-]+$", token))

    def __str__(self) -> str:
        """Return string representation of the extractor, used for cache key generation."""
        return f"regex_en_{self.model_name}_{self.exclude_nouns}_{self.max_word_length}_{self.word_delimiter}"
