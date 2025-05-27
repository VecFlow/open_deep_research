"""Refinement node for iteratively improving redline suggestions."""

from typing import Dict, Any
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src.redline.state import RedlineState, RedlineSuggestions, RefinementOutput
from src.redline.configuration import Configuration
from src.redline.utils import get_config_value, format_reference_documents_content
from src.redline.prompts import (
    redline_suggestions_system_prompt,
    refinement_prompt_template,
)


async def refine_redline_suggestions(
    state: RedlineState, config: RunnableConfig
) -> Dict[str, Any]:
    """Iteratively refine redline suggestions by asking for additional improvements.

    This node:
    1. Reviews the current redline suggestions against the plan and documents
    2. Asks the model if there are any additional suggestions to make
    3. Combines new suggestions with existing ones if more_edits is true
    4. Tracks iteration count and respects max iterations limit

    Args:
        state: Current graph state containing plan, documents, and existing suggestions
        config: Configuration for models and processing parameters

    Returns:
        Dict containing updated suggestions and iteration tracking
    """
    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Get current iteration count (default to 0 if not set)
    current_iteration = state.get("refinement_iteration", 0)
    max_iterations = get_config_value(configurable.max_refinement_iterations, 3)

    print(f"🔄 Refinement iteration {current_iteration + 1}/{max_iterations}")

    # Check if we've reached max iterations
    if current_iteration >= max_iterations:
        print(f"⏹️ Reached maximum refinement iterations ({max_iterations})")
        return {
            "refinement_iteration": current_iteration,
            "more_refinement_needed": False,
        }

    # Configure the model for refinement
    provider = get_config_value(configurable.planner_provider, "openai")
    model_name = get_config_value(configurable.planner_model, "gpt-4o-mini")
    model_kwargs = get_config_value(configurable.planner_model_kwargs, {})

    model = init_chat_model(
        model=model_name,
        model_provider=provider,
        model_kwargs=model_kwargs,
    )

    print(f"🔧 Refining redline suggestions using {provider}/{model_name}")

    # Format reference documents
    reference_docs_str = format_reference_documents_content(state)

    # Get existing suggestions for context
    existing_suggestions = state.get("redline_suggestions")
    num_individual = (
        len(existing_suggestions.suggestions) if existing_suggestions else 0
    )
    num_replace_all = (
        len(existing_suggestions.replace_all_suggestions) if existing_suggestions else 0
    )

    # Create the refinement prompt
    prompt = refinement_prompt_template.format(
        current_iteration=current_iteration + 1,
        max_iterations=max_iterations,
        redline_plan=state["redline_plan"],
        base_document_content=state["base_document_content"],
        reference_documents_content=reference_docs_str,
        num_individual_suggestions=num_individual,
        num_replace_all_suggestions=num_replace_all,
    )

    # Generate refinement suggestions using structured output
    structured_model = model.with_structured_output(RefinementOutput)

    try:
        response = await structured_model.ainvoke(
            [
                SystemMessage(content=redline_suggestions_system_prompt),
                HumanMessage(content=prompt),
            ]
        )

        print(f"✅ Refinement iteration {current_iteration + 1} completed")
        print(f"   More edits needed: {response.more_edits}")

        # Prepare return data
        return_data = {
            "refinement_iteration": current_iteration + 1,
            "more_refinement_needed": response.more_edits,
        }

        # If there are more edits, combine with existing suggestions
        if response.more_edits and existing_suggestions:
            print(
                f"   Adding {len(response.suggestions.suggestions)} individual and {len(response.suggestions.replace_all_suggestions)} replace-all suggestions"
            )

            # Combine suggestions
            combined_suggestions = RedlineSuggestions(
                suggestions=existing_suggestions.suggestions
                + response.suggestions.suggestions,
                replace_all_suggestions=existing_suggestions.replace_all_suggestions
                + response.suggestions.replace_all_suggestions,
            )

            return_data["redline_suggestions"] = combined_suggestions
        elif response.more_edits and not existing_suggestions:
            # First iteration with new suggestions
            print(
                f"   Adding {len(response.suggestions.suggestions)} individual and {len(response.suggestions.replace_all_suggestions)} replace-all suggestions"
            )
            return_data["redline_suggestions"] = response.suggestions
        else:
            print("   No additional suggestions needed")

        return return_data

    except Exception as e:
        print(f"❌ Failed to refine redline suggestions: {e}")
        raise e
