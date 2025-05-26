from typing import Dict, Any
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from langgraph.graph import START, END, StateGraph

from src.redline.state import (
    RedlineState,
    RedlineStateInput,
    RedlineStateOutput,
    ClarificationQuestion,
)
from src.redline.configuration import Configuration
from src.redline.prompts import (
    redline_planner_instructions,
    clarification_questions_instructions,
)


async def generate_redline_plan(
    state: RedlineState, config: RunnableConfig
) -> Dict[str, Any]:
    """Generate a redline plan and clarification questions.

    This node:
    1. Takes the base document ID and reference document IDs
    2. Retrieves document content (placeholder for now)
    3. Analyzes the general comments and reference document comments
    4. Generates a comprehensive redline plan
    5. Creates 3 clarification questions for the user

    Args:
        state: Current graph state containing document IDs and comments
        config: Configuration for models, document APIs, etc.

    Returns:
        Dict containing the redline plan and clarification questions
    """

    # Get inputs from state
    doc_id = state["doc_id"]
    reference_doc_ids = state["reference_doc_ids"]
    general_comments = state["general_comments"]
    reference_documents_comments = state["reference_documents_comments"]

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Set up planner model
    planner_provider = configurable.planner_provider or "openai"
    planner_model_name = configurable.planner_model or "gpt-4o-mini"
    planner_model_kwargs = configurable.planner_model_kwargs or {}

    planner_model = init_chat_model(
        model=planner_model_name,
        model_provider=planner_provider,
        model_kwargs=planner_model_kwargs,
    )

    # TODO: Implement document retrieval
    # For now, using placeholders
    base_document_content = f"[PLACEHOLDER: Content of document {doc_id}]"
    reference_documents_content = [
        f"[PLACEHOLDER: Content of reference document {ref_id}]"
        for ref_id in reference_doc_ids
    ]

    # TODO: Implement actual LLM calls for planning
    # For now, using placeholders
    redline_plan = f"""
    REDLINE PLAN (PLACEHOLDER):
    
    Base Document: {doc_id}
    Reference Documents: {', '.join(reference_doc_ids)}
    General Comments: {general_comments}
    
    1. Document Analysis Phase:
       - Compare base document structure with reference documents
       - Identify key differences in content, format, and style
    
    2. Redlining Approach:
       - Focus areas based on general comments
       - Incorporate specific feedback from reference document comments
    
    3. Implementation Strategy:
       - Systematic review section by section
       - Track changes and rationale
       - Ensure consistency with reference materials
    """

    # Create placeholder clarification questions
    clarification_questions = [
        ClarificationQuestion(
            question="What is the primary goal of this redlining task - compliance alignment, content improvement, or stylistic consistency?"
        ),
        ClarificationQuestion(
            question="Should certain reference documents be prioritized over others, and if so, in what order?"
        ),
        ClarificationQuestion(
            question="Are there specific sections or types of content that require special attention during the redlining process?"
        ),
    ]

    return {
        "base_document_content": base_document_content,
        "reference_documents_content": reference_documents_content,
        "redline_plan": redline_plan,
        "clarification_questions": clarification_questions,
    }


# Build the graph
builder = StateGraph(
    RedlineState,
    input=RedlineStateInput,
    output=RedlineStateOutput,
    config_schema=Configuration,
)

# Add nodes
builder.add_node("generate_redline_plan", generate_redline_plan)

# Add edges
builder.add_edge(START, "generate_redline_plan")
builder.add_edge("generate_redline_plan", END)

# Compile the graph
graph = builder.compile()
