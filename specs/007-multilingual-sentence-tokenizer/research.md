# Research: NLTK Multilingual Sentence Tokenizer

## Decision: Use `nltk.sent_tokenize(language=...)` parameter

**Rationale**: NLTK's `sent_tokenize()` has supported the `language` parameter since version 3.8.2. NLTK 3.9+ (already in project dependencies) includes `punkt_tab` which contains pre-trained models for 10+ languages including Russian, German, French, Spanish, and others. This is the simplest, most maintainable approach with zero new dependencies.

**Alternatives considered**:

| Alternative | Why Rejected |
|---|---|
| Custom sentence boundary detection (regex-based) | Fragile, doesn't handle abbreviations, quotes, ellipses properly. NLTK Punkt is production-tested. |
| Use spaCy sentence boundaries | spaCy already used for NLP graph extraction (P1 language-aware factory). Adding it to chunking would be a larger dependency shift. Punkt is sufficient for sentence splitting. |
| Use `regex` library with Unicode-aware patterns | Over-engineered. punkt_tab models handle language-specific sentence boundary rules (e.g., French "M." abbreviation, German compound sentences). |
| Add a new chunking strategy class | Unnecessary complexity. `SentenceChunker` already exists; just parameterize it. |

## Decision: Default value is `"english"` for backward compatibility

**Rationale**: Existing configs without `nltk_language` field must produce identical output. NLTK's `sent_tokenize()` defaults to English anyway, so `language="english"` is functionally a no-op for existing users.

**Alternatives considered**:

| Alternative | Why Rejected |
|---|---|
| Auto-detect language from document content | Adds significant complexity (requires language detection library, per-document processing overhead). P2 scope creep. |
| Default to `"auto"` or `None` with language detection | NLTK doesn't support auto-detection. Would require external dependency. |

## Decision: No changes to `bootstrap_nltk.py`

**Rationale**: `punkt_tab` is already downloaded by the existing bootstrap at `bootstrap_nltk.py:23`. Multilingual models are bundled within `punkt_tab` (not separate downloads). No changes needed.

## Decision: No custom error handling for invalid languages

**Rationale**: NLTK's built-in error for unknown language (`LookupError: Unknown punkt language`) is sufficiently clear. Adding custom error handling adds code surface area for a rare edge case. Per FR-009, invalid values should fail gracefully with NLTK's built-in error.

## Decision: Config field flows through `extra="allow"` — no explicit type binding

**Rationale**: `ChunkingConfig.model_config = ConfigDict(extra="allow")` means any extra field is passed through to `model_dump()` → `init_args` → chunker `__init__()`. The `nltk_language` field will be present in the config dict and passed to `SentenceChunker.__init__(**kwargs)`. No explicit pydantic field definition needed in `ChunkingConfig` since we're using `extra="allow"`.

Wait — actually, we DO need an explicit field for:
1. Type safety in `SentenceChunker.__init__()` type hints
2. `ChunkingDefaults` default value in `graphrag` package
3. Config template documentation in `init_content.py`
4. `poe check` (pyright) won't flag an unknown field if it's defined

So: explicit `nltk_language: str = "english"` in `ChunkingConfig` is required.
