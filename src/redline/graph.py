from typing import Dict, Any
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from langgraph.graph import START, END, StateGraph

from src.redline.state import RedlineState, RedlineStateInput, RedlineStateOutput
from src.redline.configuration import Configuration
from src.redline.utils import suppress_langchain_warnings
from src.redline.nodes import (
    retrieve_documents,
    generate_redline_plan,
    collect_user_feedback,
    generate_redline_suggestions,
    refine_redline_suggestions,
)

# Suppress LangChain deprecation warnings
suppress_langchain_warnings()

# Build the graph
builder = StateGraph(
    RedlineState,
    input=RedlineStateInput,
    output=RedlineStateOutput,
    config_schema=Configuration,
)

# Add nodes
builder.add_node("retrieve_documents", retrieve_documents)
builder.add_node("generate_redline_plan", generate_redline_plan)
builder.add_node("collect_user_feedback", collect_user_feedback)
builder.add_node("generate_redline_suggestions", generate_redline_suggestions)
builder.add_node("refine_redline_suggestions", refine_redline_suggestions)


def route_after_feedback(state: RedlineState):
    """Route after user feedback - either generate suggestions or regenerate plan."""
    structured_feedback = state.get("structured_feedback")
    if structured_feedback and structured_feedback.approval:
        return "generate_redline_suggestions"
    else:
        return "generate_redline_plan"


def route_after_refinement(state: RedlineState):
    """Route after refinement - continue refining or end."""
    current_iteration = state.get("refinement_iteration", 0)
    more_refinement_needed = state.get("more_refinement_needed", False)

    # Use default max iterations (configuration will be handled in the refinement node)
    max_iterations = 3

    # Check if we've reached max iterations or no more edits are needed
    if current_iteration >= max_iterations or not more_refinement_needed:
        return END

    # Continue refining if more edits are needed and we haven't reached max iterations
    return "refine_redline_suggestions"


# Add edges
builder.add_edge(START, "retrieve_documents")
builder.add_edge("retrieve_documents", "generate_redline_plan")
builder.add_edge("generate_redline_plan", "collect_user_feedback")
builder.add_conditional_edges(
    "collect_user_feedback",
    route_after_feedback,
    ["generate_redline_plan", "generate_redline_suggestions"],
)
builder.add_edge("generate_redline_suggestions", "refine_redline_suggestions")
builder.add_conditional_edges(
    "refine_redline_suggestions",
    route_after_refinement,
    ["refine_redline_suggestions", END],
)

# Compile the graph
graph = builder.compile()
