"""Plan generation node for creating redline plans and clarification questions."""

from typing import Dict, Any, List, Tuple, Optional
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from src.redline.state import RedlineState, ClarificationQuestion
from src.redline.configuration import Configuration
from src.redline.prompts import (
    redline_planner_instructions,
    planning_prompt_template,
    planning_revision_prompt_template,
    reference_doc_summary_template,
)
from src.redline.utils import get_config_value, format_reference_documents_content


def is_plan_revision(state: RedlineState) -> bool:
    """Check if this is a plan revision (feedback exists and approval is false)."""
    feedback = state.get("structured_feedback")
    return feedback is not None and not feedback.approval


class RedlinePlanOutput(BaseModel):
    """Structured output schema for redline plan generation."""

    plan: str = Field(
        description="A detailed redline plan outlining how to approach editing the document. This should include structural changes, clause-specific revisions, or references to precedent language."
    )
    clarification_questions: List[str] = Field(
        description="A list of clarifying questions that must be answered before proceeding with the redline. Each question should be clear, actionable, and help improve the quality of the final redlined document.",
        max_length=3,
        min_length=1,
    )


def _extract_state_data(state: RedlineState) -> Dict[str, Any]:
    """Extract common data from state that's used by both plan generation functions."""
    return {
        "doc_id": state["doc_id"],
        "reference_doc_ids": state["reference_doc_ids"],
        "general_comments": state["general_comments"],
        "reference_documents_comments": state["reference_documents_comments"],
        "base_document_content": state["base_document_content"],
        "reference_documents_content": state["reference_documents_content"],
    }


def _configure_planner_model(config: RunnableConfig) -> Tuple[Any, int]:
    """Set up the planner model and return it along with max_questions."""
    configurable = Configuration.from_runnable_config(config)

    planner_provider = get_config_value(configurable.planner_provider, "openai")
    planner_model_name = get_config_value(configurable.planner_model, "gpt-4o-mini")
    planner_model_kwargs = get_config_value(configurable.planner_model_kwargs, {})
    max_questions = get_config_value(configurable.max_clarification_questions, 3)

    planner_model = init_chat_model(
        model=planner_model_name,
        model_provider=planner_provider,
        model_kwargs=planner_model_kwargs,
    )

    return planner_model, max_questions, planner_provider, planner_model_name


def _format_answered_questions(
    structured_feedback: Any,
    previous_clarification_questions: List[ClarificationQuestion],
) -> str:
    """Format answered questions with both question and answer."""
    if not structured_feedback.answer_to_clarification_questions:
        return "No answers to clarification questions provided."

    answered_parts = []
    for q_id, answer in structured_feedback.answer_to_clarification_questions:
        index = q_id - 1  # q_id is 1-indexed, so subtract 1 for list indexing
        question_text = previous_clarification_questions[index].question
        answered_parts.append(f"Q{q_id}: {question_text}\nA{q_id}: {answer}")

    return "\n\n".join(answered_parts)


async def _invoke_planner_model(
    planner_model: Any,
    prompt: str,
) -> Tuple[str, List[str]]:
    """Invoke the planner model and return plan content and questions."""
    structured_planner_model = planner_model.with_structured_output(RedlinePlanOutput)

    try:
        response = await structured_planner_model.ainvoke(
            [
                SystemMessage(content=redline_planner_instructions),
                HumanMessage(content=prompt),
            ]
        )

        plan_content = response.plan
        questions_list = response.clarification_questions

        print(f"✅ Generated redline plan ({len(plan_content)} characters)")
        return plan_content, questions_list

    except Exception as e:
        print(f"❌ Failed to generate plan with LLM: {e}")
        raise e


def _create_clarification_questions(
    questions_list: List[str],
) -> List[ClarificationQuestion]:
    """Convert string questions to ClarificationQuestion objects."""
    clarification_questions = [
        ClarificationQuestion(question=question) for question in questions_list
    ]
    print(f"❓ Generated {len(clarification_questions)} clarification questions")
    return clarification_questions


async def generate_redline_plan(
    state: RedlineState, config: RunnableConfig
) -> Dict[str, Any]:
    """Generate a comprehensive redline plan and clarification questions.

    This node:
    1. Analyzes the base document and reference documents
    2. Considers the general comments and document-specific comments
    3. Generates a detailed redline plan
    4. Creates exactly n clarification questions for the user

    Args:
        state: Current graph state containing documents and comments
        config: Configuration for models and planning parameters

    Returns:
        Dict containing the redline plan and clarification questions
    """
    # Check if this is a revision
    if is_plan_revision(state):
        return await _generate_revised_plan(state, config)

    # Extract common data from state
    state_data = _extract_state_data(state)

    # Set up planner model
    planner_model, max_questions, planner_provider, planner_model_name = (
        _configure_planner_model(config)
    )

    print(f"🧠 Generating redline plan using {planner_provider}/{planner_model_name}")

    # Format reference documents
    reference_docs_str = format_reference_documents_content(state)

    # Create the planning prompt using template
    planning_prompt = planning_prompt_template.format(
        redline_planner_instructions=redline_planner_instructions,
        doc_id=state_data["doc_id"],
        base_document_content=state_data["base_document_content"],
        general_comments=state_data["general_comments"],
        reference_docs_str=reference_docs_str,
        max_questions=max_questions,
    )

    # Generate the plan using the LLM
    plan_content, questions_list = await _invoke_planner_model(
        planner_model, planning_prompt
    )

    # Convert string questions to ClarificationQuestion objects
    clarification_questions = _create_clarification_questions(questions_list)

    return {
        "redline_plan": plan_content,
        "clarification_questions": clarification_questions,
    }


async def _generate_revised_plan(
    state: RedlineState, config: RunnableConfig
) -> Dict[str, Any]:
    """Generate revised plan based on user feedback."""
    # Extract common data from state
    state_data = _extract_state_data(state)

    # Get feedback and previous plan
    structured_feedback = state["structured_feedback"]
    previous_plan = state.get("previous_redline_plan", "")
    specific_feedback = (
        structured_feedback.specific_feedback or "No specific feedback provided."
    )

    # Get the previous clarification questions to include in the answered questions
    previous_clarification_questions = state.get("clarification_questions", [])

    # Format answered questions with both question and answer
    answered_questions = _format_answered_questions(
        structured_feedback, previous_clarification_questions
    )

    # Set up planner model
    planner_model, max_questions, planner_provider, planner_model_name = (
        _configure_planner_model(config)
    )

    print(
        f"🔄 Revising redline plan based on feedback using {planner_provider}/{planner_model_name}"
    )

    # Format reference documents
    reference_docs_str = format_reference_documents_content(state)

    # Create the revision prompt
    revision_prompt = planning_revision_prompt_template.format(
        general_comments=state_data["general_comments"],
        previous_plan=previous_plan,
        specific_feedback=specific_feedback,
        answered_questions=answered_questions,
        doc_id=state_data["doc_id"],
        base_document_content=state_data["base_document_content"],
        reference_docs_str=reference_docs_str,
        max_questions=max_questions,
    )

    # Generate the revised plan
    plan_content, questions_list = await _invoke_planner_model(
        planner_model, revision_prompt
    )

    # Convert string questions to ClarificationQuestion objects
    clarification_questions = _create_clarification_questions(questions_list)

    return {
        "redline_plan": plan_content,
        "clarification_questions": clarification_questions,
    }
