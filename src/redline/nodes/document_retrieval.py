"""Document retrieval node for getting raw text from documents."""

import pickle
from typing import Dict, Any, List
import boto3
from langchain_core.runnables import RunnableConfig

from src.redline.state import RedlineState
from src.redline.configuration import Configuration

# Initialize S3 client
s3_client = boto3.client("s3")


async def retrieve_document(doc_id: str, bucket_name: str = None) -> str:
    """Retrieve document content by ID and return full text.

    Args:
        doc_id: Document identifier
        bucket_name: S3 bucket name for document retrieval

    Returns:
        Document content as string
    """
    try:
        # Try pickled documents first
        object_key = f"{doc_id}_serialized_data.pkl"

        try:
            obj = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            body = obj["Body"].read()
            docs = pickle.loads(body)
            # Get full text from documents
            return "".join([doc.page_content for doc in docs])
        except Exception:
            # Fallback to plain text
            object_key = f"{doc_id}_processed.txt"
            obj = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            body = obj["Body"].read()
            return body.decode("utf-8")

    except Exception as e:
        return f"[ERROR: Could not retrieve document {doc_id}: {e}]"


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

    # Get S3 bucket name from configuration
    configuration = Configuration.from_runnable_config(config)
    bucket_name = configuration.s3_bucket_name

    # Retrieve base document content
    try:
        base_document_content = await retrieve_document(doc_id, bucket_name)
        print(f"✅ Retrieved base document ({len(base_document_content)} characters)")
    except Exception as e:
        print(f"❌ Failed to retrieve base document {doc_id}: {e}")
        base_document_content = f"[ERROR: Could not retrieve document {doc_id}]"

    # Retrieve reference documents content
    reference_documents_content: List[str] = []
    for ref_id in reference_doc_ids:
        try:
            ref_content = await retrieve_document(ref_id, bucket_name)
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
