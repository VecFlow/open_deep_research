"""Redline suggestions generation node for creating structured redline suggestions."""

from typing import Dict, Any, List
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src.redline.state import RedlineState, RedlineSuggestions
from src.redline.configuration import Configuration
from src.redline.utils import get_config_value, format_reference_documents_content
from src.redline.prompts import (
    redline_suggestions_system_prompt,
    redline_suggestions_prompt_template,
)


async def generate_redline_suggestions(
    state: RedlineState, config: RunnableConfig
) -> Dict[str, Any]:
    """Generate structured redline suggestions based on the approved redline plan.

    This node:
    1. Takes the approved redline plan and document content
    2. Generates structured RedlineSuggestion and ReplaceAllSuggestion objects
    3. Returns the suggestions for the next node to process

    Args:
        state: Current graph state containing approved plan and documents
        config: Configuration for models and processing parameters

    Returns:
        Dict containing the generated redline suggestions
    """
    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Configure the model for generating suggestions
    provider = get_config_value(configurable.planner_provider, "openai")
    model_name = get_config_value(configurable.planner_model, "gpt-4o-mini")
    model_kwargs = get_config_value(configurable.planner_model_kwargs, {})

    model = init_chat_model(
        model=model_name,
        model_provider=provider,
        model_kwargs=model_kwargs,
    )

    print(f"🔧 Generating redline suggestions using {provider}/{model_name}")

    # Format reference documents
    reference_docs_str = format_reference_documents_content(state)

    # Create the prompt using the approved plan (no clarification questions needed)
    prompt = redline_suggestions_prompt_template.format(
        redline_plan=state["redline_plan"],
        base_document_content=state["base_document_content"],
        reference_documents_content=reference_docs_str,
    )

    # Generate suggestions using structured output
    structured_model = model.with_structured_output(RedlineSuggestions)

    try:
        response = await structured_model.ainvoke(
            [
                SystemMessage(content=redline_suggestions_system_prompt),
                HumanMessage(content=prompt),
            ]
        )

        print(
            f"✅ Generated {len(response.suggestions)} individual suggestions and {len(response.replace_all_suggestions)} replace-all suggestions"
        )

        return {
            "redline_suggestions": response,
            "refinement_iteration": 0,  # Initialize refinement iteration counter
        }

    except Exception as e:
        print(f"❌ Failed to generate redline suggestions: {e}")
        raise e
