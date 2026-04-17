# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Unit tests for QdrantVectorStore using in-memory Qdrant."""

import shutil
import tempfile
from unittest.mock import patch

import numpy as np
import pytest
from graphrag_vectors.filtering import F
from graphrag_vectors.qdrant import QdrantVectorStore
from graphrag_vectors.vector_store import VectorStoreDocument
from qdrant_client.http.models import Distance


class TestQdrantVectorStore:
    """Test class for QdrantVectorStore."""

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return [
            VectorStoreDocument(
                id="1",
                vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            ),
            VectorStoreDocument(
                id="2",
                vector=[0.2, 0.3, 0.4, 0.5, 0.6],
            ),
            VectorStoreDocument(
                id="3",
                vector=[0.3, 0.4, 0.5, 0.6, 0.7],
            ),
        ]

    @pytest.fixture
    def sample_documents_with_metadata(self):
        """Create sample documents with metadata fields for testing."""
        return [
            VectorStoreDocument(
                id="1",
                vector=[0.1, 0.2, 0.3, 0.4, 0.5],
                data={"os": "windows", "category": "bug", "priority": 1},
            ),
            VectorStoreDocument(
                id="2",
                vector=[0.2, 0.3, 0.4, 0.5, 0.6],
                data={"os": "linux", "category": "feature", "priority": 2},
            ),
            VectorStoreDocument(
                id="3",
                vector=[0.3, 0.4, 0.5, 0.6, 0.7],
                data={"os": "windows", "category": "feature", "priority": 3},
            ),
        ]

    @pytest.fixture
    def store_with_fields(self):
        """Create a Qdrant store with metadata fields configured."""
        temp_dir = tempfile.mkdtemp()
        store = QdrantVectorStore(
            db_uri=temp_dir,
            index_name="test_fields",
            vector_size=5,
            fields={"os": "str", "category": "str", "priority": "int"},
        )
        store.connect()
        store.create_index()
        yield store
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_connect_and_create_index(self):
        """Test connect and create_index with in-memory Qdrant."""
        store = QdrantVectorStore(
            db_uri=":memory:",
            index_name="test_index",
            vector_size=5,
        )
        store.connect()
        store.create_index()
        assert store._collection_exists is True  # noqa: SLF001

    def test_missing_url_raises_error(self):
        """Test that missing URL/db_uri raises ValueError."""
        with pytest.raises(ValueError, match="url or db_uri must be provided"):
            QdrantVectorStore()

    def test_empty_index_name_raises_error(self):
        """Test that empty index_name raises ValueError in create_index."""
        store = QdrantVectorStore(
            db_uri=":memory:",
            index_name="",
            vector_size=5,
        )
        store.connect()
        with pytest.raises(ValueError, match="index_name must be provided"):
            store.create_index()

    def test_load_and_search_documents(self, sample_documents):
        """Test basic load and search operations."""
        temp_dir = tempfile.mkdtemp()
        try:
            store = QdrantVectorStore(
                db_uri=temp_dir,
                index_name="test_collection",
                vector_size=5,
                distance="euclidean",
            )
            store.connect()
            store.create_index()
            store.load_documents(sample_documents[:2])

            doc = store.search_by_id("1")
            assert doc.id == "1"
            assert doc.vector is not None
            assert np.allclose(doc.vector, [0.1, 0.2, 0.3, 0.4, 0.5], atol=0.01)

            results = store.similarity_search_by_vector([0.1, 0.2, 0.3, 0.4, 0.5], k=2)
            assert 1 <= len(results) <= 2
            assert isinstance(results[0].score, float)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_empty_collection(self):
        """Test creating an empty collection."""
        temp_dir = tempfile.mkdtemp()
        try:
            store = QdrantVectorStore(
                db_uri=temp_dir,
                index_name="empty_collection",
                vector_size=5,
            )
            store.connect()
            store.create_index()
            assert store.count() == 0

            doc = VectorStoreDocument(
                id="1",
                vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            )
            store.insert(doc)
            assert store.count() == 1
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_insert_and_count(self, store_with_fields, sample_documents_with_metadata):
        """Test inserting documents and verifying count."""
        store = store_with_fields
        assert store.count() == 0
        for doc in sample_documents_with_metadata:
            store.insert(doc)
        assert store.count() == 3

    def test_load_documents(self, store_with_fields, sample_documents_with_metadata):
        """Test loading a batch via load_documents."""
        store = store_with_fields
        store.load_documents(sample_documents_with_metadata)
        assert store.count() == 3

    def test_search_by_id(self, store_with_fields, sample_documents_with_metadata):
        """Test searching for a document by id returns all fields."""
        store = store_with_fields
        store.load_documents(sample_documents_with_metadata)

        doc = store.search_by_id("1")
        assert doc.id == "1"
        assert doc.vector is not None
        assert doc.data["os"] == "windows"
        assert doc.data["category"] == "bug"
        assert doc.data["priority"] == 1

    def test_search_by_id_not_found(self):
        """Test search_by_id raises IndexError for missing document."""
        temp_dir = tempfile.mkdtemp()
        try:
            store = QdrantVectorStore(
                db_uri=temp_dir,
                index_name="test",
                vector_size=5,
            )
            store.connect()
            store.create_index()
            with pytest.raises(IndexError, match="not found"):
                store.search_by_id("nonexistent")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_remove(self, store_with_fields, sample_documents_with_metadata):
        """Test removing documents by id."""
        store = store_with_fields
        store.load_documents(sample_documents_with_metadata)
        assert store.count() == 3

        store.remove(["1", "2"])
        assert store.count() == 1

        with pytest.raises(IndexError):
            store.search_by_id("1")

        doc = store.search_by_id("3")
        assert doc.id == "3"

    def test_update(self, store_with_fields, sample_documents_with_metadata):
        """Test updating a document's metadata field."""
        store = store_with_fields
        store.load_documents(sample_documents_with_metadata)

        store.update(
            VectorStoreDocument(
                id="1",
                vector=None,
                data={"os": "macos", "category": "bug", "priority": 1},
            )
        )

        doc = store.search_by_id("1")
        assert doc.data["os"] == "macos"

    def test_similarity_search_by_vector(
        self, store_with_fields, sample_documents_with_metadata
    ):
        """Test vector similarity search returns ordered results."""
        store = store_with_fields
        store.load_documents(sample_documents_with_metadata)

        results = store.similarity_search_by_vector([0.1, 0.2, 0.3, 0.4, 0.5], k=3)
        assert len(results) == 3
        assert results[0].document.id == "1"
        assert results[0].score >= results[1].score

    def test_similarity_search_k_limit(
        self, store_with_fields, sample_documents_with_metadata
    ):
        """Test that k parameter limits search results."""
        store = store_with_fields
        store.load_documents(sample_documents_with_metadata)

        results = store.similarity_search_by_vector([0.1, 0.2, 0.3, 0.4, 0.5], k=1)
        assert len(results) == 1

    def test_select_limits_fields(
        self, store_with_fields, sample_documents_with_metadata
    ):
        """Test that select parameter limits returned fields."""
        store = store_with_fields
        store.load_documents(sample_documents_with_metadata)

        results = store.similarity_search_by_vector(
            [0.1, 0.2, 0.3, 0.4, 0.5], k=1, select=["os"]
        )
        data = results[0].document.data
        assert "os" in data
        assert "category" not in data
        assert "priority" not in data

    def test_include_vectors_false(
        self, store_with_fields, sample_documents_with_metadata
    ):
        """Test include_vectors=False omits vectors from results."""
        store = store_with_fields
        store.load_documents(sample_documents_with_metadata)

        results = store.similarity_search_by_vector(
            [0.1, 0.2, 0.3, 0.4, 0.5], k=1, include_vectors=False
        )
        assert results[0].document.vector is None

        doc = store.search_by_id("1", include_vectors=False)
        assert doc.vector is None

    def test_filter_eq(self, store_with_fields, sample_documents_with_metadata):
        """Test equality filter."""
        store = store_with_fields
        store.load_documents(sample_documents_with_metadata)

        results = store.similarity_search_by_vector(
            [0.1, 0.2, 0.3, 0.4, 0.5],
            k=10,
            filters=F.os == "linux",
        )
        assert len(results) == 1
        assert results[0].document.id == "2"

    def test_filter_ne(self, store_with_fields, sample_documents_with_metadata):
        """Test not-equal filter."""
        store = store_with_fields
        store.load_documents(sample_documents_with_metadata)

        results = store.similarity_search_by_vector(
            [0.1, 0.2, 0.3, 0.4, 0.5],
            k=10,
            filters=F.os != "linux",
        )
        assert len(results) == 2
        ids = {r.document.id for r in results}
        assert ids == {"1", "3"}

    def test_filter_gt_gte_lt_lte(
        self, store_with_fields, sample_documents_with_metadata
    ):
        """Test numeric range filters."""
        store = store_with_fields
        store.load_documents(sample_documents_with_metadata)

        results = store.similarity_search_by_vector(
            [0.1, 0.2, 0.3, 0.4, 0.5], k=10, filters=F.priority > 1
        )
        assert len(results) == 2

        results = store.similarity_search_by_vector(
            [0.1, 0.2, 0.3, 0.4, 0.5], k=10, filters=F.priority >= 2
        )
        assert len(results) == 2

        results = store.similarity_search_by_vector(
            [0.1, 0.2, 0.3, 0.4, 0.5], k=10, filters=F.priority < 3
        )
        assert len(results) == 2

        results = store.similarity_search_by_vector(
            [0.1, 0.2, 0.3, 0.4, 0.5], k=10, filters=F.priority <= 1
        )
        assert len(results) == 1

    def test_filter_and(self, store_with_fields, sample_documents_with_metadata):
        """Test compound AND filter."""
        store = store_with_fields
        store.load_documents(sample_documents_with_metadata)

        results = store.similarity_search_by_vector(
            [0.1, 0.2, 0.3, 0.4, 0.5],
            k=10,
            filters=(F.os == "windows") & (F.category == "feature"),
        )
        assert len(results) == 1
        assert results[0].document.id == "3"

    def test_filter_or(self, store_with_fields, sample_documents_with_metadata):
        """Test compound OR filter."""
        store = store_with_fields
        store.load_documents(sample_documents_with_metadata)

        results = store.similarity_search_by_vector(
            [0.1, 0.2, 0.3, 0.4, 0.5],
            k=10,
            filters=(F.os == "linux") | (F.category == "bug"),
        )
        assert len(results) == 2
        ids = {r.document.id for r in results}
        assert ids == {"1", "2"}

    def test_filter_not(self, store_with_fields, sample_documents_with_metadata):
        """Test negated filter."""
        store = store_with_fields
        store.load_documents(sample_documents_with_metadata)

        results = store.similarity_search_by_vector(
            [0.1, 0.2, 0.3, 0.4, 0.5],
            k=10,
            filters=~(F.os == "windows"),
        )
        assert len(results) == 1
        assert results[0].document.id == "2"

    def test_filter_in(self, store_with_fields, sample_documents_with_metadata):
        """Test IN filter."""
        store = store_with_fields
        store.load_documents(sample_documents_with_metadata)

        results = store.similarity_search_by_vector(
            [0.1, 0.2, 0.3, 0.4, 0.5],
            k=10,
            filters=F.os.in_(["windows", "macos"]),
        )
        assert len(results) == 2
        ids = {r.document.id for r in results}
        assert ids == {"1", "3"}

    def test_batch_upload_1000_docs(self):
        """Test batch upload with 1000+ documents."""
        temp_dir = tempfile.mkdtemp()
        try:
            store = QdrantVectorStore(
                db_uri=temp_dir,
                index_name="large_batch",
                vector_size=10,
            )
            store.connect()
            store.create_index()

            docs = [
                VectorStoreDocument(
                    id=str(i),
                    vector=[float(i + j * 0.1) for j in range(10)],
                )
                for i in range(1050)
            ]
            store.load_documents(docs)
            assert store.count() == 1050
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_skip_none_vectors(self):
        """Test documents with None vectors are skipped."""
        temp_dir = tempfile.mkdtemp()
        try:
            store = QdrantVectorStore(
                db_uri=temp_dir,
                index_name="test",
                vector_size=5,
            )
            store.connect()
            store.create_index()

            docs = [
                VectorStoreDocument(id="1", vector=[0.1, 0.2, 0.3, 0.4, 0.5]),
                VectorStoreDocument(id="2", vector=None),
                VectorStoreDocument(id="3", vector=[0.3, 0.4, 0.5, 0.6, 0.7]),
            ]
            store.load_documents(docs)
            assert store.count() == 2
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_custom_hnsw_params(self):
        """Test custom HNSW parameters are passed to create_collection."""
        temp_dir = tempfile.mkdtemp()
        try:
            store = QdrantVectorStore(
                db_uri=temp_dir,
                index_name="test_hnsw",
                vector_size=5,
                hnsw_m=32,
                hnsw_ef_construct=256,
            )
            store.connect()

            with patch.object(store._client, "create_collection") as mock_create:  # noqa: SLF001
                store.create_index()
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["vectors_config"].size == 5
                assert isinstance(call_kwargs["hnsw_config"], dict)
                assert call_kwargs["hnsw_config"]["m"] == 32
                assert call_kwargs["hnsw_config"]["ef_construct"] == 256
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_custom_distance(self):
        """Test custom distance metric is applied."""
        temp_dir = tempfile.mkdtemp()
        try:
            store = QdrantVectorStore(
                db_uri=temp_dir,
                index_name="test_distance",
                vector_size=5,
                distance="dot",
            )
            store.connect()

            with patch.object(store._client, "create_collection") as mock_create:  # noqa: SLF001
                store.create_index()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["vectors_config"].distance == Distance.DOT
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cloud_config_construction(self):
        """Test Qdrant Cloud config creates client with API key."""
        store = QdrantVectorStore(
            url="https://test.us-east.aws.cloud.qdrant.io:6333",
            api_key="test-api-key",
        )
        # Verify connection args are set correctly without actually connecting
        assert (
            store._connection_args["url"]  # noqa: SLF001
            == "https://test.us-east.aws.cloud.qdrant.io:6333"
        )
        assert store._connection_args["api_key"]  # noqa: SLF001 == "test-api-key"

    def test_text_similarity_search(self, sample_documents_with_metadata):
        """Test text-based similarity search via mock embedder."""
        temp_dir = tempfile.mkdtemp()
        try:
            store = QdrantVectorStore(
                db_uri=temp_dir,
                index_name="test_text",
                vector_size=5,
                fields={"category": "str"},
            )
            store.connect()
            store.create_index()
            store.load_documents(sample_documents_with_metadata)

            def mock_embedder(text: str) -> list[float]:
                return [0.1, 0.2, 0.3, 0.4, 0.5]

            results = store.similarity_search_by_text("test query", mock_embedder, k=2)
            assert len(results) == 2
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
