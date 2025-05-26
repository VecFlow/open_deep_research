"""Plan generation node for creating redline plans and clarification questions."""

from typing import Dict, Any
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src.redline.state import RedlineState, ClarificationQuestion
from src.redline.configuration import Configuration
from src.redline.prompts import (
    redline_planner_instructions,
    clarification_questions_instructions,
)
from src.redline.utils import get_config_value


async def generate_redline_plan(
    state: RedlineState, config: RunnableConfig
) -> Dict[str, Any]:
    """Generate a comprehensive redline plan and clarification questions.

    This node:
    1. Analyzes the base document and reference documents
    2. Considers the general comments and document-specific comments
    3. Generates a detailed redline plan
    4. Creates exactly 3 clarification questions for the user

    Args:
        state: Current graph state containing documents and comments
        config: Configuration for models and planning parameters

    Returns:
        Dict containing the redline plan and clarification questions
    """

    # Get inputs from state
    doc_id = state["doc_id"]
    reference_doc_ids = state["reference_doc_ids"]
    general_comments = state["general_comments"]
    reference_documents_comments = state["reference_documents_comments"]
    base_document_content = state["base_document_content"]
    reference_documents_content = state["reference_documents_content"]

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Set up planner model
    planner_provider = get_config_value(configurable.planner_provider, "openai")
    planner_model_name = get_config_value(configurable.planner_model, "gpt-4o-mini")
    planner_model_kwargs = get_config_value(configurable.planner_model_kwargs, {})
    max_questions = get_config_value(configurable.max_clarification_questions, 3)

    planner_model = init_chat_model(
        model=planner_model_name,
        model_provider=planner_provider,
        model_kwargs=planner_model_kwargs,
    )

    print(f"🧠 Generating redline plan using {planner_provider}/{planner_model_name}")

    # Format reference documents with their comments
    reference_docs_summary = []
    for i, (ref_id, ref_content, ref_comment) in enumerate(
        zip(
            reference_doc_ids, reference_documents_content, reference_documents_comments
        )
    ):
        ref_summary = f"""
Reference Document {i+1}: {ref_id}
Comment: {ref_comment}
Content Preview: {ref_content[:500]}{'...' if len(ref_content) > 500 else ''}
"""
        reference_docs_summary.append(ref_summary)

    reference_docs_str = "\n".join(reference_docs_summary)

    # Create the planning prompt
    planning_prompt = f"""
{redline_planner_instructions}

TASK DETAILS:
Base Document ID: {doc_id}
Base Document Content: {base_document_content[:1000]}{'...' if len(base_document_content) > 1000 else ''}

General Instructions: {general_comments}

{reference_docs_str}

Please provide:
1. A detailed redline plan
2. Exactly {max_questions} clarification questions
"""

    # Generate the plan using the LLM
    try:
        response = await planner_model.ainvoke(
            [
                SystemMessage(content=redline_planner_instructions),
                HumanMessage(content=planning_prompt),
            ]
        )

        # For now, use a structured approach with placeholders
        # TODO: Implement structured output for better parsing
        plan_content = response.content
        print(f"✅ Generated redline plan ({len(plan_content)} characters)")

    except Exception as e:
        print(f"❌ Failed to generate plan with LLM: {e}")
        plan_content = f"""
REDLINE PLAN (FALLBACK):

Base Document: {doc_id}
Reference Documents: {', '.join(reference_doc_ids)}
General Comments: {general_comments}

1. Document Analysis Phase:
   - Compare base document structure with reference documents
   - Identify key differences in content, format, and style
   - Focus on areas mentioned in general comments

2. Redlining Approach:
   - Systematic review section by section
   - Incorporate feedback from reference document comments
   - Track changes and provide rationale for each modification

3. Implementation Strategy:
   - Prioritize changes based on general comments
   - Ensure consistency with reference materials
   - Maintain document integrity and readability
"""

    # Generate clarification questions
    clarification_questions = [
        ClarificationQuestion(
            question="What is the primary goal of this redlining task - compliance alignment, content improvement, or stylistic consistency?"
        ),
        ClarificationQuestion(
            question="Should certain reference documents be prioritized over others when conflicts arise?"
        ),
        ClarificationQuestion(
            question="Are there specific sections or types of content that require special attention during the redlining process?"
        ),
    ]

    print(f"❓ Generated {len(clarification_questions)} clarification questions")

    return {
        "redline_plan": plan_content,
        "clarification_questions": clarification_questions,
    }
