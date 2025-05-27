from typing import List, TypedDict, Optional, Tuple
from pydantic import BaseModel, Field


class ClarificationQuestion(BaseModel):
    question: str = Field(
        description="A clarification question to help refine the redline task."
    )


class StructuredFeedback(BaseModel):
    """Structured feedback from user on redline plan."""

    approval: bool = Field(description="Whether the user approves the redline plan")
    specific_feedback: Optional[str] = Field(
        default=None, description="Optional specific feedback or comments from the user"
    )
    answer_to_clarification_questions: Optional[List[Tuple[int, str]]] = Field(
        default=None,
        description="Optional answers to clarification questions as list of (question_id, answer) tuples",
    )


class RedlineStateInput(TypedDict):
    doc_id: str  # Base document ID
    reference_doc_ids: List[str]  # List of reference document IDs
    general_comments: str  # Instructions for this specific redline task
    reference_documents_comments: List[str]  # Comments for each reference document


class RedlineStateOutput(TypedDict):
    redline_plan: str  # Plan for the redline task
    clarification_questions: List[
        ClarificationQuestion
    ]  # 3 questions for user clarification


class RedlineState(TypedDict):
    # Input fields
    doc_id: str  # Base document ID
    reference_doc_ids: List[str]  # List of reference document IDs
    general_comments: str  # Instructions for this specific redline task
    reference_documents_comments: List[str]  # Comments for each reference document

    # Working fields (can be added as the graph evolves)
    base_document_content: str  # Content of the base document
    reference_documents_content: List[str]  # Content of reference documents
    user_approved: bool  # Whether user approved the plan
    structured_feedback: Optional[StructuredFeedback]  # Structured feedback from user
    clarification_answers: Optional[
        List[Tuple[int, str]]
    ]  # Answers to clarification questions

    # Output fields
    redline_plan: str  # Plan for the redline task
    clarification_questions: List[ClarificationQuestion]
