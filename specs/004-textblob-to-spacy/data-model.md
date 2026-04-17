# Data Model: RegexENNounPhraseExtractor (spaCy migration)

## Overview

`RegexENNounPhraseExtractor` is a stateless noun phrase extraction service. It does not persist data — it transforms input text into a list of uppercase noun phrases. The "data model" here describes the class structure, attributes, and filtering pipeline.

## Class: RegexENNounPhraseExtractor

### Attributes

| Attribute | Type | Description | Constraint |
|---|---|---|---|
| `model_name` | `str` | spaCy model name (e.g., `"en_core_web_sm"`) | Set at init, immutable |
| `max_word_length` | `int` | Maximum length (in characters) of each extracted word | Default: 15, must be > 0 |
| `exclude_nouns` | `list[str]` | Stop words to exclude from noun phrases | Stored as uppercase, default: EN_STOP_WORDS |
| `word_delimiter` | `str` | Delimiter for joining tokens in output | Default: `" "` |
| `nlp` | `spacy.language.Language` | spaCy pipeline instance | Loaded once at init |

### Input/Output

| Item | Type | Description |
|---|---|---|
| Input | `text: str` | Raw text for noun phrase extraction |
| Output | `list[str]` | List of uppercase noun phrases, deduplicated |

### Processing Pipeline

```
text → spaCy pipeline → doc (Doc object)
                        ↓
         doc.noun_chunks → list of chunk.text
         doc.ents (PROPN) → proper_nouns set (via token.pos_ == "PROPN")
                        ↓
         For each chunk:
           split into tokens
           filter exclude_nouns → cleaned_tokens
           check has_proper_nouns (PROPN in chunk)
           check has_compound_words (is_compound(cleaned_tokens))
           check has_valid_tokens (is_valid_token_length + regex)
                        ↓
         Filter: has_proper_nouns OR (len(cleaned_tokens) > 1 OR has_compound_words) AND has_valid_tokens
                        ↓
         Join with word_delimiter → upper() → deduplicate → list[str]
```

### Tagging Result (intermediate representation)

Each noun phrase is tagged with attributes for filtering:

| Attribute | Type | Description |
|---|---|---|
| `cleaned_tokens` | `list[str]` | Tokens after stop-word removal |
| `cleaned_text` | `str` | Joined, uppercased, newline-stripped phrase |
| `has_proper_nouns` | `bool` | True if any token is a proper noun (PROPN) |
| `has_compound_words` | `bool` | True if any token contains `-` with multiple parts |
| `has_valid_tokens` | `bool` | True if all tokens match `^[a-zA-Z0-9\-]+$` and length <= max_word_length |

### Relationships

| Relationship | Description |
|---|---|
| `RegexENNounPhraseExtractor` → `BaseNounPhraseExtractor` | Inherits base class with shared init params and `load_spacy_model()` |
| `RegexENNounPhraseExtractor` → `np_validator.py` | Reuses `is_compound()` and `has_valid_token_length()` |
| `RegexENNounPhraseExtractor` → `stop_words.py` | Uses `EN_STOP_WORDS` as default `exclude_nouns` |
| `RegexENNounPhraseExtractor` → `NounPhraseExtractorFactory` | Registered factory entry for `NounPhraseExtractorType.RegexEnglish` |
| `RegexENNounPhraseExtractor` → `CFGNounPhraseExtractor` | Shares `np_validator.py` helpers and `BaseNounPhraseExtractor` base |

## Validation Rules

| Rule | Source | Description |
|---|---|---|
| Token length | `has_valid_token_length()` | No token > `max_word_length` characters |
| Token content | Regex `^[a-zA-Z0-9\-]+$` | Only alphanumeric, hyphens, and newlines (stripped) |
| Stop word exclusion | `self.exclude_nouns` | Tokens matching excluded words are removed before processing |
| Phrase minimum | `has_proper_nouns OR (len > 1 OR compound)` | Single common nouns are only kept if they're compound or part of multi-word phrase |
| Deduplication | `set()` | Duplicate noun phrases (case-insensitive via `.upper()`) are removed |
