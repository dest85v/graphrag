# Data Model: Qdrant Vector Store

## Entities

### QdrantVectorStore

The Qdrant implementation of the `VectorStore` ABC. Manages connection to a Qdrant server, collection lifecycle, and all vector operations.

**Attributes** (inherited from `VectorStore`):
| Field | Type | Default | Description |
|---|---|---|---|
| `index_name` | `str` | `"vector_index"` | Qdrant collection name |
| `id_field` | `str` | `"id"` | Payload field storing document ID |
| `vector_field` | `str` | `"vector"` | Vector field name in Qdrant |
| `create_date_field` | `str` | `"create_date"` | Payload field for creation timestamp |
| `update_date_field` | `str` | `"update_date"` | Payload field for update timestamp |
| `vector_size` | `int` | `3072` | Vector dimensionality |
| `fields` | `dict[str, str]` | `{}` | Metadata field name → type mapping |
| `timestamp_exploder` | `Callable` | `explode_timestamp` | Timestamp field generator |

**Attributes** (Qdrant-specific, in `VectorStoreConfig`):
| Field | Type | Default | Description |
|---|---|---|---|
| `url` | `str \| None` | `None` | Qdrant server URL (`http://host:port`) or cloud URL |
| `api_key` | `str \| None` | `None` | Qdrant Cloud API key (required for cloud, optional for local) |
| `distance` | `str` | `"cosine"` | Similarity metric: `cosine`, `dot`, `euclidean`, `manhattan` |
| `hnsw_m` | `int \| None` | `None` | HNSW `m` parameter (edges per node); default: Qdrant default (16) |
| `hnsw_ef_construct` | `int \| None` | `None` | HNSW `ef_construct` parameter; default: Qdrant default (100) |
| `hnsw_ef` | `int \| None` | `None` | Search-time `ef` parameter; default: Qdrant default (unset = use index ef) |
| `db_uri` | `str \| None` | `None` | Local Qdrant path (`:memory:`, `./path`) — alias for `url` when starting with `:` or `/` |

**Internal state** (not serialized):
| Field | Type | Description |
|---|---|---|
| `_client` | `QdrantClient` | Connected Qdrant client instance |

### VectorStoreDocument (inherited)

The document model passed to `load_documents()`, `insert()`, `update()`. No changes.

| Field | Type | Description |
|---|---|---|
| `id` | `str \| int` | Document identifier → stored as Qdrant point ID |
| `vector` | `list[float] \| None` | Embedding vector → stored as Qdrant vector |
| `data` | `dict[str, Any]` | Metadata payload → stored as Qdrant payload |
| `create_date` | `str \| None` | ISO 8601 timestamp → exploded into `create_date_*` fields |
| `update_date` | `str \| None` | ISO 8601 timestamp → exploded into `update_date_*` fields |

### VectorStoreSearchResult (inherited)

The result model returned by `similarity_search_by_vector()`, `similarity_search_by_text()`, `search_by_id()`. No changes.

| Field | Type | Description |
|---|---|---|
| `document` | `VectorStoreDocument` | The matching document |
| `score` | `float` | Similarity score (0–1 for cosine, varies by metric) |

## Field Type Mapping

Python `fields` dict values map to Qdrant payload types:

| `fields` value | Qdrant payload type | Qdrant filter compatibility |
|---|---|---|
| `"str"` | `string` | `MatchValue`, `MatchText`, `MatchAny` |
| `"int"` | `integer` | `MatchValue`, `MatchInt`, `Range` |
| `"float"` | `float` | `MatchValue`, `Range` |
| `"bool"` | `boolean` | `MatchValue` |
| `"date"` | `string` (ISO 8601) | `MatchValue`, `DatetimeRange` |

## Relationship to Existing Vector Stores

```
VectorStore (ABC)
├── LanceDBVectorStore    → lancedb.py     (file-based, PyArrow)
├── AzureAISearchVectorStore → azure_ai_search.py (Azure cloud)
├── CosmosDBVectorStore   → cosmosdb.py    (Azure NoSQL)
└── QdrantVectorStore     → qdrant.py      (NEW: remote/local Qdrant)
```

All four implement the same `VectorStore` ABC with identical method signatures. The factory pattern (`VectorStoreFactory` + `create_vector_store()`) is shared. Filter compilation follows the same match-statement pattern per store type.

## Configuration Hierarchy

```
VectorStoreConfig (pydantic model)
├── type: VectorStoreType (LanceDB, AzureAISearch, CosmosDB, Qdrant)
├── db_uri: str | None    (LanceDB: file path; Qdrant: local path or URL)
├── url: str | None       (Azure AI Search: endpoint; Qdrant: server URL)
├── api_key: str | None   (Azure AI Search / Qdrant Cloud)
├── audience: str | None  (Azure AI Search only)
├── connection_string: str | None (CosmosDB only)
├── database_name: str | None (CosmosDB only)
├── vector_size: int
├── index_schema: dict[str, IndexSchema]
└── [extra fields for Qdrant]
    ├── distance: str
    ├── hnsw_m: int | None
    ├── hnsw_ef_construct: int | None
    └── hnsw_ef: int | None
```

Extra fields for Qdrant are allowed via `model_config = ConfigDict(extra="allow")` on `VectorStoreConfig`.
