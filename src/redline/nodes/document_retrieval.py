"""Document retrieval node for getting raw text from documents."""

from typing import Dict, Any, List
from langchain_core.runnables import RunnableConfig

from src.redline.state import RedlineState
from src.redline.configuration import Configuration
from src.redline.utils import retrieve_document, validate_document_ids


async def retrieve_documents(
    state: RedlineState, config: RunnableConfig
) -> Dict[str, Any]:
    """Retrieve raw text content from base and reference documents.

    This node:
    1. Takes document IDs from the state
    2. Validates the document IDs
    3. Retrieves raw text content for the base document
    4. Retrieves raw text content for all reference documents
    5. Updates the state with the retrieved content

    Args:
        state: Current graph state containing document IDs
        config: Configuration for document APIs and retrieval settings

    Returns:
        Dict containing the document contents
    """

    # Get inputs from state
    doc_id = state["doc_id"]
    reference_doc_ids = state["reference_doc_ids"]

    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    document_api_config = configurable.document_api_config or {}

    # Validate document IDs
    all_doc_ids = [doc_id] + reference_doc_ids
    if not validate_document_ids(all_doc_ids):
        raise ValueError("Invalid document IDs provided")

    print(f"📄 Retrieving base document: {doc_id}")
    print(
        f"📚 Retrieving {len(reference_doc_ids)} reference documents: {', '.join(reference_doc_ids)}"
    )

    # Retrieve base document content
    try:
        base_document_content = await retrieve_document(doc_id, document_api_config)
        print(f"✅ Retrieved base document ({len(base_document_content)} characters)")
    except Exception as e:
        print(f"❌ Failed to retrieve base document {doc_id}: {e}")
        base_document_content = f"[ERROR: Could not retrieve document {doc_id}]"

    # Retrieve reference documents content
    reference_documents_content: List[str] = []
    for ref_id in reference_doc_ids:
        try:
            ref_content = await retrieve_document(ref_id, document_api_config)
            reference_documents_content.append(ref_content)
            print(
                f"✅ Retrieved reference document {ref_id} ({len(ref_content)} characters)"
            )
        except Exception as e:
            print(f"❌ Failed to retrieve reference document {ref_id}: {e}")
            reference_documents_content.append(
                f"[ERROR: Could not retrieve document {ref_id}]"
            )

    return {
        "base_document_content": base_document_content,
        "reference_documents_content": reference_documents_content,
    }
