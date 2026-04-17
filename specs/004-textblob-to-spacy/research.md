# Research: RegexENNounPhraseExtractor migration from textblob to spaCy

## Decision: Use `doc.noun_chunks` + POS/NER filtering with `en_core_web_sm`

**Rationale**: spaCy's `doc.noun_chunks` provides the most direct equivalent to TextBlob's `noun_phrases` property. Combined with `token.pos_` (PROPN, NOUN) and `doc.ents` for named entities, it covers all filtering logic currently implemented in `RegexENNounPhraseExtractor._tag_noun_phrases()`.

**Model**: `en_core_web_sm` — the smallest English model, already download-capable via `spacy.cli.download`. This matches the existing `load_spacy_model()` pattern in `BaseNounPhraseExtractor`.

**Why not `doc.ents` only**: Named entities alone miss valid noun phrases (e.g., "machine learning algorithm"). noun_chunks are "base noun phrases" with a noun as head — the right source.

**Why not a larger model** (`en_core_web_md`/`en_core_web_lg`): The existing CFGNounPhraseExtractor uses `en_core_web_sm`-level models. Switching to a larger model would change performance characteristics across the board, not just for this extractor. Keep scope tight.

## Decision: Map textblob behavior → spaCy attributes

| textblob attribute | spaCy equivalent | Usage |
|---|---|---|
| `blob.tags` (POS tag pairs) | `[(token.text, token.pos_) for token in doc]` | Build proper_nouns set |
| `blob.noun_phrases` | `[chunk.text for chunk in doc.noun_chunks]` | Source noun phrases |
| `token[0]` (raw token) | `token.text` | Individual token access |

### POS tag mapping

TextBlob uses Penn Treebank POS tags (NNP, NN, NNS, etc.). spaCy uses Universal POS tags:

| spaCy `token.pos_` | Description | Used for |
|---|---|---|
| `PROPN` | Proper noun | `has_proper_nouns` check |
| `NOUN` | Common noun | Part of noun chunks |
| `ADJ` | Adjective | Modifier in noun chunks |
| `DET` | Determiner | Filtered out (not included in phrase) |
| `ADP` | Adposition | Filtered out |
| `AUX` | Auxiliary verb | Filtered out |
| `VERB` | Verb | Filtered out |
| `ADV` | Adverb | Filtered out |

The `has_proper_nouns` check becomes: `any(token.pos_ == "PROPN" for token in doc)`.

## Decision: Preserve filtering logic exactly

The current `_tag_noun_phrases()` logic must be preserved 1:1 in behavior:

1. **Exclusion**: Tokens whose `upper()` form is in `self.exclude_nouns` are removed → same check
2. **Proper nouns**: Any cleaned token is a proper noun if its upper() form is in the pre-computed proper_nouns set → becomes `any(token.pos_ == "PROPN" for token in cleaned_chunk)`
3. **Compound words**: Tokens containing `-` with multiple parts → reuse existing `is_compound()` from `np_validator.py`
4. **Valid tokens**: All tokens match `^[a-zA-Z0-9\-]+\n?$` and length <= max_word_length → reuse `has_valid_token_length()` + regex check from `np_validator.py`

The key difference: instead of using NLTK corpora (brown, treebank) and the averaged perceptron tagger, we use spaCy's built-in pipeline.

## Decision: No NLTK corpus downloads

Current code downloads 5 NLTK resources: `brown`, `treebank`, `punkt`, `punkt_tab`, `averaged_perceptron_tagger_eng`. These are all replaced by the single spaCy model download (`en_core_web_sm`).

The `download_if_not_exists()` function in `resource_loader.py` should NOT be modified — it is used by CFGNounPhraseExtractor and SyntacticNounPhraseExtractor for spaCy model downloads. The Regex extractor will use `load_spacy_model()` from base.py directly (same as other spaCy-based extractors).

## Decision: API compatibility

The `__init__` signature of `RegexENNounPhraseExtractor` stays unchanged:
- `exclude_nouns: list[str]`
- `max_word_length: int`
- `word_delimiter: str`

The `extract(text: str) -> list[str]` signature stays unchanged.
The `__str__()` return value format changes from `regex_en_{exclude}_{max}_{delim}` to `regex_en_{model}_{exclude}_{max}_{delim}` (model name added for cache key granularity) — but since model_name was already `None` and is now a fixed string, the cache key will change. This is acceptable because:
- The old cache entries will be invalidated (no correctness issue, just re-extraction)
- The behavior is verified equivalent via tests

## Decision: Use existing `np_validator.py` helpers

Reuse `is_compound()` and `has_valid_token_length()` from `np_validator.py` — these are pure utility functions with no spaCy/textblob coupling. This avoids code duplication with `CFGNounPhraseExtractor` and `SyntacticNounPhraseExtractor`.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Use `en_core_web_md` or `en_core_web_lg` | Larger models change performance characteristics for ALL extractors, not just Regex. Scope creep beyond P0. |
| Use spaCy's `Matcher` / `PhraseMatcher` for noun phrase rules | Overkill — `noun_chunks` + POS filtering is sufficient and more maintainable than custom pattern rules. |
| Keep textblob as optional dependency, add spaCy as new path | Adds conditional complexity for a P0 cleanup task. Single path is cleaner. |
| Implement custom POS tagger with spaCy's `Tagger` component | Unnecessary — `noun_chunks` already uses the parser which includes POS tagging. Adding a separate tagger is redundant. |
| Use `doc.concords` or `doc.sentences` instead of `noun_chunks` | `concords` is for keyword-in-context, `sentences` is too coarse. `noun_chunks` is the correct API. |
