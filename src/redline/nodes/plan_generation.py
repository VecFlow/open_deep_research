"""Plan generation node for creating redline plans and clarification questions."""

from typing import Dict, Any, List
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from src.redline.state import RedlineState, ClarificationQuestion
from src.redline.configuration import Configuration
from src.redline.prompts import (
    redline_planner_instructions,
    planning_prompt_template,
    reference_doc_summary_template,
)
from src.redline.utils import get_config_value


class RedlinePlanOutput(BaseModel):
    """Structured output schema for redline plan generation."""

    plan: str = Field(
        description="A detailed redline plan outlining how to approach editing the document. This should include structural changes, clause-specific revisions, or references to precedent language."
    )
    clarification_questions: List[str] = Field(
        description="A list of clarifying questions that must be answered before proceeding with the redline. Each question should be clear, actionable, and help improve the quality of the final redlined document.",
        max_items=3,
        min_items=1,
    )


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

    # Format reference documents with their comments using template
    reference_docs_summary = []
    for i, (ref_id, ref_content, ref_comment) in enumerate(
        zip(
            reference_doc_ids, reference_documents_content, reference_documents_comments
        )
    ):
        ref_summary = reference_doc_summary_template.format(
            doc_number=i + 1,
            ref_id=ref_id,
            ref_comment=ref_comment,
            ref_content=ref_content,
        )
        reference_docs_summary.append(ref_summary)

    reference_docs_str = "\n".join(reference_docs_summary)

    # Create the planning prompt using template
    planning_prompt = planning_prompt_template.format(
        redline_planner_instructions=redline_planner_instructions,
        doc_id=doc_id,
        base_document_content=base_document_content,
        general_comments=general_comments,
        reference_docs_str=reference_docs_str,
        max_questions=max_questions,
    )

    # save the planning prompt to a file
    with open("planning_prompt.txt", "w") as f:
        f.write(planning_prompt)

    # Set up structured output model
    structured_planner_model = planner_model.with_structured_output(RedlinePlanOutput)

    # Generate the plan using the LLM with structured output
    try:
        response = await structured_planner_model.ainvoke(
            [
                SystemMessage(content=redline_planner_instructions),
                HumanMessage(content=planning_prompt),
            ]
        )

        # Extract structured output
        plan_content = response.plan
        questions_list = response.clarification_questions

        print(f"✅ Generated redline plan ({len(plan_content)} characters)")

    except Exception as e:
        print(f"❌ Failed to generate plan with LLM: {e}")
        raise e

    # Convert string questions to ClarificationQuestion objects
    clarification_questions = [
        ClarificationQuestion(question=question) for question in questions_list
    ]

    print(f"❓ Generated {len(clarification_questions)} clarification questions")

    return {
        "redline_plan": plan_content,
        "clarification_questions": clarification_questions,
    }
