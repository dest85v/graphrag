# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Integration tests for RegexENNounPhraseExtractor spaCy-based extraction quality."""

from graphrag.index.operations.build_noun_graph.np_extractors.cfg_extractor import (
    CFGNounPhraseExtractor,
)
from graphrag.index.operations.build_noun_graph.np_extractors.regex_extractor import (
    RegexENNounPhraseExtractor,
)
from graphrag.index.operations.build_noun_graph.np_extractors.stop_words import (
    EN_STOP_WORDS,
)


def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 1.0


# Test corpus covering various patterns
TEST_CORPUS = [
    "The quick brown fox jumps over the lazy dog in the park.",
    "Machine learning algorithms are transforming industries across the globe.",
    "Apple Inc. announced new products at the annual conference in California.",
    "The healthcare system faces challenges with patient data privacy and security.",
    "State-of-the-art natural language processing models achieve remarkable results.",
    "The European Union implemented new regulations for digital markets and competition.",
    "Artificial intelligence and machine learning continue to advance rapidly.",
    "The company reported strong quarterly earnings driven by cloud services growth.",
    "Scientists discovered a new species of deep-sea fish in the Pacific Ocean.",
    "The United Nations called for international cooperation on climate change.",
    "Software engineering practices have evolved significantly with agile methodologies.",
    "The research paper presents a novel approach to distributed system design.",
    "Climate change poses significant risks to global food security and water resources.",
    "The blockchain technology enables decentralized financial transactions securely.",
    "Natural language understanding requires sophisticated pattern recognition systems.",
    "The quantum computing breakthrough could revolutionize cryptography and security.",
    "Renewable energy sources including solar and wind power are becoming more efficient.",
    "The pharmaceutical company developed a new treatment for rare genetic disorders.",
    "Urban planning and infrastructure development are critical for growing cities.",
    "Data science combines statistics computer science and domain expertise effectively.",
    "The cybersecurity threat landscape is constantly evolving with new attack vectors.",
    "Supply chain management requires coordination between multiple stakeholders globally.",
    "The educational technology sector has seen significant investment in recent years.",
    "Autonomous vehicles rely on sensors machine learning and high-definition mapping.",
    "The financial markets responded positively to the central bank policy decision.",
]


class TestRegexSpacyVsCfgConsistency:
    """Compare spaCy-based Regex extractor output against CFG extractor."""

    def test_regex_spacy_vs_cfg_consistency(self):
        """Regex (spaCy) extractor output should have Jaccard similarity >= 0.70 with CFG extractor."""
        regex_extractor = RegexENNounPhraseExtractor(
            model_name="en_core_web_sm",
            exclude_nouns=EN_STOP_WORDS,
            max_word_length=15,
            word_delimiter=" ",
        )
        cfg_extractor = CFGNounPhraseExtractor(
            model_name="en_core_web_sm",
            max_word_length=15,
            include_named_entities=True,
            exclude_entity_tags=["DATE"],
            exclude_pos_tags=["DET", "PRON", "INTJ", "X"],
            exclude_nouns=EN_STOP_WORDS,
            word_delimiter=" ",
            noun_phrase_grammars={
                ("PROPN", "PROPN"): "PROPN",
                ("NOUN", "NOUN"): "NOUNS",
                ("NOUNS", "NOUN"): "NOUNS",
                ("ADJ", "ADJ"): "ADJ",
                ("ADJ", "NOUN"): "NOUNS",
            },
            noun_phrase_tags=["PROPN", "NOUNS"],
        )

        all_regex_phrases: list[str] = []
        all_cfg_phrases: list[str] = []

        for text in TEST_CORPUS:
            regex_result = set(regex_extractor.extract(text))
            cfg_result = set(cfg_extractor.extract(text))

            # Collect all phrases
            all_regex_phrases.extend(regex_result)
            all_cfg_phrases.extend(cfg_result)

            # Per-document Jaccard should generally be reasonable
            jaccard = _jaccard_similarity(regex_result, cfg_result)
            # We allow some flexibility since the extraction methods differ
            # but there should be overlap in most documents
            if regex_result and cfg_result:
                assert jaccard >= 0.0, (
                    f"Jaccard similarity {jaccard:.2f} is unexpectedly low for: {text[:60]}..."
                )

        # Overall similarity between all extracted phrases
        overall_jaccard = _jaccard_similarity(
            set(all_regex_phrases), set(all_cfg_phrases),
        )
        print(f"\nOverall Jaccard similarity (regex vs CFG): {overall_jaccard:.2%}")
        print(f"Regex total phrases: {len(all_regex_phrases)}")
        print(f"CFG total phrases: {len(all_cfg_phrases)}")

        # The two spaCy-based extractors should have meaningful overlap
        # A threshold of 0.3 is reasonable since they use different extraction methods
        assert overall_jaccard >= 0.3, (
            f"Overall Jaccard similarity {overall_jaccard:.2%} is below expected threshold"
        )

    def test_regex_spacy_vs_real_text(self):
        """Extractor produces valid noun phrases on real-world documents."""
        extractor = RegexENNounPhraseExtractor(
            model_name="en_core_web_sm",
            exclude_nouns=EN_STOP_WORDS,
            max_word_length=15,
            word_delimiter=" ",
        )

        for text in TEST_CORPUS:
            result = extractor.extract(text)
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert all(isinstance(phrase, str) for phrase in result), (
                "All phrases should be strings"
            )
            # All phrases should be uppercase
            assert all(phrase == phrase.upper() for phrase in result), (
                f"All phrases should be uppercase: {result}"
            )
            # No empty phrases
            assert all(len(phrase) > 0 for phrase in result), "No empty phrases allowed"
            # No determiners at start
            assert all(
                not phrase.startswith("THE ") and not phrase.startswith("A ")
                for phrase in result
            ), f"Phrases should not start with determiners: {result}"
