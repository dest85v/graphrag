# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for the Cosmos DB query sanitizer utility."""

from unittest.mock import patch

from graphrag_vectors.cosmos_sanitizer import _sanitize_cosmos_key


class TestSanitizeCosmosKey:
    """Test cases for the _sanitize_cosmos_key sanitizer function."""

    def test_normal_string_unchanged(self):
        """Normal strings with only alphanumeric chars pass through unchanged."""
        assert _sanitize_cosmos_key("entities") == "entities"
        assert _sanitize_cosmos_key("my_file_name") == "my_file_name"
        assert _sanitize_cosmos_key("entities.parquet") == "entities.parquet"

    def test_apostrophe_escaped(self):
        """Single quotes are doubled for SQL string literal safety."""
        assert _sanitize_cosmos_key("file's name") == "file''s name"
        assert _sanitize_cosmos_key("O'Brien") == "O''Brien"

    def test_backslash_escaped(self):
        """Backslashes are doubled for SQL string literal safety."""
        assert _sanitize_cosmos_key("path\\to\\file") == "path\\\\to\\\\file"

    def test_double_quote_escaped(self):
        """Double quotes are escaped with backslash."""
        assert _sanitize_cosmos_key('say "hello"') == 'say \\"hello\\"'

    def test_nosql_injection_payload_neutralized(self):
        """Common NoSQL injection payload is fully escaped."""
        payload = "entities'; DROP DATABASE --"
        result = _sanitize_cosmos_key(payload)
        assert result == "entities''; DROP DATABASE --"

    def test_complex_injection_payload(self):
        """Complex injection with multiple special characters is escaped."""
        payload = "x' OR 1=1 --"
        result = _sanitize_cosmos_key(payload)
        assert result == "x'' OR 1=1 --"

    def test_unicode_preserved(self):
        """Unicode characters are preserved unchanged."""
        assert _sanitize_cosmos_key("Привет мир") == "Привет мир"
        assert _sanitize_cosmos_key("こんにちは世界") == "こんにちは世界"

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert _sanitize_cosmos_key("") == ""

    def test_logging_on_escape_applied(self):
        """When escaping occurs, a WARNING is logged."""
        with patch("graphrag_vectors.cosmos_sanitizer.logger") as mock_logger:
            _sanitize_cosmos_key("file's name")
            mock_logger.warning.assert_called_once()

    def test_no_logging_on_unchanged_string(self):
        """No WARNING is logged when no escaping is needed."""
        with patch("graphrag_vectors.cosmos_sanitizer.logger") as mock_logger:
            _sanitize_cosmos_key("normal_string")
            mock_logger.warning.assert_not_called()
