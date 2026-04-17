# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for vector store type enum."""

from graphrag_vectors.vector_store_type import VectorStoreType


class TestVectorStoreType:
    """Test class for VectorStoreType enum."""

    def test_lancedb_value(self):
        """Test LanceDB enum value."""
        assert VectorStoreType.LanceDB == "lancedb"
        assert VectorStoreType.LanceDB.value == "lancedb"

    def test_azure_ai_search_value(self):
        """Test Azure AI Search enum value."""
        assert VectorStoreType.AzureAISearch == "azure_ai_search"
        assert VectorStoreType.AzureAISearch.value == "azure_ai_search"

    def test_cosmosdb_value(self):
        """Test CosmosDB enum value."""
        assert VectorStoreType.CosmosDB == "cosmosdb"
        assert VectorStoreType.CosmosDB.value == "cosmosdb"

    def test_qdrant_value(self):
        """Test Qdrant enum value."""
        assert VectorStoreType.Qdrant == "qdrant"
        assert VectorStoreType.Qdrant.value == "qdrant"

    def test_qdrant_discoverable(self):
        """Test Qdrant is discoverable in all types list."""
        types = list(VectorStoreType)
        assert VectorStoreType.Qdrant in types
        type_values = [t.value for t in VectorStoreType]
        assert "qdrant" in type_values

    def test_all_types_count(self):
        """Test all expected types are present."""
        types = list(VectorStoreType)
        assert len(types) == 4
        assert VectorStoreType.LanceDB in types
        assert VectorStoreType.AzureAISearch in types
        assert VectorStoreType.CosmosDB in types
        assert VectorStoreType.Qdrant in types
