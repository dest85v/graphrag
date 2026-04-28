# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for the safe Jinja prompt rendering engine."""

import pytest

from graphrag.utils.jinja_engine import render_prompt


class TestRenderPromptBasic:
    """Basic substitution tests."""

    def test_single_variable(self):
        result = render_prompt("Hello {name}", name="World")
        assert result == "Hello World"

    def test_multiple_variables(self):
        result = render_prompt("{greeting} {name}!", greeting="Hello", name="World")
        assert result == "Hello World!"

    def test_variable_in_middle(self):
        result = render_prompt("prefix {var} suffix", var="mid")
        assert result == "prefix mid suffix"

    def test_numeric_value(self):
        result = render_prompt("Count: {count}", count=42)
        assert result == "Count: 42"

    def test_integer_zero_value(self):
        result = render_prompt("Value: {val}", val=0)
        assert result == "Value: 0"

    def test_empty_string_value(self):
        result = render_prompt("Text: {text}", text="")
        assert result == "Text: "


class TestRenderPromptSafeFromInjection:
    """Security tests: user input cannot inject template variables."""

    def test_double_brace_in_value(self):
        """}} in user text renders literally, does not crash."""
        result = render_prompt("Text: {input_text}", input_text="use }} for closing")
        assert result == "Text: use }} for closing"

    def test_template_like_text_in_value(self):
        """{input_text} as user text renders literally, not substituted."""
        result = render_prompt("Types: {entity_types}", entity_types="{input_text}")
        assert result == "Types: {input_text}"

    def test_single_open_brace_in_value(self):
        result = render_prompt("Text: {val}", val="a { b")
        assert result == "Text: a { b"

    def test_single_close_brace_in_value(self):
        result = render_prompt("Text: {val}", val="a } b")
        assert result == "Text: a } b"

    def test_multiple_braces_in_value(self):
        result = render_prompt("{input_text}", input_text="{{ { {}} }}")
        assert result == "{{ { {}} }}"

    def test_variable_name_as_value(self):
        result = render_prompt("Info: {info}", info="input_text")
        assert result == "Info: input_text"

    def test_placeholder_pattern_in_value(self):
        result = render_prompt("{text}", text="check {placeholder} here")
        assert result == "check {placeholder} here"

    def test_value_equals_template_placeholder_name(self):
        """Value '{entity_types}' does not substitute when template has different var."""
        result = render_prompt("{data}", data="{entity_types}")
        assert result == "{entity_types}"


class TestRenderPromptErrors:
    """Error handling tests."""

    def test_missing_key_raises_keyerror(self):
        with pytest.raises(KeyError):
            render_prompt("{missing_key}")

    def test_missing_key_error_message_includes_name(self):
        with pytest.raises(KeyError) as exc_info:
            render_prompt("{foo}")
        assert "foo" in str(exc_info.value) or "foo" in repr(exc_info.value)

    def test_one_missing_key_with_others_present(self):
        with pytest.raises(KeyError):
            render_prompt("{a} and {b}", a="ok")

    def test_empty_context_with_no_placeholders(self):
        result = render_prompt("Hello, World!")
        assert result == "Hello, World!"

    def test_empty_context_with_placeholder_raises(self):
        with pytest.raises(KeyError):
            render_prompt("{missing}")


class TestRenderPromptCaching:
    """Template caching tests."""

    def test_same_template_cached(self):
        template = "Hello {name}"
        render_prompt(template, name="Alice")
        assert hasattr(render_prompt, "_cache")
        assert len(render_prompt._cache) >= 1  # type: ignore[attr-defined]

    def test_different_templates_cached_separately(self):
        render_prompt("{a}", a="1")
        render_prompt("{b}", b="2")
        assert len(render_prompt._cache) >= 2  # type: ignore[attr-defined]


class TestRenderPromptSpecialCases:
    """Edge case tests."""

    def test_none_value(self):
        result = render_prompt("Value: {val}", val=None)
        assert result == "Value: None"

    def test_complex_json_string_value(self):
        import json
        data = json.dumps({"key": "value with } braces"}, ensure_ascii=False)
        result = render_prompt("JSON: {data}", data=data)
        assert "value with } braces" in result

    def test_multiline_template(self):
        tmpl = "Line 1\nLine 2 {var}\nLine 3"
        result = render_prompt(tmpl, var="middle")
        assert result == "Line 1\nLine 2 middle\nLine 3"

    def test_unicode_in_value(self):
        result = render_prompt("Text: {val}", val="Привет мир")
        assert result == "Text: Привет мир"

    def test_unicode_in_template(self):
        result = render_prompt("Привет, {name}!", name="Мир")
        assert result == "Привет, Мир!"

    def test_newlines_in_value(self):
        value = "line1\nline2\nline3"
        result = render_prompt("{val}", val=value)
        assert result == value

    def test_backslash_in_value(self):
        result = render_prompt("{val}", val=r"path\to\file")
        assert result == r"path\to\file"

    def test_percent_sign_in_value(self):
        result = render_prompt("{val}", val="100% done")
        assert result == "100% done"

    def test_newline_in_template(self):
        result = render_prompt("{a}\n{b}", a="first", b="second")
        assert result == "first\nsecond"

    def test_braces_in_value_with_other_placeholders(self):
        """User input with braces alongside other variables."""
        result = render_prompt("{greeting} {text} {signoff}", greeting="Hello", text="use }} for closing", signoff="Bye")
        assert result == "Hello use }} for closing Bye"
