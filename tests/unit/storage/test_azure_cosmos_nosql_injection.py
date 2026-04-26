# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for NoSQL injection defense in AzureCosmosStorage."""

import re
import unittest
from unittest.mock import MagicMock, patch

from graphrag_storage.azure_cosmos_storage import AzureCosmosStorage


class TestAzureCosmosStorageNoSQLInjection(unittest.IsolatedAsyncioTestCase):
    """Test cases for NoSQL injection defense in AzureCosmosStorage operations."""

    def _create_mock_storage(self):
        """Create a mocked AzureCosmosStorage instance."""
        with (
            patch(
                "graphrag_storage.azure_cosmos_storage.CosmosClient"
            ) as MockCosmosClient,
            patch("graphrag_storage.azure_cosmos_storage.PartitionKey"),
        ):
            mock_client = MagicMock()
            MockCosmosClient.from_connection_string.return_value = mock_client

            mock_db = MagicMock()
            mock_client.create_database_if_not_exists.return_value = mock_db

            mock_container = MagicMock()
            mock_db.create_container_if_not_exists.return_value = mock_container

            storage = AzureCosmosStorage(
                database_name="test_db",
                container_name="test_container",
                connection_string="Endpoint=https://test.cosmos.azure.com;AccountKey=dGVzdA==;",
            )
            storage._cosmos_client = mock_client
            storage._database_client = mock_db
            storage._container_client = mock_container

            return storage, mock_container

    async def test_get_with_normal_key_works(self):
        """Normal key retrieval should work without sanitization changes."""
        storage, mock_container = self._create_mock_storage()
        mock_container.query_items.return_value.by_page.return_value = [
            [{"id": "entities:1", "body": {"name": "test"}}],
        ]

        await storage.get("entities/test.parquet", as_bytes=True)
        mock_container.query_items.assert_called()

    async def test_get_with_injection_in_key_is_sanitized(self):
        """Key with SQL injection should be sanitized — apostrophe doubled."""
        storage, mock_container = self._create_mock_storage()
        mock_container.query_items.return_value.by_page.return_value = []

        malicious_key = "entities/test'; DROP DATABASE --.parquet"
        await storage.get(malicious_key, as_bytes=True)

        call_args = mock_container.query_items.call_args
        self.assertIsNotNone(call_args)
        executed_query = call_args.kwargs["query"]
        # The sanitized form should have doubled apostrophe: entities/test'';
        self.assertIn("entities/test''; DROP DATABASE --:", executed_query)

    async def test_has_with_injection_in_key_is_sanitized(self):
        """has() with SQL injection in key should be sanitized."""
        storage, mock_container = self._create_mock_storage()
        mock_container.query_items.return_value.__iter__ = lambda self: iter([1])

        malicious_key = "entities'; DELETE FROM c --"
        await storage.has(malicious_key)

        call_args = mock_container.query_items.call_args
        self.assertIsNotNone(call_args)
        executed_query = call_args.kwargs["query"]
        # The sanitized form should have doubled apostrophe
        self.assertIn("entities''; DELETE FROM c --", executed_query)

    async def test_has_with_non_parquet_key_injection(self):
        """has() with injection in non-parquet key should be sanitized."""
        storage, mock_container = self._create_mock_storage()
        mock_container.query_items.return_value.__iter__ = lambda self: iter([1])

        malicious_key = "normal_key'; DROP TABLE c --"
        await storage.has(malicious_key)

        call_args = mock_container.query_items.call_args
        self.assertIsNotNone(call_args)
        executed_query = call_args.kwargs["query"]
        # The sanitized form should have doubled apostrophe
        self.assertIn("normal_key''; DROP TABLE c --", executed_query)

    async def test_delete_with_injection_in_key_is_sanitized(self):
        """delete() with SQL injection in key should be sanitized."""
        storage, mock_container = self._create_mock_storage()
        mock_container.query_items.return_value.by_page.return_value = []
        mock_container.delete_item.return_value = None

        malicious_key = "entities/test'; DELETE FROM c --.parquet"
        await storage.delete(malicious_key)

        call_args = mock_container.query_items.call_args
        self.assertIsNotNone(call_args)
        executed_query = call_args.kwargs["query"]
        # The sanitized form should have doubled apostrophe
        self.assertIn("entities/test''; DELETE FROM c --:", executed_query)

    def test_find_with_injection_pattern_is_safe(self):
        """find() uses parameterized query with RegexMatch - should remain parameterized."""
        storage, mock_container = self._create_mock_storage()
        mock_container.query_items.return_value.by_page.return_value = []

        malicious_pattern = re.compile(r"test'; DROP DATABASE --")
        list(storage.find(malicious_pattern))

        call_args = mock_container.query_items.call_args
        self.assertIsNotNone(call_args)
        executed_query = call_args.kwargs["query"]
        self.assertEqual(
            executed_query, "SELECT * FROM c WHERE RegexMatch(c.id, @pattern)"
        )
        params = call_args.kwargs.get("parameters", [])
        self.assertGreater(len(params), 0)
        self.assertEqual(params[0]["name"], "@pattern")

    async def test_get_with_backslash_injection_sanitized(self):
        """Key with backslash should have it doubled."""
        storage, mock_container = self._create_mock_storage()
        mock_container.query_items.return_value.by_page.return_value = []

        malicious_key = "entities/test\\; DELETE c --.parquet"
        await storage.get(malicious_key, as_bytes=True)

        call_args = mock_container.query_items.call_args
        self.assertIsNotNone(call_args)
        executed_query = call_args.kwargs["query"]
        # Single backslash before semicolon should be doubled
        self.assertIn("test\\\\; DELETE", executed_query)

    async def test_delete_with_double_quote_injection_sanitized(self):
        """delete() with double quote injection should be escaped."""
        storage, mock_container = self._create_mock_storage()
        mock_container.query_items.return_value.by_page.return_value = []
        mock_container.delete_item.return_value = None

        malicious_key = 'entities/test"; DELETE FROM c --.parquet'
        await storage.delete(malicious_key)

        call_args = mock_container.query_items.call_args
        self.assertIsNotNone(call_args)
        executed_query = call_args.kwargs["query"]
        # The double quote should be escaped with backslash
        self.assertIn('test\\"; DELETE FROM c --:', executed_query)
