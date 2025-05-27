redline_planner_instructions = """
You are an AI assistant specializing in redlining legal documents. Your role is to review the base document and instructions, then return a concise and structured output to guide the redlining process.

1. Overview and Plan
2. Clarification Questions

Here is a description of each:
- **Overview**: Write a brief summary (maximum 2 sentences) describing the purpose of the document and the key categories of edits to be made.
- **Plan**: Provide a high-level plan outlining how you will approach editing the document. This may include structural changes, clause-specific revisions, or references to precedent language.
- **Questions**: List clarifying questions that must be answered before proceeding with the redline. The user will respond in natural language, so feel free to ask simple or complex questions as needed.

Be precise, legally aware, and maintain a professional tone throughout.
"""

reference_doc_summary_template = """
Reference Document {doc_number}: {ref_id}
Comment: {ref_comment}

{ref_content}
"""

planning_prompt_template = """
TASK DETAILS:
General Instructions: {general_comments}

---
BASE DOCUMENT:

Base Document ID: {doc_id}
Base Document Content: 
{base_document_content}

---
REFERENCE DOCUMENTS:

{reference_docs_str}

---
Based on the above information, generate:
1. A comprehensive redline plan that outlines your approach to editing the document, including specific areas of focus and how you'll incorporate elements from the reference documents
2. Exactly {max_questions} clarifying questions that will help you better understand the requirements and produce a higher quality redlined document

The plan should be detailed enough to guide the actual redlining process while the questions should address any ambiguities or areas where additional guidance would be valuable.

Your thoughtful clarification questions should address:
1. The specific intent or priority areas for this specific redlining task
2. The most pertinent content from the reference documents to consider
3. Any specific content preferences for the redlined output
"""

structured_feedback_prompt_template = """
🎯 GENERATED REDLINE PLAN:
{redline_plan}

❓ CLARIFICATION QUESTIONS:
{questions_str}

---

Required:
- approval: boolean (true to approve, false to request changes)

Optional:
- specific_feedback: string with your comments or suggestions
- answer_to_clarification_questions: list of tuples with (question_number, answer)

Your feedback:"""
