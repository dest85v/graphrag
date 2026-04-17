# Quickstart: RegexENNounPhraseExtractor (spaCy)

## Overview

`RegexENNounPhraseExtractor` is an English-only noun phrase extractor that uses spaCy for tokenization, POS tagging, and noun chunk detection. This quickstart covers setup, configuration, and usage.

## Setup

### Prerequisites

- Python 3.11, 3.12, or 3.13
- GraphRAG monorepo with `uv` installed

### Installation

The extractor is part of the `graphrag` package. No additional dependencies need to be installed — `spacy~=3.8` is already a transitive dependency.

```bash
uv sync
```

### Model Download

On first use, the extractor automatically downloads the `en_core_web_sm` spaCy model:

```python
from graphrag.index.operations.build_noun_graph.np_extractors.regex_extractor import RegexENNounPhraseExtractor

extractor = RegexENNounPhraseExtractor(
    exclude_nouns=["stuff", "thing", "things"],
    max_word_length=15,
    word_delimiter=" ",
)
# First call triggers model download if not cached
phrases = extractor.extract("Sample text to extract noun phrases from")
```

You can also pre-download the model manually:

```bash
python -m spacy download en_core_web_sm
```

## Configuration

### Via TextAnalyzerConfig

```python
from graphrag.config.models.extract_graph_nlp_config import TextAnalyzerConfig
from graphrag.index.operations.build_noun_graph.np_extractors.factory import create_noun_phrase_extractor

config = TextAnalyzerConfig(
    extractor_type="regex_english",
    model_name="en_core_web_sm",
    max_word_length=15,
    exclude_nouns=["stuff", "thing", "things", "bunch"],
    word_delimiter=" ",
    include_named_entities=False,
    exclude_entity_tags=[],
    exclude_pos_tags=[],
    noun_phrase_grammars={},
    noun_phrase_tags=[],
)

extractor = create_noun_phrase_extractor(config)
```

### Via YAML config

```yaml
index:
  text_analyzer:
    extractor_type: "regex_english"
    model_name: "en_core_web_sm"
    max_word_length: 15
    exclude_nouns:
      - "stuff"
      - "thing"
      - "things"
      - "bunch"
      - "bit"
      - "bits"
      - "people"
      - "person"
    word_delimiter: " "
```

## Usage

### Basic extraction

```python
from graphrag.index.operations.build_noun_graph.np_extractors.regex_extractor import RegexENNounPhraseExtractor

extractor = RegexENNounPhraseExtractor(
    exclude_nouns=["stuff", "thing"],
    max_word_length=15,
)

text = "The quick brown fox jumps over the lazy dog. Machine learning algorithms are transforming industries."
phrases = extractor.extract(text)
# Result: ["QUICK BROWN FOX", "LAZY DOG", "MACHINE LEARNING ALGORITHMS", "INDUSTRIES"]
```

### Edge cases

```python
# Empty text
extractor.extract("")  # []

# None handling (caller responsibility — extractor expects str)

# Non-English text
extractor.extract("Bonjour le monde")  # [] (graceful degradation)

# Unicode
extractor.extract("Café résumé naïve")  # ["CAFÉ", "RÉSUMÉ", "NAÏVE"] (if valid tokens)
```

### Cache key

```python
extractor = RegexENNounPhraseExtractor(
    exclude_nouns=["stuff", "thing"],
    max_word_length=15,
    word_delimiter=" ",
)
print(str(extractor))
# Output: regex_en_en_core_web_sm_[stuff,thing]_15_
```

## Testing

### Run unit tests

```bash
uv run poe test_unit -k "regex"
```

### Run integration tests

```bash
uv run poe test_integration -k "noun_phrase"
```

### Run full check

```bash
uv run poe check
```
