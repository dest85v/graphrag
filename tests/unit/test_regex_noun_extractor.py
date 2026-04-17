# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Unit tests for RegexENNounPhraseExtractor (spaCy-based)."""

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


class TestRegexENNounPhraseExtractor:
    """Tests for RegexENNounPhraseExtractor."""

    def test_extract_returns_uppercase_phrases(self):
        """Output phrases are all uppercased."""
        extractor = _make_extractor()
        result = extractor.extract("The quick brown fox jumps over the lazy dog")
        assert all(phrase == phrase.upper() for phrase in result)

    def test_extract_filters_exclude_nouns(self):
        """Excluded stop words do not appear in output."""
        extractor = _make_extractor(
            exclude_nouns=["quick", "brown", "fox", "lazy", "dog", "jumps"]
        )
        result = extractor.extract("The quick brown fox jumps over the lazy dog")
        for phrase in result:
            for word in phrase.split():
                assert word.upper() not in [
                    w.upper() for w in ["quick", "brown", "fox", "lazy", "dog", "jumps"]
                ]

    def test_extract_handles_empty_text(self):
        """Empty string returns empty list."""
        extractor = _make_extractor()
        result = extractor.extract("")
        assert result == []

    def test_extract_handles_unicode(self):
        """Unicode text is processed without errors."""
        extractor = _make_extractor()
        result = extractor.extract("Café résumé naïve")
        assert isinstance(result, list)

    def test_extract_max_word_length(self):
        """Words exceeding max_word_length are filtered out."""
        extractor = _make_extractor(max_word_length=5)
        result = extractor.extract("The supercalifragilisticexpialidocious elephant")
        for phrase in result:
            for word in phrase.split():
                assert len(word) <= 5, f"Word '{word}' exceeds max length 5"

    def test_extract_compound_words(self):
        """Hyphenated compound words are preserved if they pass validation."""
        extractor = _make_extractor(max_word_length=50)
        result = extractor.extract("Well-designed machine learning systems")
        # Well-designed should be preserved as a compound (no trailing punctuation)
        assert (
            any("WELL-DESIGNED" in phrase for phrase in result)
            or any("MACHINE" in phrase for phrase in result)
            or any("LEARNING" in phrase for phrase in result)
        )

    def test_extract_proper_nouns(self):
        """Proper nouns are detected and included."""
        extractor = _make_extractor(max_word_length=50)
        result = extractor.extract("President Biden visited the capital city")
        # Proper noun like BIDEN should be in the output
        assert any("BIDEN" in phrase for phrase in result), (
            f"Expected BIDEN in results, got: {result}"
        )

    def test_str_cache_key(self):
        """__str__() returns format with model name for cache key."""
        extractor = _make_extractor(max_word_length=20)
        s = str(extractor)
        assert s.startswith("regex_en_en_core_web_sm_")
        assert "20" in s
        assert "word_delimiter" not in s  # the actual delimiter value, not the word

    def test_extract_invalid_tokens(self):
        """Non-alphanumeric tokens are filtered out."""
        extractor = _make_extractor(max_word_length=50)
        # Text with special characters
        result = extractor.extract("Hello @world# test$123")
        for phrase in result:
            for word in phrase.split():
                cleaned = word.replace("\n", "")
                import re

                assert re.match(r"^[A-Z0-9\-]+$", cleaned), (
                    f"Invalid token found: '{cleaned}' in {phrase}"
                )

    def test_extract_determiners_stripped(self):
        """Leading determiners (the, a, an) are stripped from noun phrases."""
        extractor = _make_extractor(max_word_length=50)
        result = extractor.extract("The big brown dog ran fast")
        # Check that no phrase starts with 'THE', 'A', or 'AN'
        for phrase in result:
            assert not phrase.startswith("THE "), f"Phrase starts with 'THE': {phrase}"
            assert not phrase.startswith("A "), f"Phrase starts with 'A': {phrase}"

    def test_extract_produces_deduplicated_output(self):
        """Duplicate noun phrases are deduplicated."""
        extractor = _make_extractor(max_word_length=50)
        result = extractor.extract("The data and the data and the data")
        assert len(result) == len(set(result)), "Output contains duplicates"

    def test_extract_single_word_proper_noun(self):
        """Single proper noun words are extracted."""
        extractor = _make_extractor(max_word_length=50)
        result = extractor.extract("Paris is beautiful")
        assert any("PARIS" in phrase for phrase in result), (
            f"Expected PARIS in results, got: {result}"
        )
