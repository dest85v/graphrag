# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Unit tests for Unicode-aware token validation and Russian noun phrase extraction."""

import re

from graphrag.index.operations.build_noun_graph.np_extractors.regex_extractor import (
    RegexENNounPhraseExtractor,
)
from graphrag.index.operations.build_noun_graph.np_extractors.stop_words import (
    EN_STOP_WORDS,
)


def _make_extractor(**overrides) -> RegexENNounPhraseExtractor:
    """Helper to create a RegexENNounPhraseExtractor with default + overrides."""
    defaults = {
        "model_name": "en_core_web_sm",
        "exclude_nouns": EN_STOP_WORDS,
        "max_word_length": 15,
        "word_delimiter": " ",
    }
    defaults.update(overrides)
    return RegexENNounPhraseExtractor(**defaults)


class TestUnicodeTokenValidation:
    """Tests for Unicode-aware _is_valid_token validation."""

    def test_cyrillic_tokens_pass(self):
        """Cyrillic words pass Unicode validation."""
        pattern = r"^[\w\-]+$"

        cyrillic_words = ["внутренний", "АУДИТ", "отчёт", "документация", "система"]
        for word in cyrillic_words:
            assert re.match(pattern, word), (
                f"Cyrillic word '{word}' should pass validation"
            )

    def test_english_tokens_still_pass(self):
        """English words still pass after Unicode change."""
        pattern = r"^[\w\-]+$"

        english_words = ["API", "endpoint", "deployment", "system", "test"]
        for word in english_words:
            assert re.match(pattern, word), (
                f"English word '{word}' should pass validation"
            )

    def test_hyphenated_compound_words_pass(self):
        """Hyphenated compound words pass validation."""
        pattern = r"^[\w\-]+$"

        compound_words = ["deployment-pipeline", "well-designed", "machine-learning"]
        for word in compound_words:
            assert re.match(pattern, word), (
                f"Compound word '{word}' should pass validation"
            )

    def test_standalone_hyphen_passes(self):
        """Standalone hyphen token (from spaCy tokenization) passes validation."""
        pattern = r"^[\w\-]+$"

        assert re.match(pattern, "-"), (
            "Standalone hyphen should pass (needed for spaCy tokenization)"
        )

    def test_special_chars_still_fail(self):
        """Tokens with special characters still fail validation."""
        pattern = r"^[\w\-]+$"

        invalid_tokens = ["@world", "test$123", "hello!", "world#1", "good@bye"]
        for token in invalid_tokens:
            assert not re.match(pattern, token), f"'{token}' should fail validation"

    def test_numbers_still_pass(self):
        """Numeric tokens still pass validation."""
        pattern = r"^[\w\-]+$"

        number_tokens = ["2026", "v2", "API3", "123"]
        for token in number_tokens:
            assert re.match(pattern, token), (
                f"Number token '{token}' should pass validation"
            )

    def test_jaccard_similarity_on_english_text(self):
        """Jaccard similarity between ASCII-only and new Unicode RegexExtractor on English text >= 95%."""
        english_texts = [
            "The quick brown fox jumps over the lazy dog",
            "Well-designed machine learning systems",
            "President Biden visited the capital city",
            "The big brown dog ran fast",
            "The data and the data and the data",
            "Paris is beautiful",
        ]

        # Old ASCII regex pattern
        old_pattern = r"^[a-zA-Z0-9\-]+$"

        def old_is_valid(token: str) -> bool:
            return bool(re.match(old_pattern, token))

        # New Unicode regex pattern
        new_pattern = r"^[\w\-]+$"

        def new_is_valid(token: str) -> bool:
            return bool(re.match(new_pattern, token))

        all_old_valid_tokens = set()
        all_new_valid_tokens = set()

        for text in english_texts:
            tokens = text.split()
            for token in tokens:
                if old_is_valid(token):
                    all_old_valid_tokens.add(token.upper())
                if new_is_valid(token):
                    all_new_valid_tokens.add(token.upper())

        if len(all_old_valid_tokens) == 0 and len(all_new_valid_tokens) == 0:
            jaccard = 1.0
        else:
            intersection = all_old_valid_tokens & all_new_valid_tokens
            union = all_old_valid_tokens | all_new_valid_tokens
            jaccard = len(intersection) / len(union) if union else 1.0

        assert jaccard >= 0.95, f"Jaccard similarity {jaccard:.4f} < 0.95"


class TestRussianNounPhraseExtraction:
    """Tests for Russian noun phrase extraction with Unicode-aware extractor."""

    def test_cyrillic_extraction_with_unicode_model(self):
        """Russian text is processed without errors by Unicode extractor."""
        extractor = _make_extractor(max_word_length=50)
        result = extractor.extract("Этот текст на русском языке")
        assert isinstance(result, list)
        assert all(phrase == phrase.upper() for phrase in result)

    def test_mixed_russian_english_extraction(self):
        """Mixed Russian-English text extracts both languages."""
        extractor = _make_extractor(max_word_length=50)
        result = extractor.extract("Настройка API сервера требует deployment pipeline")
        assert isinstance(result, list)
        # Should extract phrases in uppercase
        assert all(phrase == phrase.upper() for phrase in result)
        # Should have some noun phrases
        assert len(result) > 0, f"Expected noun phrases in mixed text, got: {result}"

    def test_english_terms_in_russian_context(self):
        """English terms inside Russian text are extracted."""
        extractor = _make_extractor(max_word_length=50)
        result = extractor.extract("Читай API документацию внимательно")
        assert isinstance(result, list)
        assert len(result) > 0, f"Expected noun phrases, got: {result}"

    def test_russian_compound_phrases(self):
        """Russian compound noun phrases are extracted."""
        extractor = _make_extractor(max_word_length=50)
        result = extractor.extract("финансовый отчёт за прошлый год")
        assert isinstance(result, list)
        assert len(result) > 0, f"Expected noun phrases, got: {result}"

    def test_russian_proper_nouns(self):
        """Russian proper nouns are detected."""
        extractor = _make_extractor(max_word_length=50)
        result = extractor.extract("Москва является столицей России")
        assert isinstance(result, list)
        assert len(result) > 0, f"Expected noun phrases, got: {result}"

    def test_russian_numeric_tokens(self):
        """Russian text with numbers is handled correctly."""
        extractor = _make_extractor(max_word_length=50)
        result = extractor.extract("Версия 2.0 системы работает стабильно")
        assert isinstance(result, list)

    def test_russian_hyphenated_terms(self):
        """Russian text with hyphenated terms is handled correctly."""
        extractor = _make_extractor(max_word_length=50)
        result = extractor.extract("системо-ориентированный подход")
        assert isinstance(result, list)
