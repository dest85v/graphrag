# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for MCP types."""


from graphrag_llm.mcp.types import MCPTool


class TestMCPTool:
    """Tests for the MCPTool dataclass."""

    def test_mcp_tool_creation(self):
        """Test basic MCPTool creation."""
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {"x": {"type": "integer"}}},
        )
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.input_schema["type"] == "object"

    def test_mcp_tool_defaults(self):
        """Test MCPTool with default input_schema."""
        tool = MCPTool(name="tool", description="desc")
        assert tool.input_schema == {}

    def test_to_openai_tool_format(self):
        """Test conversion to OpenAI ChatCompletionTool format."""
        tool = MCPTool(
            name="echo",
            description="Echo back input",
            input_schema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
        )
        openai_tool = tool.to_openai_tool()
        assert openai_tool["type"] == "function"  # type: ignore[index]
        assert openai_tool["function"]["name"] == "echo"  # type: ignore[index]
        assert openai_tool["function"]["description"] == "Echo back input"  # type: ignore[index]
        assert openai_tool["function"]["parameters"]["type"] == "object"  # type: ignore[index]
        assert "message" in openai_tool["function"]["parameters"]["properties"]  # type: ignore[index]

    def test_to_openai_tool_empty_schema(self):
        """Test conversion with empty schema."""
        tool = MCPTool(name="ping", description="Ping")
        openai_tool = tool.to_openai_tool()
        assert openai_tool["type"] == "function"  # type: ignore[index]
        assert openai_tool["function"]["parameters"] == {}  # type: ignore[index]

    def test_to_openai_tool_mock_integration(self):
        """Test that the format matches what openai.pydantic_function_tool expects."""
        tool = MCPTool(
            name="add",
            description="Add two numbers",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "First number"},
                    "b": {"type": "integer", "description": "Second number"},
                },
                "required": ["a", "b"],
            },
        )
        openai_tool = tool.to_openai_tool()
        # Verify structure matches OpenAI's expected tool format
        assert isinstance(openai_tool, dict)
        assert "type" in openai_tool
        assert "function" in openai_tool
        func = openai_tool["function"]
        assert "name" in func
        assert "description" in func
        assert "parameters" in func
