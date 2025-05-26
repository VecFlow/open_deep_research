from typing import Annotated, Optional, Any, Dict
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig


class Configuration(BaseModel):
    """Configuration for the redline graph."""

    # Model configuration
    planner_provider: Annotated[
        Optional[str], Field(description="The provider for the planner model")
    ] = "openai"
    planner_model: Annotated[
        Optional[str], Field(description="The model to use for planning")
    ] = "gpt-4o-mini"
    planner_model_kwargs: Annotated[
        Optional[Dict[str, Any]],
        Field(description="Additional model kwargs for planner"),
    ] = {}

    # Document retrieval configuration
    document_api: Annotated[
        Optional[str], Field(description="API to use for document retrieval")
    ] = None
    document_api_config: Annotated[
        Optional[Dict[str, Any]], Field(description="Configuration for document API")
    ] = {}

    # Redline task configuration
    max_clarification_questions: Annotated[
        Optional[int], Field(description="Maximum number of clarification questions")
    ] = 3
    plan_detail_level: Annotated[
        Optional[str], Field(description="Level of detail for redline plan")
    ] = "detailed"

    @classmethod
    def from_runnable_config(cls, config: RunnableConfig) -> "Configuration":
        """Create Configuration from RunnableConfig."""
        configurable = config.get("configurable", {})
        return cls(**configurable)
