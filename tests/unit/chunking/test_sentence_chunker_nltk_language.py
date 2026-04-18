# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for SentenceChunker nltk_language parameter."""

from unittest.mock import patch

import pytest
from graphrag_chunking.sentence_chunker import SentenceChunker


class TestSentenceChunkerNltkLanguage:
    """Tests for the nltk_language parameter of SentenceChunker."""

    def test_sentence_chunker_english_default(self):
        """Verify nltk_language='english' works for English text (default behavior)."""
        chunker = SentenceChunker(nltk_language="english")
        text = "Hello world. This is a test. How are you?"
        chunks = chunker.chunk(text)

        assert len(chunks) == 3
        assert chunks[0].text.strip() == "Hello world."
        assert chunks[1].text.strip() == "This is a test."
        assert chunks[2].text.strip() == "How are you?"

    def test_sentence_chunker_english_explicit(self):
        """Verify explicit nltk_language='english' matches default behavior."""
        chunker_default = SentenceChunker()
        chunker_explicit = SentenceChunker(nltk_language="english")

        text = "This is a sentence. And another one."
        chunks_default = chunker_default.chunk(text)
        chunks_explicit = chunker_explicit.chunk(text)

        assert len(chunks_default) == len(chunks_explicit)
        assert chunks_default[0].text == chunks_explicit[0].text

    def test_sentence_chunker_russian_language(self):
        """Verify Russian text splits correctly with nltk_language='russian'."""
        with patch("nltk.sent_tokenize") as mock_tokenize:
            mock_tokenize.return_value = [
                "Иван Иванович пришёл на работу в понедельник.",
                "Он открыл ноутбук и начал анализ данных.",
            ]
            chunker = SentenceChunker(nltk_language="russian")
            text = "Иван Иванович пришёл на работу в понедельник. Он открыл ноутбук и начал анализ данных."
            chunks = chunker.chunk(text)

            assert len(chunks) == 2
            mock_tokenize.assert_called_once_with(
                text.strip(),
                language="russian",
            )

    def test_sentence_chunker_russian_language_actual(self):
        """Verify actual Russian text splitting with bootstrap."""
        from graphrag_chunking.bootstrap_nltk import bootstrap

        bootstrap()

        chunker = SentenceChunker(nltk_language="russian")
        text = "Иван Иванович пришёл на работу в понедельник. Он открыл ноутбук и начал анализ данных."
        chunks = chunker.chunk(text)

        assert len(chunks) >= 2
        assert chunks[0].text.strip().endswith(".")
        assert chunks[1].text.strip().endswith(".")

    def test_sentence_chunker_german_language(self):
        """Verify German text splits correctly with nltk_language='german'."""
        with patch("nltk.sent_tokenize") as mock_tokenize:
            mock_tokenize.return_value = [
                "Das ist der erste Satz.",
                "Dies ist der zweite Satz.",
            ]
            chunker = SentenceChunker(nltk_language="german")
            text = "Das ist der erste Satz. Dies ist der zweite Satz."
            chunks = chunker.chunk(text)

            assert len(chunks) == 2
            mock_tokenize.assert_called_once_with(
                text.strip(),
                language="german",
            )

    def test_sentence_chunker_french_language(self):
        """Verify French text splits correctly with nltk_language='french'."""
        with patch("nltk.sent_tokenize") as mock_tokenize:
            mock_tokenize.return_value = [
                "C'est la première phrase.",
                "Voici la deuxième phrase.",
            ]
            chunker = SentenceChunker(nltk_language="french")
            text = "C'est la première phrase. Voici la deuxième phrase."
            chunks = chunker.chunk(text)

            assert len(chunks) == 2
            mock_tokenize.assert_called_once_with(
                text.strip(),
                language="french",
            )

    def test_sentence_chunker_invalid_language_raises(self):
        """Verify invalid language code raises LookupError on chunk call."""
        chunker = SentenceChunker(nltk_language="invalid_xyz")
        with pytest.raises(LookupError):
            chunker.chunk("Some test text.")

    def test_sentence_chunker_default_is_english(self):
        """Verify default nltk_language is 'english'."""
        chunker = SentenceChunker()
        assert chunker._nltk_language == "english"  # noqa: SLF001
