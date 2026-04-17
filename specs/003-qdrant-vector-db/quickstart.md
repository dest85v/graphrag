# Quickstart: Qdrant Vector Store

## Prerequisites

- A running Qdrant instance (local Docker or Qdrant Cloud)
- GraphRAG installed with the `qdrant` optional dependency

## Installation

```bash
# Install GraphRAG with Qdrant support
uv pip install "graphrag-vectors[qdrant]"
# or in the monorepo:
uv sync --extra qdrant
```

## Local Qdrant (Development)

Start a local Qdrant instance with Docker:

```bash
docker run -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage:z \
  qdrant/qdrant:latest
```

## Qdrant Cloud (Production)

1. Create an instance at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Copy the cloud URL and API key from the dashboard

## Configuration

Add Qdrant to your GraphRAG configuration YAML:

### Local Qdrant

```yaml
vector_store:
  type: qdrant
  url: http://localhost:6333
  # distance: cosine        # optional, default
  # hnsw_m: 16              # optional, default
  # hnsw_ef_construct: 100  # optional, default
```

### Qdrant Cloud

```yaml
vector_store:
  type: qdrant
  url: https://your-instance.us-east.aws.cloud.qdrant.io:6333
  api_key: your-api-key-here
```

### With Custom HNSW Parameters

```yaml
vector_store:
  type: qdrant
  url: http://localhost:6333
  distance: dot
  hnsw_m: 32
  hnsw_ef_construct: 256
  hnsw_ef: 512
```

### With Custom Collection Name

```yaml
vector_store:
  type: qdrant
  url: http://localhost:6333
  # index_name is set per-table via IndexSchema
```

## Running GraphRAG

After configuration, run GraphRAG normally — the vector store is selected automatically:

```bash
# Index documents
uv run graphrag index --root ./my-project

# Query
uv run graphrag query --method local --query "What does the document say about AI?"
```

## Verification

To verify Qdrant is working, check the Qdrant dashboard:

```bash
# Local dashboard
open http://localhost:6333/dashboard
```

Or via API:

```bash
# Check collection exists
curl http://localhost:6333/collections

# Check point count
curl http://localhost:6333/collections/your_collection_name/points/counts
```

## Migration from LanceDB

To switch from LanceDB to Qdrant:

1. Stop your GraphRAG indexing pipeline
2. Change `vector_store.type` from `lancedb` to `qdrant`
3. Add `url` (and optionally `api_key`)
4. Re-run indexing (Qdrant collection is created fresh)

```yaml
# Before
vector_store:
  type: lancedb
  db_uri: ./lancedb

# After
vector_store:
  type: qdrant
  url: http://localhost:6333
```

No code changes required — the `VectorStore` interface is identical across all backends.

## Troubleshooting

### Connection Refused

Ensure Qdrant is running and the URL is correct:

```bash
# Test connectivity
curl http://localhost:6333/healthz
```

### Dimension Mismatch

If your embedding model produces vectors of a different size than configured, update `vector_store.vector_size` or the `vector_size` in your `index_schema`:

```yaml
vector_store:
  type: qdrant
  url: http://localhost:6333
  vector_size: 1536  # matches your embedding model
```

### Index Name Conflicts

Qdrant collections are recreated on each index run. If you need to preserve data across runs, use different `index_name` values per index (configured via `IndexSchema`).
