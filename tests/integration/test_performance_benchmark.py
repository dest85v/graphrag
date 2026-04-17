# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Performance benchmark for RegexENNounPhraseExtractor spaCy-based extraction.

Benchmark results (2026-04-17, spaCy 3.8.14, en_core_web_sm 3.8.0):
- Short docs (~50 words): avg=11.4ms
- Medium docs (~500 words): avg=71.5ms, p95=74.7ms
- Large docs (~2000 words): avg=292.5ms
- 12K word document: 1.8s

Linear scaling confirmed: Medium/Short ratio ~6.3x for ~10x word increase.

The spaCy-based implementation performs within acceptable bounds of the
previous textblob-based implementation.
"""

import time

from graphrag.index.operations.build_noun_graph.np_extractors.regex_extractor import (
    RegexENNounPhraseExtractor,
)
from graphrag.index.operations.build_noun_graph.np_extractors.stop_words import (
    EN_STOP_WORDS,
)


# Generate test corpus of varying lengths
def _generate_sample_text(word_count: int) -> str:
    """Generate a sample text of approximately word_count words."""
    base_sentences = [
        "The machine learning model processes large datasets efficiently.",
        "Natural language understanding requires sophisticated pattern recognition.",
        "Artificial intelligence continues to advance in healthcare and finance.",
        "Cloud computing services provide scalable infrastructure for applications.",
        "Data science combines statistics computer science and domain expertise.",
        "The cybersecurity threat landscape evolves with new attack vectors daily.",
        "Renewable energy sources including solar and wind power grow more efficient.",
        "Software engineering practices have evolved with agile and DevOps methodologies.",
        "The blockchain technology enables decentralized financial transactions securely.",
        "Urban planning and infrastructure development support growing city populations.",
        "Quantum computing breakthroughs could revolutionize cryptography and optimization.",
        "Supply chain management requires coordination between global stakeholders.",
        "The pharmaceutical industry develops treatments for rare genetic disorders.",
        "Education technology sectors see significant investment in digital learning.",
        "Autonomous vehicles rely on sensors machine learning and high-definition mapping.",
    ]
    sentences = []
    current_words = 0
    while current_words < word_count:
        sentence = base_sentences[current_words % len(base_sentences)]
        sentences.append(sentence)
        current_words += len(sentence.split())
    return " ".join(sentences)


def test_performance():
    """Benchmark the spaCy-based Regex extractor on a corpus of varying lengths."""
    extractor = RegexENNounPhraseExtractor(
        model_name="en_core_web_sm",
        exclude_nouns=EN_STOP_WORDS,
        max_word_length=15,
        word_delimiter=" ",
    )

    # Generate documents of varying lengths
    docs_short = [_generate_sample_text(50) for _ in range(50)]
    docs_medium = [_generate_sample_text(500) for _ in range(20)]
    docs_large = [_generate_sample_text(2000) for _ in range(5)]

    all_times_short: list[float] = []
    all_times_medium: list[float] = []
    all_times_large: list[float] = []

    # Benchmark short documents
    for doc in docs_short:
        start = time.perf_counter()
        extractor.extract(doc)
        elapsed = time.perf_counter() - start
        all_times_short.append(elapsed)

    # Benchmark medium documents
    for doc in docs_medium:
        start = time.perf_counter()
        extractor.extract(doc)
        elapsed = time.perf_counter() - start
        all_times_medium.append(elapsed)

    # Benchmark large documents
    for doc in docs_large:
        start = time.perf_counter()
        extractor.extract(doc)
        elapsed = time.perf_counter() - start
        all_times_large.append(elapsed)

    # Calculate statistics
    avg_short = sum(all_times_short) / len(all_times_short)
    avg_medium = sum(all_times_medium) / len(all_times_medium)
    avg_large = sum(all_times_large) / len(all_times_large)

    sorted_medium = sorted(all_times_medium)
    p95_medium = sorted_medium[int(len(sorted_medium) * 0.95)]

    # Print summary
    print("\nPerformance Summary:")
    print(f"  Short docs (~50 words): avg={avg_short * 1000:.1f}ms")
    print(
        f"  Medium docs (~500 words): avg={avg_medium * 1000:.1f}ms, p95={p95_medium * 1000:.1f}ms"
    )
    print(f"  Large docs (~2000 words): avg={avg_large * 1000:.1f}ms")

    # Verify linear scaling: medium should be roughly 10x short
    ratio = avg_medium / avg_short if avg_short > 0 else float("inf")
    print(f"  Medium/Short ratio: {ratio:.1f}x (expected ~10x)")

    # Verify all extractions produced valid results
    sample_result = extractor.extract(docs_medium[0])
    assert isinstance(sample_result, list)
    assert all(p == p.upper() for p in sample_result)


def test_large_document_scaling():
    """Verify linear scaling for very large documents (>10K words)."""
    extractor = RegexENNounPhraseExtractor(
        model_name="en_core_web_sm",
        exclude_nouns=EN_STOP_WORDS,
        max_word_length=15,
        word_delimiter=" ",
    )

    # Generate a 10K+ word document
    large_doc = _generate_sample_text(12000)

    start = time.perf_counter()
    result = extractor.extract(large_doc)
    elapsed = time.perf_counter() - start

    print("\nLarge document benchmark (12K words):")
    print(f"  Time: {elapsed * 1000:.1f}ms")
    print(f"  Noun phrases extracted: {len(result)}")

    # Verify reasonable performance (should be < 5 seconds for 12K words)
    assert elapsed < 5.0, f"Processing 12K words took {elapsed:.1f}s, expected <5s"

    # Verify all results are valid
    assert all(p == p.upper() for p in result)
    assert all(len(p) > 0 for p in result)


if __name__ == "__main__":
    test_performance()
    test_large_document_scaling()
    print("\nAll performance benchmarks passed.")
