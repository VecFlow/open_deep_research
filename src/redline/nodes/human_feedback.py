"""Human feedback node for collecting user input on redline plans."""

from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from src.redline.state import RedlineState


def collect_user_feedback(
    state: RedlineState, config: RunnableConfig
) -> Dict[str, Any]:
    """Collect user feedback on the redline plan and clarification questions.

        This node:
    1. Presents the generated redline plan to the user
    2. Shows the clarification questions
    3. Collects user feedback via an interrupt
    4. Updates state with feedback and approval status

    Args:
        state: Current graph state with redline plan and questions
        config: Configuration for the workflow

    Returns:
        Dict with user feedback and approval status
    """

    # Get the current plan and questions
    redline_plan = state["redline_plan"]
    clarification_questions = state["clarification_questions"]
    doc_id = state["doc_id"]
    reference_doc_ids = state["reference_doc_ids"]

    # Format the plan and questions for user review
    questions_str = "\n".join(
        [
            f"{i+1}. {question.question}"
            for i, question in enumerate(clarification_questions)
        ]
    )

    # Create the feedback prompt
    feedback_prompt = f"""
📋 REDLINE PLAN REVIEW

Base Document: {doc_id}
Reference Documents: {', '.join(reference_doc_ids)}

🎯 GENERATED REDLINE PLAN:
{redline_plan}

❓ CLARIFICATION QUESTIONS:
{questions_str}

---

Please review the redline plan and clarification questions above.

OPTIONS:
1. Type 'approve' or 'yes' to proceed with this plan
2. Provide specific feedback to regenerate the plan (e.g., "Focus more on legal compliance", "Add more detail about formatting changes", etc.)
3. Answer any of the clarification questions to help refine the plan

Your feedback:"""

    print("💬 Requesting user feedback on redline plan...")

    # Get feedback from user via interrupt
    feedback = interrupt(feedback_prompt)

    # Process the feedback
    if isinstance(feedback, str):
        feedback_lower = feedback.lower().strip()

        # Check if user approves the plan
        if feedback_lower in ["approve", "yes", "approved", "good", "ok", "proceed"]:
            print("✅ User approved the redline plan")
            return {"user_approved": True, "user_feedback": feedback}

        # User provided feedback for improvement
        else:
            print(f"📝 User provided feedback: {feedback}")
            return {"user_approved": False, "user_feedback": feedback}

    elif isinstance(feedback, bool) and feedback is True:
        print("✅ User approved the redline plan")
        return {"user_approved": True, "user_feedback": "approved"}

    else:
        # Invalid feedback type, ask for regeneration
        print("⚠️ Invalid feedback received, regenerating plan...")
        return {"user_approved": False, "user_feedback": "invalid_feedback"}
