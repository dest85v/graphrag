# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Persona generating module for fine-tuning GraphRAG prompts."""

from typing import TYPE_CHECKING

from graphrag.prompt_tune.defaults import DEFAULT_TASK
from graphrag.prompt_tune.prompt.persona import GENERATE_PERSONA_PROMPT
from graphrag.utils.jinja_engine import render_prompt

if TYPE_CHECKING:
    from graphrag_llm.completion import LLMCompletion
    from graphrag_llm.types import LLMCompletionResponse


async def generate_persona(
    model: "LLMCompletion",
    domain: str,
    task: str = DEFAULT_TASK,
) -> str:
    """Generate an LLM persona to use for GraphRAG prompts.

    Parameters
    ----------
    - model (LLMCompletion): The LLM to use for generation
    - domain (str): The domain to generate a persona for
    - task (str): The task to generate a persona for. Default is DEFAULT_TASK
    """
    formatted_task = render_prompt(task, domain=domain)
    persona_prompt = render_prompt(GENERATE_PERSONA_PROMPT, sample_task=formatted_task)

    response: LLMCompletionResponse = await model.completion_async(
        messages=persona_prompt,
    )  # type: ignore

    return response.content
