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
from src.redline.utils import suppress_langchain_warnings
from src.redline.nodes import (
    retrieve_documents,
    generate_redline_plan,
    collect_user_feedback,
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


def route_after_feedback(state: RedlineState):
    """Route after user feedback - either end or regenerate plan."""
    if state.get("user_approved", False):
        return END
    else:
        return "generate_redline_plan"


# Add edges
builder.add_edge(START, "retrieve_documents")
builder.add_edge("retrieve_documents", "generate_redline_plan")
builder.add_edge("generate_redline_plan", "collect_user_feedback")
builder.add_conditional_edges(
    "collect_user_feedback", route_after_feedback, ["generate_redline_plan", END]
)

# Compile the graph
graph = builder.compile()
