"""Human feedback node for collecting user input on redline plans."""

from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from src.redline.state import RedlineState, StructuredFeedback
from src.redline.prompts import structured_feedback_prompt_template


def collect_user_feedback(
    state: RedlineState, config: RunnableConfig
) -> Dict[str, Any]:
    """Collect user feedback on the redline plan and clarification questions.

    This node:
    1. Presents the generated redline plan to the user
    2. Shows the clarification questions with indexes
    3. Collects structured user feedback via an interrupt
    4. Saves feedback directly to state

    Args:
        state: Current graph state with redline plan and questions
        config: Configuration for the workflow

    Returns:
        Dict with structured feedback saved to state
    """

    # Get the current plan and questions
    redline_plan = state["redline_plan"]
    clarification_questions = state["clarification_questions"]

    # Format the plan and questions for user review with question IDs
    questions_str = "\n".join(
        [
            f"{i+1}. {question.question}"
            for i, question in enumerate(clarification_questions)
        ]
    )

    # Create the structured feedback prompt using the template
    structured_prompt = structured_feedback_prompt_template.format(
        redline_plan=redline_plan, questions_str=questions_str
    )

    print("💬 Requesting structured user feedback on redline plan...")

    # Get feedback from user via interrupt
    feedback = interrupt(structured_prompt)

    # Create structured feedback object
    structured_feedback = StructuredFeedback(**feedback)

    # Save structured feedback to state
    return {
        "user_approved": structured_feedback.approval,
        "structured_feedback": structured_feedback,
        "clarification_answers": structured_feedback.answer_to_clarification_questions,
    }
