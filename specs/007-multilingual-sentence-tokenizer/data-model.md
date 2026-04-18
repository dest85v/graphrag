# Data Model: NLTK Multilingual Sentence Tokenizer

## Entities

### ChunkingConfig

**Location**: `packages/graphrag-chunking/graphrag_chunking/chunking_config.py`

**Purpose**: Pydantic model holding chunking pipeline configuration.

**Fields**:

| Field | Type | Default | Description |
|---|---|---|---|
| `type` | `str` | `ChunkerType.Tokens` | Chunking strategy (tokens, sentence, etc.) |
| `encoding_model` | `str \| None` | `None` | Token encoding model name |
| `size` | `int` | `1200` | Target chunk size |
| `overlap` | `int` | `100` | Chunk overlap in tokens |
| `prepend_metadata` | `list[str] \| None` | `None` | Metadata fields to prepend |
| **`nltk_language`** | **`str`** | **`"english"`** | **[NEW]** NLTK Punkt language model to use for sentence tokenization. Supported values: `english`, `russian`, `german`, `french`, `spanish`, etc. |

**Validation**: No custom validators. Field accepts any string; invalid languages fail at runtime with NLTK's `LookupError`.

**Relationships**: Used by `GraphRagConfig.chunking` field in `graphrag` package. Passed to `create_chunker()` factory.

---

### SentenceChunker

**Location**: `packages/graphrag-chunking/graphrag_chunking/sentence_chunker.py`

**Purpose**: Chunker implementation that splits text into sentence-based chunks using NLTK PUNKT.

**Instance Attributes**:

| Attribute | Type | Default | Description |
|---|---|---|---|
| `_encode` | `Callable[[str], list[int]] \| None` | `None` | Token encoding function |
| **`_nltk_language`** | **`str`** | **`"english"`** | **[NEW]** NLTK Punkt language for `sent_tokenize()` |

**Methods**:

| Method | Signature | Description |
|---|---|---|
| `__init__` | `(encode, nltk_language="english", **kwargs)` | **[MODIFIED]** Accepts `nltk_language` parameter |
| `chunk` | `(text, transform=None)` | **[MODIFIED]** Calls `nltk.sent_tokenize(text, language=self._nltk_language)` |

**State**: Stateless after initialization. Bootstrap called once in `__init__`.

---

### ChunkingDefaults

**Location**: `packages/graphrag/graphrag/config/defaults.py`

**Purpose**: Dataclass with default chunking values for GraphRagConfig initialization.

**Fields** (existing → new):

| Field | Type | Default |
|---|---|---|
| `type` | `str` | `ChunkerType.Tokens` |
| `size` | `int` | `1200` |
| `overlap` | `int` | `100` |
| `encoding_model` | `str` | `o200k_base` |
| `prepend_metadata` | `None` | `None` |
| **`nltk_language`** | **`str`** | **`"english"`** | **[NEW]** |

---

## Relationship Diagram

```
GraphRagConfig
    └── chunking: ChunkingConfig          (from graphrag-chunking)
            ├── type: str
            ├── size: int
            ├── overlap: int
            ├── encoding_model: str | None
            ├── prepend_metadata: list[str] | None
            └── nltk_language: str  ← [NEW]

ChunkingDefaults ──default──> ChunkingConfig  (populates defaults)

create_chunker(config) ──passes──> SentenceChunker.__init__(**config_model)
                                                        └── nltk_language → _nltk_language
                                                                                   └── nltk.sent_tokenize(language=...)
```

## State Transitions

Not applicable — this is a configuration field, not a state machine.

## Validation Rules

| Rule | Enforcement |
|---|---|
| `nltk_language` defaults to `"english"` | `ChunkingDefaults`, `ChunkingConfig` field default |
| Empty string `""` → treated as `"english"` by NLTK (or custom guard) | Optional: add default in `SentenceChunker.__init__` |
| Invalid language string → NLTK `LookupError` at runtime | No pre-validation (per FR-009) |
| Field is optional (backward compat) | `extra="allow"` on `ChunkingConfig` + explicit field default |
