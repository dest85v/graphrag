# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Create a noun phrase extractor from a configuration."""

from typing import ClassVar

from graphrag.config.enums import NounPhraseExtractorType
from graphrag.config.models.extract_graph_nlp_config import TextAnalyzerConfig
from graphrag.index.operations.build_noun_graph.np_extractors.base import (
    BaseNounPhraseExtractor,
)
from graphrag.index.operations.build_noun_graph.np_extractors.cfg_extractor import (
    CFG_NOUN_PHRASE_GRAMMARS,
    EN_NOUN_PHRASE_GRAMMARS,
    CFGNounPhraseExtractor,
)
from graphrag.index.operations.build_noun_graph.np_extractors.regex_extractor import (
    RegexENNounPhraseExtractor,
)
from graphrag.index.operations.build_noun_graph.np_extractors.stop_words import (
    EN_STOP_WORDS,
    RU_STOP_WORDS,
)
from graphrag.index.operations.build_noun_graph.np_extractors.syntactic_parsing_extractor import (
    SyntacticNounPhraseExtractor,
)

LANGUAGE_MODEL_MAP: dict[str, str] = {
    "ru": "ru_core_news_md",
    "de": "de_core_news_md",
    "fr": "fr_core_news_md",
    "es": "es_core_news_md",
    "xx": "xx_ent_wiki_sm",
}

DEFAULT_MODEL = "en_core_web_md"


class NounPhraseExtractorFactory:
    """A factory class for creating noun phrase extractor."""

    np_extractor_types: ClassVar[dict[str, type]] = {}

    @classmethod
    def register(cls, np_extractor_type: str, np_extractor: type):
        """Register a vector store type."""
        cls.np_extractor_types[np_extractor_type] = np_extractor

    @classmethod
    def get_np_extractor(cls, config: TextAnalyzerConfig) -> BaseNounPhraseExtractor:
        """Get the noun phrase extractor type from a string."""
        np_extractor_type = config.extractor_type
        language = (config.language or "").lower()
        exclude_nouns = config.exclude_nouns
        if exclude_nouns is None:
            exclude_nouns = list(RU_STOP_WORDS) if language == "ru" else EN_STOP_WORDS
        effective_model_name = config.nlp_model or config.model_name
        if not effective_model_name:
            effective_model_name = LANGUAGE_MODEL_MAP.get(language, DEFAULT_MODEL)
        match np_extractor_type:
            case NounPhraseExtractorType.Syntactic:
                return SyntacticNounPhraseExtractor(
                    model_name=effective_model_name,
                    max_word_length=config.max_word_length,
                    include_named_entities=config.include_named_entities,
                    exclude_entity_tags=config.exclude_entity_tags,
                    exclude_pos_tags=config.exclude_pos_tags,
                    exclude_nouns=exclude_nouns,
                    word_delimiter=config.word_delimiter,
                )
            case NounPhraseExtractorType.CFG:
                grammars = {}
                for key, value in config.noun_phrase_grammars.items():
                    grammars[tuple(key.split(","))] = value
                if not grammars:
                    if language == "ru":
                        grammars.update(CFG_NOUN_PHRASE_GRAMMARS)
                    else:
                        for key, value in EN_NOUN_PHRASE_GRAMMARS.items():
                            grammars[tuple(key.split(","))] = value
                return CFGNounPhraseExtractor(
                    model_name=effective_model_name,
                    max_word_length=config.max_word_length,
                    include_named_entities=config.include_named_entities,
                    exclude_entity_tags=config.exclude_entity_tags,
                    exclude_pos_tags=config.exclude_pos_tags,
                    exclude_nouns=exclude_nouns,
                    word_delimiter=config.word_delimiter,
                    noun_phrase_grammars=grammars,
                    noun_phrase_tags=config.noun_phrase_tags,
                )
            case NounPhraseExtractorType.RegexEnglish:
                return RegexENNounPhraseExtractor(
                    model_name=effective_model_name,
                    exclude_nouns=exclude_nouns,
                    max_word_length=config.max_word_length,
                    word_delimiter=config.word_delimiter,
                )


def create_noun_phrase_extractor(
    analyzer_config: TextAnalyzerConfig,
) -> BaseNounPhraseExtractor:
    """Create a noun phrase extractor from a configuration."""
    return NounPhraseExtractorFactory.get_np_extractor(analyzer_config)
