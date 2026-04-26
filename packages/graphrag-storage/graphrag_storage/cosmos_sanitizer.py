# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Cosmos DB query string sanitizer.

Provides a utility to escape special characters in string values
that will be interpolated into Azure Cosmos DB SQL API query strings.
This prevents NoSQL injection attacks where user-supplied values
contain SQL metacharacters.
"""

import logging

logger = logging.getLogger(__name__)


def _sanitize_cosmos_key(key: str) -> str:
    r"""Escape special characters in a string value for safe Cosmos DB SQL interpolation.

    Escapes the following characters:
    - Single quote (') → double single quote ('') for SQL string literal safety
    - Backslash (\\) → double backslash (\\\\) for escape sequence safety
    - Double quote (\") → backslash-escaped (\\\\\") for field reference safety

    Args:
        key: The raw string value to sanitize.

    Returns
    -------
        The sanitized string safe for interpolation into Cosmos DB SQL queries.
    """
    original = key

    # Escape backslashes first (before other escapes that use backslash)
    key = key.replace("\\", "\\\\")
    # Escape double quotes
    key = key.replace('"', '\\"')
    # Escape single quotes (SQL string literal termination)
    key = key.replace("'", "''")

    if key != original:
        logger.warning(
            "Cosmos DB query sanitization applied: escaped characters in key '%s'",
            original,
        )

    return key
