# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Jinja2-based secure template engine for prompt rendering.

Replaces str.format() to prevent prompt injection via user-controlled input.
User input is passed as context variables, not as template strings, so brace
characters in user data are never interpreted as template syntax.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from jinja2 import BaseLoader, Environment, StrictUndefined, Template, TemplateSyntaxError, UndefinedError

logger = logging.getLogger(__name__)

# Shared Jinja2 environment with custom { } delimiters matching existing prompt syntax
_env = Environment(
    loader=BaseLoader(),
    variable_start_string="{",
    variable_end_string="}",
    undefined=StrictUndefined,
)


def render_prompt(template: str, /, **context: Any) -> str:
    """Render a prompt template with context variables safely.

    User-controlled values (document text, queries, context data) are passed
    as context variables, not as template strings. This means brace characters
    in user data are never interpreted as template syntax.

    Args:
        template: A prompt template string containing ``{variable}`` placeholders.
        **context: Variable names mapped to values for substitution.

    Returns:
        The rendered prompt with all placeholders substituted.

    Raises:
        KeyError: If a placeholder references a key not present in context.
        TemplateSyntaxError: If the template contains invalid Jinja2 syntax.
    """
    # Compile and cache template
    cache_key = hashlib.sha256(template.encode("utf-8")).hexdigest()[:16]
    if not hasattr(render_prompt, "_cache"):
        render_prompt._cache = {}  # type: ignore[attr-defined]
    if cache_key not in render_prompt._cache:  # type: ignore[attr-defined]
        render_prompt._cache[cache_key] = _env.from_string(template)  # type: ignore[attr-defined]
    tpl = render_prompt._cache[cache_key]  # type: ignore[attr-defined]

    try:
        return tpl.render(**context)
    except UndefinedError as e:
        # Extract variable name from Jinja2 error and re-raise as KeyError
        msg = str(e)
        # UndefinedError message: "'varname' is undefined"
        for key in context.keys():
            if key in msg:
                raise KeyError(f"Missing key '{key}' in prompt template") from e
        raise KeyError(msg) from e
