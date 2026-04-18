# Quickstart: Multilingual Sentence Tokenization

## TL;DR

Add `nltk_language: russian` (or any supported language) to your `config.yaml` `chunking` section when using `chunking.type: sentence`. Default is `"english"` — zero change for existing configs.

## Configuration

### English (default — no config change needed)

```yaml
chunking:
  type: sentence
  size: 1200
  overlap: 100
```

### Russian

```yaml
chunking:
  type: sentence
  nltk_language: russian
  size: 1200
  overlap: 100
```

### German, French, Spanish

```yaml
chunking:
  type: sentence
  nltk_language: german   # or french, spanish, italian, portuguese, dutch, ...
  size: 1200
  overlap: 100
```

## How It Works

1. `graphrag index` reads `config.yaml` → `ChunkingConfig(nltk_language="russian")`
2. `create_chunker()` passes `nltk_language` to `SentenceChunker.__init__()`
3. `SentenceChunker` stores `self._nltk_language = "russian"`
4. On `chunk()`, calls `nltk.sent_tokenize(text, language="russian")`
5. NLTK uses the Russian PUNKT model from `punkt_tab` to split sentences

## Supported Languages

The following language codes are supported by NLTK PUNKT (in `punkt_tab`):

`english`, `russian`, `german`, `french`, `spanish`, `portuguese`, `italian`, `dutch`, `norwegian`, `swedish`, `danish`, `finnish`, `greek`, `turkish`, `polish`, `catalan`, `romanian`, `croatian`, `serbian`, `chinese`, `arabic`, `japanese`, `hungarian`, `hindi`

## Notes

- **NLTK auto-downloads** the language model on first use (cached in `~/.nltk/`)
- **Only affects `chunking.type: sentence`** — `type: tokens` is unchanged
- **Mixed-language text**: uses the configured language model; non-configured languages may have degraded quality
- **Invalid language**: NLTK raises `LookupError: Unknown punkt language "<code>"`
