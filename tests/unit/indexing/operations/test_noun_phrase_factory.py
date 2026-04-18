# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for language-aware NLP factory functionality.

Validates:
- T001/T012: language field on TextAnalyzerConfig, default behavior
- T007/T012: RU_STOP_WORDS used when language="ru", EN_STOP_WORDS otherwise
- T008/T013: CFG grammars selected based on language
- T017: spaCy model auto-selection from language
"""

from typing import Any

from graphrag.config.enums import NounPhraseExtractorType
from graphrag.config.models.extract_graph_nlp_config import TextAnalyzerConfig
from graphrag.index.operations.build_noun_graph.np_extractors.factory import (
    LANGUAGE_MODEL_MAP,
    NounPhraseExtractorFactory,
)


class TestTextAnalyzerConfigLanguageField:
    """Test the language field on TextAnalyzerConfig (T001, T012)."""

    def test_language_field_accepts_none(self):
        """language=None should be accepted and default to English behavior."""
        config = TextAnalyzerConfig()
        assert config.language is None

    def test_language_field_accepts_en(self):
        """language='en' should be accepted."""
        config = TextAnalyzerConfig(language="en")
        assert config.language == "en"

    def test_language_field_accepts_ru(self):
        """language='ru' should be accepted."""
        config = TextAnalyzerConfig(language="ru")
        assert config.language == "ru"

    def test_language_field_accepts_other_languages(self):
        """language='de' should be accepted."""
        config = TextAnalyzerConfig(language="de")
        assert config.language == "de"

    def test_language_field_default_is_none(self):
        """Default language should be None (backward compatible)."""
        config = TextAnalyzerConfig()
        assert config.language is None


class TestStopWordsSelection:
    """Test stop words are selected based on language (T007, T012)."""

    def test_ru_language_uses_russian_stop_words(self):
        """language='ru' should use RU_STOP_WORDS instead of EN_STOP_WORDS."""
        config = TextAnalyzerConfig(
            language="ru",
            extractor_type=NounPhraseExtractorType.Syntactic,
            model_name="xx_ent_wiki_sm",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        # BaseNounPhraseExtractor uppercases exclude_nouns in __init__
        assert "И" in extractor.exclude_nouns
        assert "ИЛИ" in extractor.exclude_nouns
        assert "ЧТО" in extractor.exclude_nouns
        assert "НА" in extractor.exclude_nouns
        assert "STUFF" not in extractor.exclude_nouns
        assert "THING" not in extractor.exclude_nouns

    def test_en_language_uses_english_stop_words(self):
        """language='en' should use EN_STOP_WORDS (uppercased)."""
        config = TextAnalyzerConfig(
            language="en",
            extractor_type=NounPhraseExtractorType.Syntactic,
            model_name="en_core_web_md",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        assert "STUFF" in extractor.exclude_nouns
        assert "THING" in extractor.exclude_nouns
        assert "И" not in extractor.exclude_nouns
        assert "ИЛИ" not in extractor.exclude_nouns

    def test_none_language_uses_english_stop_words(self):
        """language=None (default) should use EN_STOP_WORDS (backward compat)."""
        config = TextAnalyzerConfig(
            extractor_type=NounPhraseExtractorType.Syntactic,
            model_name="en_core_web_md",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        assert "STUFF" in extractor.exclude_nouns
        assert "THING" in extractor.exclude_nouns
        assert "И" not in extractor.exclude_nouns

    def test_empty_string_language_uses_english_stop_words(self):
        """language='' should fallback to EN_STOP_WORDS."""
        config = TextAnalyzerConfig(
            language="",
            extractor_type=NounPhraseExtractorType.Syntactic,
            model_name="en_core_web_md",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        assert "STUFF" in extractor.exclude_nouns
        assert "И" not in extractor.exclude_nouns

    def test_custom_exclude_nouns_overrides_language(self):
        """Explicit exclude_nouns should bypass language-based selection."""
        custom_words = ["ПОЛЬЗОВАТЕЛЬСКОЕ", "CUSTOM"]
        config = TextAnalyzerConfig(
            language="ru",
            extractor_type=NounPhraseExtractorType.Syntactic,
            model_name="xx_ent_wiki_sm",
            exclude_nouns=custom_words,
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        assert "CUSTOM" in extractor.exclude_nouns
        assert "И" not in extractor.exclude_nouns
        assert "ИЛИ" not in extractor.exclude_nouns
        assert "STUFF" not in extractor.exclude_nouns

    def test_russian_stop_words_converted_from_frozenset_to_list(self):
        """RU_STOP_WORDS (frozenset) should be converted to list by factory."""
        config = TextAnalyzerConfig(
            language="ru",
            extractor_type=NounPhraseExtractorType.Syntactic,
            model_name="xx_ent_wiki_sm",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        assert isinstance(extractor.exclude_nouns, list)

    def test_syntactic_extractor_uses_language_stop_words(self):
        """Syntactic extractor should use language-based stop words."""
        config = TextAnalyzerConfig(
            language="ru",
            extractor_type=NounPhraseExtractorType.Syntactic,
            model_name="xx_ent_wiki_sm",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        assert "И" in extractor.exclude_nouns

    def test_regex_english_extractor_uses_language_stop_words(self):
        """RegexEnglish extractor should use language-based stop words."""
        config = TextAnalyzerConfig(
            language="ru",
            extractor_type=NounPhraseExtractorType.RegexEnglish,
            model_name="xx_ent_wiki_sm",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        assert "И" in extractor.exclude_nouns
        assert "STUFF" not in extractor.exclude_nouns


class TestCfgGrammarsSelection:
    """Test CFG grammars are selected based on language (T008, T013)."""

    def test_ru_language_uses_grammar_based_on_russian_patterns(self):
        """CFG extractor with language='ru' should use Russian-style grammar patterns."""
        config = TextAnalyzerConfig(
            language="ru",
            extractor_type=NounPhraseExtractorType.CFG,
            model_name="xx_ent_wiki_sm",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        cfg_extractor: Any = extractor
        assert len(cfg_extractor.noun_phrase_grammars) > 0
        has_tuple_keys = any(
            isinstance(k, tuple) for k in cfg_extractor.noun_phrase_grammars
        )
        assert has_tuple_keys, "Russian CFG grammars should use tuple keys"

    def test_en_language_uses_english_grammars(self):
        """CFG extractor with language='en' should use EN_NOUN_PHRASE_GRAMMARS."""
        config = TextAnalyzerConfig(
            language="en",
            extractor_type=NounPhraseExtractorType.CFG,
            model_name="en_core_web_md",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        cfg_ext: Any = extractor
        assert len(cfg_ext.noun_phrase_grammars) > 0

    def test_none_language_uses_english_grammars(self):
        """CFG extractor with language=None should use EN_NOUN_PHRASE_GRAMMARS."""
        config = TextAnalyzerConfig(
            extractor_type=NounPhraseExtractorType.CFG,
            model_name="en_core_web_md",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        cfg_ext: Any = extractor
        assert len(cfg_ext.noun_phrase_grammars) > 0

    def test_user_grammars_override_base_grammars(self):
        """User-provided grammars should override base language-based grammars."""
        custom_grammars = {"ADJ,NOUN": "CUSTOM_ADJ_NOUN"}
        config = TextAnalyzerConfig(
            language="ru",
            extractor_type=NounPhraseExtractorType.CFG,
            model_name="xx_ent_wiki_sm",
            noun_phrase_grammars=custom_grammars,
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        cfg_ext: Any = extractor
        assert ("ADJ", "NOUN") in cfg_ext.noun_phrase_grammars


class TestNlpModelAutoSelection:
    """Test spaCy model auto-selection from language (T017)."""

    def test_ru_language_auto_selects_ru_model(self):
        """language='ru' with no explicit model should auto-select ru_core_news_md."""
        config = TextAnalyzerConfig(
            language="ru",
            extractor_type=NounPhraseExtractorType.Syntactic,
            nlp_model=None,
            model_name="",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        model_name_str = extractor.model_name  # type: ignore
        assert model_name_str is not None
        assert "ru_core_news_md" in model_name_str

    def test_de_language_auto_selects_de_model(self):
        """language='de' with no explicit model should auto-select de_core_news_md."""
        config = TextAnalyzerConfig(
            language="de",
            extractor_type=NounPhraseExtractorType.Syntactic,
            nlp_model=None,
            model_name="",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        model_name_str = extractor.model_name  # type: ignore
        assert model_name_str is not None
        assert "de_core_news_md" in model_name_str

    def test_xx_language_auto_selects_multilingual_model(self):
        """language='xx' with no explicit model should auto-select xx_ent_wiki_sm."""
        config = TextAnalyzerConfig(
            language="xx",
            extractor_type=NounPhraseExtractorType.Syntactic,
            nlp_model=None,
            model_name="",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        model_name_str = extractor.model_name  # type: ignore
        assert model_name_str is not None
        assert "xx_ent_wiki_sm" in model_name_str

    def test_explicit_nlp_model_overrides_auto_selection(self):
        """Explicit nlp_model should override language-based auto-selection."""
        config = TextAnalyzerConfig(
            language="en",
            extractor_type=NounPhraseExtractorType.Syntactic,
            nlp_model="en_core_web_sm",
            model_name="",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        assert extractor.model_name == "en_core_web_sm"

    def test_explicit_model_name_overrides_auto_selection(self):
        """Explicit model_name should override language-based auto-selection."""
        config = TextAnalyzerConfig(
            language="en",
            extractor_type=NounPhraseExtractorType.Syntactic,
            nlp_model=None,
            model_name="en_core_web_sm",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        assert extractor.model_name == "en_core_web_sm"

    def test_none_language_defaults_to_en_model(self):
        """language=None with no model should default to en_core_web_md."""
        config = TextAnalyzerConfig(
            extractor_type=NounPhraseExtractorType.Syntactic,
            nlp_model=None,
            model_name="",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        model_name_str = extractor.model_name  # type: ignore
        assert model_name_str is not None
        assert "en_core_web_md" in model_name_str

    def test_unknown_language_defaults_to_en_model(self):
        """Unknown language with no model should default to en_core_web_md."""
        config = TextAnalyzerConfig(
            language="jp",
            extractor_type=NounPhraseExtractorType.Syntactic,
            nlp_model=None,
            model_name="",
        )
        extractor = NounPhraseExtractorFactory.get_np_extractor(config)
        model_name_str = extractor.model_name  # type: ignore
        assert model_name_str is not None
        assert "en_core_web_md" in model_name_str


class TestLanguageModelMap:
    """Test LANGUAGE_MODEL_MAP contents."""

    def test_language_model_map_contains_russian(self):
        """LANGUAGE_MODEL_MAP should contain ru -> ru_core_news_md."""
        assert "ru" in LANGUAGE_MODEL_MAP
        assert LANGUAGE_MODEL_MAP["ru"] == "ru_core_news_md"

    def test_language_model_map_contains_multilingual(self):
        """LANGUAGE_MODEL_MAP should contain xx -> xx_ent_wiki_sm."""
        assert "xx" in LANGUAGE_MODEL_MAP
        assert LANGUAGE_MODEL_MAP["xx"] == "xx_ent_wiki_sm"

    def test_language_model_map_contains_german(self):
        """LANGUAGE_MODEL_MAP should contain de -> de_core_news_md."""
        assert "de" in LANGUAGE_MODEL_MAP
        assert LANGUAGE_MODEL_MAP["de"] == "de_core_news_md"

    def test_language_model_map_contains_french(self):
        """LANGUAGE_MODEL_MAP should contain fr -> fr_core_news_md."""
        assert "fr" in LANGUAGE_MODEL_MAP
        assert LANGUAGE_MODEL_MAP["fr"] == "fr_core_news_md"

    def test_language_model_map_contains_spanish(self):
        """LANGUAGE_MODEL_MAP should contain es -> es_core_news_md."""
        assert "es" in LANGUAGE_MODEL_MAP
        assert LANGUAGE_MODEL_MAP["es"] == "es_core_news_md"
