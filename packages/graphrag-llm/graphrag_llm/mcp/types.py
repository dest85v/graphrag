# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""MCP types for graphrag-llm."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionToolParam


@dataclass
class MCPTool:
    """A tool discovered from an MCP server.

    Represents a tool that can be invoked via the Model Context Protocol.
    Immutable after creation.
    """

    name: str
    """Unique tool name used for invocation."""

    description: str
    """Human-readable description of what the tool does."""

    input_schema: dict[str, Any] = field(default_factory=dict)
    """JSON Schema object defining required and optional parameters."""

    def to_openai_tool(self) -> ChatCompletionToolParam:
        """Convert this MCPTool to an OpenAI ChatCompletionTool format.

        Returns
        -------
        ChatCompletionToolParam
            A tool dict with type="function" and function={name, description, parameters}.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }
