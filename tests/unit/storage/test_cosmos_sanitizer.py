# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for the Cosmos DB query sanitizer utility."""

from unittest.mock import patch

from graphrag_storage.cosmos_sanitizer import _sanitize_cosmos_key


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
        assert _sanitize_cosmos_key("it's a test") == "it''s a test"

    def test_backslash_escaped(self):
        """Backslashes are doubled for SQL string literal safety."""
        assert _sanitize_cosmos_key("path\\to\\file") == "path\\\\to\\\\file"
        assert _sanitize_cosmos_key("C:\\Users\\test") == "C:\\\\Users\\\\test"

    def test_double_quote_escaped(self):
        """Double quotes are escaped with backslash."""
        assert _sanitize_cosmos_key('say "hello"') == 'say \\"hello\\"'
        assert _sanitize_cosmos_key('file"name') == 'file\\"name'

    def test_nosql_injection_payload_neutralized(self):
        """Common NoSQL injection payload is fully escaped."""
        payload = "entities'; DROP DATABASE --"
        result = _sanitize_cosmos_key(payload)
        # Single quotes are doubled, so the injected ' cannot terminate the string
        assert result == "entities''; DROP DATABASE --"

    def test_complex_injection_payload(self):
        """Complex injection with multiple special characters is escaped."""
        payload = "x' OR 1=1 --"
        result = _sanitize_cosmos_key(payload)
        # Single quotes doubled — safe in SQL string literal
        assert result == "x'' OR 1=1 --"

    def test_backslash_injection_payload(self):
        """Payload using backslash for statement termination is escaped."""
        payload = "entities\\; DELETE FROM c --"
        result = _sanitize_cosmos_key(payload)
        # Both backslashes must be doubled
        assert result == "entities\\\\; DELETE FROM c --"

    def test_mixed_special_chars(self):
        """String with all three special characters is fully escaped."""
        payload = "file\\'name\"test"
        result = _sanitize_cosmos_key(payload)
        # Backslash doubled, apostrophe doubled, double-quote escaped
        assert result == "file\\\\''name\\\"test"

    def test_unicode_preserved(self):
        """Unicode characters are preserved unchanged."""
        assert _sanitize_cosmos_key("Привет мир") == "Привет мир"
        assert _sanitize_cosmos_key("こんにちは世界") == "こんにちは世界"
        assert _sanitize_cosmos_key("مرحبا بالعالم") == "مرحبا بالعالم"

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert _sanitize_cosmos_key("") == ""

    def test_only_special_chars(self):
        """String containing only special characters is fully escaped."""
        # Three single quotes → six single quotes (each doubled)
        assert _sanitize_cosmos_key("'''") == "''''''"
        # Three double quotes → three backslash-escaped double quotes
        assert _sanitize_cosmos_key('"""') == '\\"\\"\\"'
        # Three backslashes → six backslashes (each doubled)
        assert _sanitize_cosmos_key("\\\\\\") == "\\\\\\\\\\\\"

    def test_logging_on_escape_applied(self):
        """When escaping occurs, a WARNING is logged."""
        with patch("graphrag_storage.cosmos_sanitizer.logger") as mock_logger:
            _sanitize_cosmos_key("file's name")
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert "Cosmos DB query sanitization applied" in call_args[0][0]

    def test_no_logging_on_unchanged_string(self):
        """No WARNING is logged when no escaping is needed."""
        with patch("graphrag_storage.cosmos_sanitizer.logger") as mock_logger:
            _sanitize_cosmos_key("normal_string")
            mock_logger.warning.assert_not_called()
