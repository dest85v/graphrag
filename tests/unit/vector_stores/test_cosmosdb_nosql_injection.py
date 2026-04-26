# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for NoSQL injection defense in CosmosDBVectorStore."""

import unittest
from unittest.mock import MagicMock, patch

from azure.cosmos import CosmosClient
from graphrag_vectors.cosmosdb import CosmosDBVectorStore
from graphrag_vectors.filtering import AndExpr, Condition, Operator


class TestCosmosDBVectorStoreNoSQLInjection(unittest.IsolatedAsyncioTestCase):
    """Test cases for NoSQL injection defense in CosmosDBVectorStore."""

    def _create_mock_store(self):
        """Create a mocked CosmosDBVectorStore instance."""
        with patch.object(CosmosClient, "from_connection_string"):
            store = CosmosDBVectorStore(
                database_name="test_db",
                connection_string="Endpoint=https://test.cosmos.azure.com;AccountKey=dGVzdA==;",
                index_name="test_index",
                vector_size=128,
                id_field="id",
                vector_field="vector",
                fields={"metadata": str},
            )
            store._cosmos_client = MagicMock()
            mock_db = MagicMock()
            store._cosmos_client.get_database_client.return_value = mock_db

            mock_container = MagicMock()
            mock_db.get_container_client.return_value = mock_container
            store._container_client = mock_container
            store._database_client = mock_db

            return store, mock_container

    def test_compile_condition_with_normal_value(self):
        """Normal condition value should compile correctly."""
        store, _ = self._create_mock_store()
        cond = Condition(field="name", operator=Operator.eq, value="Alice")
        result = store._compile_condition(cond)
        self.assertEqual(result, "c.name = 'Alice'")

    def test_compile_condition_with_injection_in_value(self):
        """SQL injection in condition value should be escaped."""
        store, _ = self._create_mock_store()
        cond = Condition(field="name", operator=Operator.eq, value="'; DROP TABLE c --")
        result = store._compile_condition(cond)
        # The injected single quote should be doubled
        self.assertIn("''; DROP TABLE c --", result)

    def test_compile_condition_with_injection_in_contains(self):
        """SQL injection in CONTAINS operator should be escaped."""
        store, _ = self._create_mock_store()
        cond = Condition(
            field="title", operator=Operator.contains, value="'; DELETE FROM c --"
        )
        result = store._compile_condition(cond)
        self.assertIn("''; DELETE FROM c --", result)

    def test_compile_condition_with_injection_in_startswith(self):
        """SQL injection in STARTSWITH operator should be escaped."""
        store, _ = self._create_mock_store()
        cond = Condition(
            field="name", operator=Operator.startswith, value="admin'; DROP DATABASE --"
        )
        result = store._compile_condition(cond)
        self.assertIn("admin''; DROP DATABASE --", result)

    def test_compile_condition_with_injection_in_endswith(self):
        """SQL injection in ENDSWITH operator should be escaped."""
        store, _ = self._create_mock_store()
        cond = Condition(
            field="name", operator=Operator.endswith, value="'; DROP TABLE users --"
        )
        result = store._compile_condition(cond)
        self.assertIn("''; DROP TABLE users --", result)

    def test_compile_condition_with_injection_in_in_operator(self):
        """SQL injection in IN operator should be escaped."""
        store, _ = self._create_mock_store()
        cond = Condition(
            field="status",
            operator=Operator.in_,
            value=["active", "'; DROP TABLE c --"],
        )
        result = store._compile_condition(cond)
        self.assertIn("''; DROP TABLE c --", result)

    def test_compile_condition_with_injection_in_not_in_operator(self):
        """SQL injection in NOT IN operator should be escaped."""
        store, _ = self._create_mock_store()
        cond = Condition(
            field="status",
            operator=Operator.not_in,
            value=["deleted", "'; DELETE FROM c --"],
        )
        result = store._compile_condition(cond)
        self.assertIn("''; DELETE FROM c --", result)

    def test_compile_condition_with_backslash_in_value(self):
        """Backslash in condition value should be doubled."""
        store, _ = self._create_mock_store()
        cond = Condition(
            field="path", operator=Operator.eq, value="C:\\; DROP DATABASE"
        )
        result = store._compile_condition(cond)
        self.assertIn("C:\\\\; DROP DATABASE", result)

    def test_compile_condition_with_double_quote_in_value(self):
        """Double quote in condition value should be escaped."""
        store, _ = self._create_mock_store()
        cond = Condition(
            field="name", operator=Operator.eq, value='say "hello"; DROP TABLE'
        )
        result = store._compile_condition(cond)
        self.assertIn('say \\"hello\\"; DROP TABLE', result)

    def test_compile_filter_with_nested_injection(self):
        """SQL injection nested in AND expression should be escaped."""
        store, _ = self._create_mock_store()
        cond1 = Condition(field="name", operator=Operator.eq, value="test")
        cond2 = Condition(
            field="role", operator=Operator.eq, value="'; DROP TABLE c --"
        )
        filter_expr = AndExpr(and_=[cond1, cond2])
        result = store._compile_filter(filter_expr)
        self.assertIn("''; DROP TABLE c --", result)

    def test_compile_condition_eq_operator(self):
        """SQL injection with eq operator should be sanitized."""
        store, _ = self._create_mock_store()
        cond = Condition(field="id", operator=Operator.eq, value="1 OR 1=1 --")
        result = store._compile_condition(cond)
        # String values should have quotes added and escaped
        self.assertIn("'1 OR 1=1 --'", result)

    def test_compile_condition_ne_operator(self):
        """SQL injection with ne operator should be sanitized."""
        store, _ = self._create_mock_store()
        cond = Condition(
            field="status", operator=Operator.ne, value="'; DROP TABLE c --"
        )
        result = store._compile_condition(cond)
        self.assertIn("''; DROP TABLE c --", result)

    def test_compile_condition_gt_operator(self):
        """Numeric comparison should not break with injection attempt."""
        store, _ = self._create_mock_store()
        cond = Condition(field="count", operator=Operator.gt, value=5)
        result = store._compile_condition(cond)
        self.assertEqual(result, "c.count > 5")

    def test_compile_condition_numeric_injection(self):
        """String injection in numeric operator should be sanitized."""
        store, _ = self._create_mock_store()
        cond = Condition(
            field="count", operator=Operator.gt, value="5'; DROP TABLE c --"
        )
        result = store._compile_condition(cond)
        self.assertIn("5''; DROP TABLE c --", result)
