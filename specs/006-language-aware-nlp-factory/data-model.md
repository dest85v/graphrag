# Data Model: Language-Aware NLP Factory

**Feature**: `006-language-aware-nlp-factory`
**Date**: 2026-04-18

## TextAnalyzerConfig

Configuration model for NLP text analyzer. Single file change: `extract_graph_nlp_config.py`.

### Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `extractor_type` | `NounPhraseExtractorType` | `RegexEnglish` | Extractor strategy |
| `model_name` | `str` | `"en_core_web_md"` | Default spaCy model name |
| `nlp_model` | `str \| None` | `None` | Override model name |
| `max_word_length` | `int` | `15` | Max word character length |
| `word_delimiter` | `str` | `" "` | Word delimiter character |
| `include_named_entities` | `bool` | `True` | Include NER in extraction |
| `exclude_nouns` | `list[str] \| None` | `EN_STOP_WORDS` | Stop words list |
| `exclude_entity_tags` | `list[str]` | `["DATE"]` | NER tags to exclude |
| `exclude_pos_tags` | `list[str]` | `["DET", "PRON", "INTJ", "X"]` | POS tags to exclude |
| `noun_phrase_tags` | `list[str]` | `["PROPN", "NOUNS"]` | Valid output POS tags |
| `noun_phrase_grammars` | `dict[str, str]` | English CFG defaults | CFG grammar rules |
| **`language`** | **`str \| None`** | **`None`** | **NEW**: Document language. Selects stop words & CFG grammars. Supported: `en`, `ru`. Others → English fallback. |

### New field: `language`

```python
language: str | None = Field(
    default=None,
    description="Document language for selecting appropriate stop words and CFG grammars (e.g., 'en', 'ru'). Falls back to English defaults if not set.",
)
```

**Behavior**:
- `None` or `""` → English (backward compatible)
- `"en"` → English
- `"ru"` → Russian (RU_STOP_WORDS + CFG_NOUN_PHRASE_GRAMMARS)
- Other → English fallback

### Internal behavior changes (not in schema)

**`exclude_nouns` resolution** (in factory):
```
IF exclude_nouns is None:
    IF language == "ru":
        exclude_nouns = list(RU_STOP_WORDS)
    ELSE:
        exclude_nouns = EN_STOP_WORDS
ELSE:
    exclude_nouns = exclude_nouns  # user-provided, no change
```

**`noun_phrase_grammars` resolution** (in factory, CFG only):
```
IF noun_phrase_grammars is empty:
    IF language == "ru":
        grammars = CFG_NOUN_PHRASE_GRAMMARS
    ELSE:
        grammars = EN_NOUN_PHRASE_GRAMMARS
# Apply user grammars on top
grammars.update(user_grammars)
```

**`effective_model_name` resolution** (optional, P2):
```
IF nlp_model is None AND model_name is None:
    effective_model_name = LANGUAGE_MODEL_MAP.get(language, "en_core_web_md")
ELSE:
    effective_model_name = nlp_model or model_name
```

## Grammar Constants

### `EN_NOUN_PHRASE_GRAMMARS` (extracted from defaults.py)

```python
EN_NOUN_PHRASE_GRAMMARS: dict[str, str] = {
    "PROPN,PROPN": "PROPN",
    "NOUN,NOUN": "NOUNS",
    "NOUNS,NOUN": "NOUNS",
    "ADJ,ADJ": "ADJ",
    "ADJ,NOUN": "NOUNS",
}
```

### `CFG_NOUN_PHRASE_GRAMMARS` (renamed from RU_NOUN_PHRASE_GRAMMARS)

```python
CFG_NOUN_PHRASE_GRAMMARS: dict[tuple[str, ...], str] = {
    ("ADJ", "NOUN"): "ADJ_NOUN",
    ("ADJ", "PROPN"): "ADJ_PROPN",
    ("ADV", "ADJ"): "ADV_ADJ",
    ("ADV", "ADJ", "NOUN"): "ADV_ADJ_NOUN",
    ("NOUN", "PREP"): "NOUN_PREP",
    ("NOUN", "PREP", "NOUN"): "NOUN_PREP_NOUN",
    ("PROPN", "NOUN"): "PROPN_NOUN",
    ("NUM", "NOUN"): "NUM_NOUN",
    ("NOUN", "ADJ"): "NOUN_ADJ",
    ("DET", "NOUN"): "DET_NOUN",
    ("DET", "ADJ", "NOUN"): "DET_ADJ_NOUN",
}
```

**Note**: Grammar key format change — `EN_NOUN_PHRASE_GRAMMARS` uses `str` keys (comma-separated), `CFG_NOUN_PHRASE_GRAMMARS` uses `tuple` keys. Factory must normalize before passing to `CFGNounPhraseExtractor`.

## Stop Words

### `EN_STOP_WORDS` (existing, unchanged)
```python
EN_STOP_WORDS = ["stuff", "thing", "things", "bunch", "bit", "bits", "people", "person", "okay", "hey", "hi", "hello", "laughter", "oh"]
```

### `RU_STOP_WORDS` (existing, unchanged — newly integrated)
```python
RU_STOP_WORDS = frozenset({
    "И", "ИЛИ", "НО", "А", "В", "НА", "К", "ПО", "ОТ", "ДО", "С", "У",
    "ДЛЯ", "ЧТО", "КОТОРЫЙ", "ЭТОТ", "ЭТА", "ЭТО", "ЭТИ", "ТАКОЙ", "ТАК",
    "НЕ", "ТЕ", "МЫ", "ВЫ", "ОНИ", "ОН", "ОНА", "ЗДЕСЬ", "ТАМ", "ВСЕ",
    "ВСЯКИЙ", "КАЖДЫЙ", "МОЙ", "ТВОЙ", "СВОЙ", "ВАШ", "Наш",
    "ЭТОГО", "ЭТОЙ", "ЭТИХ", "ТАКОГО", "КОМУ", "КОГО", "КЕМ", "ЧЕМ",
    "ОКОЛО", "КРОМЕ", "БЕЗ", "ПОД", "ПЕРЕ", "ПРЕД", "ЗА", "ОБ", "РОЗ",
    "СРЕДИ",
})
```

## Dependency Graph

```
TextAnalyzerConfig (extract_graph_nlp_config.py)
    └── language: str | None  [NEW]

NounPhraseExtractorFactory (factory.py)
    ├── imports: EN_STOP_WORDS, RU_STOP_WORDS [NEW: RU]
    ├── imports: CFG_NOUN_PHRASE_GRAMMARS [NEW: extracted from cfg_extractor.py]
    ├── imports: EN_NOUN_PHRASE_GRAMMARS [NEW: extracted from cfg_extractor.py]
    ├── get_np_extractor(config) → uses config.language
    │   ├── SyntacticNounPhraseExtractor: language → stop words
    │   ├── CFGNounPhraseExtractor: language → grammars + stop words
    │   └── RegexENNounPhraseExtractor: language → stop words
    └── LANGUAGE_MODEL_MAP [NEW: optional auto model selection]

cfg_extractor.py
    ├── EN_NOUN_PHRASE_GRAMMARS [NEW: extracted from defaults.py]
    └── CFG_NOUN_PHRASE_GRAMMARS [RENAMED from RU_NOUN_PHRASE_GRAMMARS]

defaults.py
    └── TextAnalyzerDefaults.noun_phrase_grammars → from cfg_extractor.EN_NOUN_PHRASE_GRAMMARS [CHANGED]
```
