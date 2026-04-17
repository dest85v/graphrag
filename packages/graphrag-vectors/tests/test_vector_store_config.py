# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for VectorStoreConfig model."""

from graphrag_vectors.index_schema import IndexSchema
from graphrag_vectors.vector_store_config import VectorStoreConfig
from graphrag_vectors.vector_store_type import VectorStoreType


class TestVectorStoreConfig:
    """Test class for VectorStoreConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = VectorStoreConfig()
        assert config.type == VectorStoreType.LanceDB
        assert config.db_uri is None
        assert config.url is None
        assert config.api_key is None
        assert config.vector_size == 3072
        assert config.index_schema == {}

    def test_qdrant_distance_field(self):
        """Test Qdrant distance field is accepted and passed through."""
        config = VectorStoreConfig(
            type=VectorStoreType.Qdrant,
            url="http://localhost:6333",
            distance="cosine",
        )
        assert config.distance == "cosine"
        dumped = config.model_dump()
        assert dumped["distance"] == "cosine"

    def test_qdrant_hnsw_m_field(self):
        """Test Qdrant hnsw_m field is accepted and passed through."""
        config = VectorStoreConfig(
            type=VectorStoreType.Qdrant,
            url="http://localhost:6333",
            hnsw_m=32,
        )
        assert config.hnsw_m == 32
        dumped = config.model_dump()
        assert dumped["hnsw_m"] == 32

    def test_qdrant_hnsw_ef_construct_field(self):
        """Test Qdrant hnsw_ef_construct field is accepted and passed through."""
        config = VectorStoreConfig(
            type=VectorStoreType.Qdrant,
            url="http://localhost:6333",
            hnsw_ef_construct=256,
        )
        assert config.hnsw_ef_construct == 256
        dumped = config.model_dump()
        assert dumped["hnsw_ef_construct"] == 256

    def test_qdrant_hnsw_ef_field(self):
        """Test Qdrant hnsw_ef field is accepted and passed through."""
        config = VectorStoreConfig(
            type=VectorStoreType.Qdrant,
            url="http://localhost:6333",
            hnsw_ef=512,
        )
        assert config.hnsw_ef == 512
        dumped = config.model_dump()
        assert dumped["hnsw_ef"] == 512

    def test_qdrant_all_hnsw_fields(self):
        """Test all Qdrant HNSW fields together."""
        config = VectorStoreConfig(
            type=VectorStoreType.Qdrant,
            url="http://localhost:6333",
            api_key="test-key",
            distance="dot",
            hnsw_m=32,
            hnsw_ef_construct=256,
            hnsw_ef=512,
            vector_size=1536,
        )
        assert config.type == VectorStoreType.Qdrant
        assert config.url == "http://localhost:6333"
        assert config.api_key == "test-key"
        assert config.distance == "dot"
        assert config.hnsw_m == 32
        assert config.hnsw_ef_construct == 256
        assert config.hnsw_ef == 512
        assert config.vector_size == 1536

        dumped = config.model_dump()
        assert dumped["distance"] == "dot"
        assert dumped["hnsw_m"] == 32
        assert dumped["hnsw_ef_construct"] == 256
        assert dumped["hnsw_ef"] == 512

    def test_extra_fields_still_allowed(self):
        """Test that extra='allow' still works for other custom fields."""
        config = VectorStoreConfig(custom_field="custom_value")
        assert config.model_dump()["custom_field"] == "custom_value"

    def test_index_schema_passthrough(self):
        """Test index schema is accepted and passed through."""
        schema = IndexSchema(
            index_name="test", vector_size=1536, fields={"label": "str"}
        )
        config = VectorStoreConfig(
            type=VectorStoreType.Qdrant,
            url="http://localhost:6333",
            index_schema={"entities": schema},
        )
        dumped = config.model_dump()
        assert "entities" in dumped["index_schema"]
