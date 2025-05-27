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


class RedlineSuggestion(BaseModel):
    """Individual redline suggestion for context-specific edits."""

    original_text: str = Field(description="The original text of the document")
    new_text: str = Field(description="The new text of the document")


class ReplaceAllSuggestion(BaseModel):
    """Replace-all suggestion for terms that should be replaced throughout the document."""

    replace_type: str = Field(
        default="replace_all", description="Type of replacement operation"
    )
    find_text: str = Field(
        description="The exact text to find and replace throughout the document"
    )
    replace_text: str = Field(description="The text to replace all instances with")
    case_sensitive: bool = Field(
        default=False, description="Whether the replacement should be case sensitive"
    )
    whole_words_only: bool = Field(
        default=True, description="Whether to match whole words only"
    )


class RedlineSuggestions(BaseModel):
    """Complete set of redline suggestions."""

    suggestions: List[RedlineSuggestion] = Field(
        description="List of individual context-based edit suggestions"
    )
    replace_all_suggestions: List[ReplaceAllSuggestion] = Field(
        default=[],
        description="List of replace-all operations for terms that appear multiple times",
    )


class RefinementOutput(BaseModel):
    """Structured output for refinement iterations."""

    more_edits: bool = Field(description="Whether there are more edits to be made")
    suggestions: RedlineSuggestions = Field(
        description="Additional redline suggestions to be combined with existing ones"
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
    redline_suggestions: Optional[RedlineSuggestions]  # Generated redline suggestions


class RedlineState(TypedDict):
    # Input fields
    doc_id: str  # Base document ID
    reference_doc_ids: List[str]  # List of reference document IDs
    general_comments: str  # Instructions for this specific redline task
    reference_documents_comments: List[str]  # Comments for each reference document

    # Working fields (can be added as the graph evolves)
    base_document_content: str  # Content of the base document
    reference_documents_content: List[str]  # Content of reference documents
    structured_feedback: Optional[StructuredFeedback]  # Structured feedback from user

    # Output fields
    redline_plan: str  # Plan for the redline task
    clarification_questions: List[ClarificationQuestion]
    redline_suggestions: Optional[RedlineSuggestions]  # Generated redline suggestions

    # Refinement tracking fields
    refinement_iteration: Optional[int]  # Current refinement iteration count
    previous_redline_plan: Optional[str]  # Previous plan for revision
    more_refinement_needed: Optional[
        bool
    ]  # Whether more refinement iterations are needed
