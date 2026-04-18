# Quickstart: Russian Language Support in GraphRAG

## Prerequisites

Install Russian or multilingual spaCy models:

```bash
# For Russian text only:
uv run python -m spacy download ru_core_news_md

# For multilingual (RU + EN + others):
uv run python -m spacy download xx_ent_wiki_sm
```

## Basic Usage: Russian Documents

1. **Configure** your `graphrag.yaml`:

   ```yaml
   models:
     graph_extraction:
       strategy:
         type: graphrag_nlp
         config:
           nlp_model: "ru_core_news_md"
           extractor_type: syntactic  # recommended for Russian
   ```

2. **Run** indexing:
   ```bash
   graphrag index --root ./data
   ```

3. **Query** in Russian:
   ```bash
   graphrag query --method local --query "Что такое внутренний аудит?"
   ```

## Mixed RU+EN Text

For documents with both Russian and English terms (e.g., technical documentation):

```yaml
models:
  graph_extraction:
    strategy:
      type: graphrag_nlp
      config:
        nlp_model: "xx_ent_wiki_sm"  # multilingual NER
        extractor_type: syntactic
```

The `xx_ent_wiki_sm` model handles Russian, English, and other languages in a single model.

## Using RegexExtractor with Unicode

The RegexExtractor now supports Unicode tokens. For mixed RU+EN text with the regex extractor:

```yaml
models:
  graph_extraction:
    strategy:
      type: graphrag_nlp
      config:
        nlp_model: "ru_core_news_md"
        extractor_type: regex_english  # now Unicode-aware
```

**Note**: `syntactic` extractor is recommended for Russian text as it uses spaCy's full syntactic parser, which provides better noun phrase detection for Slavic languages.

## Custom Model

Any spaCy model name can be specified:

```yaml
models:
  graph_extraction:
    strategy:
      type: graphrag_nlp
      config:
        nlp_model: "my-custom-model"  # must be installed via spacy install
        extractor_type: syntactic
```

If the model is not found, GraphRAG will attempt to download it automatically.

## Troubleshooting

### "Model not found" error

```
OSError: Model `ru_core_news_md` not found. Attempting to download...
```

**Solution**: Install the model manually:
```bash
uv run python -m spacy download ru_core_news_md
```

### Poor noun phrase extraction quality

- Try `extractor_type: syntactic` instead of `regex_english`
- Try `nlp_model: xx_ent_wiki_sm` for better multilingual coverage
- Adjust `max_word_length` if long compound terms are cut off

### Stop words filtering

Custom stop words can be passed in the config:
```yaml
models:
  graph_extraction:
    strategy:
      type: graphrag_nlp
      config:
        nlp_model: "ru_core_news_md"
        exclude_nouns:
          - "СИСТЕМА"
          - "ПРОЦЕСС"
```
