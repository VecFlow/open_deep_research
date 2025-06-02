"""
Document Service for Legal Discovery Backend.
Handles file upload, processing, and integration with Weaviate vector database.
"""

import os
import uuid
import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, BinaryIO
from sqlalchemy.orm import Session

from fastapi import UploadFile, HTTPException

# Setup logging first
logger = logging.getLogger(__name__)

# Document processing imports
try:
    import weaviate
    WEAVIATE_AVAILABLE = True
    # Try different exception imports based on Weaviate version
    try:
        from weaviate.exceptions import WeaviateException
    except ImportError:
        try:
            from weaviate import WeaviateException
        except ImportError:
            # Fallback for newer versions
            WeaviateException = Exception
except ImportError:
    WEAVIATE_AVAILABLE = False
    WeaviateException = Exception
    logger.warning("Weaviate not available. Document search will be limited.")

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from .config import config
    from .models import DocumentDB
except ImportError:
    from config import config
    from models import DocumentDB

class DocumentService:
    """Service for handling document operations."""
    
    def __init__(self):
        self.weaviate_client: Optional[Any] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the document service."""
        try:
            # Create upload directory if it doesn't exist
            if not os.path.exists(config.upload_directory):
                os.makedirs(config.upload_directory, exist_ok=True)
                logger.info(f"Created upload directory: {config.upload_directory}")
            
            # Initialize Weaviate client if configured
            if config.weaviate_url and WEAVIATE_AVAILABLE:
                try:
                    # Initialize Weaviate v4 client
                    from urllib.parse import urlparse
                    parsed_url = urlparse(config.weaviate_url)
                    is_weaviate_cloud = '.weaviate.cloud' in parsed_url.hostname or '.weaviate.network' in parsed_url.hostname
                    
                    if is_weaviate_cloud:
                        # For Weaviate Cloud
                        self.weaviate_client = weaviate.use_async_with_weaviate_cloud(
                            cluster_url=config.weaviate_url,
                            auth_credentials=weaviate.auth.Auth.api_key(config.weaviate_api_key) if config.weaviate_api_key else None
                        )
                    else:
                        # For custom instances
                        http_host = parsed_url.hostname
                        http_port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 8080)
                        http_secure = parsed_url.scheme == 'https'
                        grpc_port = 50051
                        grpc_secure = http_secure
                        
                        self.weaviate_client = weaviate.use_async_with_custom(
                            http_host=http_host,
                            http_port=http_port,
                            http_secure=http_secure,
                            grpc_host=http_host,
                            grpc_port=grpc_port,
                            grpc_secure=grpc_secure,
                            auth_credentials=weaviate.auth.Auth.api_key(config.weaviate_api_key) if config.weaviate_api_key else None
                        )
                    
                    # Test connection (async context required for v4)
                    async with self.weaviate_client as client:
                        if client.is_ready():
                            logger.info("Weaviate client initialized successfully")
                            await self._ensure_document_schema()
                        else:
                            logger.warning("Weaviate client not ready")
                            self.weaviate_client = None
                        
                except Exception as e:
                    logger.error(f"Failed to initialize Weaviate client: {e}")
                    self.weaviate_client = None
            
            self._initialized = True
            logger.info("Document service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize document service: {e}")
            raise
    
    async def _ensure_document_schema(self) -> None:
        """Ensure the document schema exists in Weaviate v4."""
        try:
            if not self.weaviate_client:
                return
            
            collection_name = config.weaviate_collection_name or "Documents"
            
            async with self.weaviate_client as client:
                # Check if collection exists
                try:
                    collection = client.collections.get(collection_name)
                    logger.debug(f"Document collection already exists: {collection_name}")
                    return
                except Exception:
                    # Collection doesn't exist, create it
                    pass
                
                # Create document collection with v4 syntax
                from weaviate.classes.config import Configure, Property, DataType
                
                client.collections.create(
                    name=collection_name,
                    description="Legal documents for case analysis",
                    properties=[
                        Property(name="case_id", data_type=DataType.TEXT, description="ID of the case this document belongs to"),
                        Property(name="filename", data_type=DataType.TEXT, description="Original filename of the document"),
                        Property(name="content", data_type=DataType.TEXT, description="Extracted text content of the document"),
                        Property(name="file_type", data_type=DataType.TEXT, description="Type of the document file"),
                        Property(name="upload_date", data_type=DataType.DATE, description="Date when the document was uploaded"),
                        Property(name="page_count", data_type=DataType.INT, description="Number of pages in the document"),
                        Property(name="metadata", data_type=DataType.OBJECT, description="Additional metadata about the document")
                    ],
                    vectorizer_config=Configure.Vectorizer.text2vec_openai()  # Use OpenAI embeddings
                )
                
                logger.info(f"Created document collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to ensure document schema: {e}")
    
    async def upload_document(
        self,
        case_id: str,
        file: UploadFile,
        db_session: Session
    ) -> str:
        """Upload and process a document."""
        try:
            # Validate file
            if not file.filename:
                raise ValueError("No filename provided")
            
            file_extension = Path(file.filename).suffix.lower()
            if file_extension not in config.allowed_file_types:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            # Read file content
            file_content = await file.read()
            file_size = len(file_content)
            
            if file_size > config.max_file_size:
                raise ValueError(f"File too large: {file_size} bytes (max: {config.max_file_size})")
            
            # Generate document ID and file path
            document_id = f"doc-{str(uuid.uuid4())[:8]}"
            safe_filename = self._make_safe_filename(file.filename)
            file_path = os.path.join(
                config.upload_directory,
                case_id,
                f"{document_id}_{safe_filename}"
            )
            
            # Create case directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save file to disk
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            # Extract text content
            text_content = await self._extract_text_content(file_path, file_extension)
            
            # Store in Weaviate if available
            weaviate_id = None
            if self.weaviate_client and text_content:
                weaviate_id = await self._store_in_weaviate(
                    document_id=document_id,
                    case_id=case_id,
                    filename=file.filename,
                    content=text_content,
                    file_type=file_extension,
                    metadata={"file_size": file_size}
                )
            
            # Store in database
            document_db = DocumentDB(
                id=document_id,
                case_id=case_id,
                filename=file.filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_extension,
                weaviate_id=weaviate_id,
                uploaded_at=datetime.utcnow()
            )
            
            db_session.add(document_db)
            db_session.commit()
            
            logger.info(f"Uploaded document {document_id} for case {case_id}")
            return document_id
            
        except Exception as e:
            logger.error(f"Failed to upload document for case {case_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")
    
    async def _extract_text_content(self, file_path: str, file_extension: str) -> str:
        """Extract text content from a document file."""
        try:
            if file_extension == ".txt":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            
            elif file_extension == ".md":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            
            elif file_extension == ".pdf" and PDF_AVAILABLE:
                text_content = ""
                with open(file_path, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        text_content += page.extract_text() + "\n"
                return text_content
            
            elif file_extension == ".docx" and DOCX_AVAILABLE:
                doc = DocxDocument(file_path)
                text_content = ""
                for paragraph in doc.paragraphs:
                    text_content += paragraph.text + "\n"
                return text_content
            
            else:
                logger.warning(f"Unsupported file type for text extraction: {file_extension}")
                return ""
                
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            return ""
    
    async def _store_in_weaviate(
        self,
        document_id: str,
        case_id: str,
        filename: str,
        content: str,
        file_type: str,
        metadata: Dict[str, Any]
    ) -> Optional[str]:
        """Store document in Weaviate v4 vector database."""
        try:
            if not self.weaviate_client:
                return None
            
            collection_name = config.weaviate_collection_name or "Documents"
            
            # Prepare document data
            document_data = {
                "case_id": case_id,
                "filename": filename,
                "content": content,
                "file_type": file_type,
                "upload_date": datetime.utcnow(),  # v4 handles datetime objects
                "page_count": content.count("\n") + 1,  # Rough page estimate
                "metadata": metadata
            }
            
            # Create object in Weaviate v4
            async with self.weaviate_client as client:
                collection = client.collections.get(collection_name)
                result = collection.data.insert(
                    properties=document_data,
                    uuid=document_id
                )
            
            logger.debug(f"Stored document {document_id} in Weaviate")
            return document_id
            
        except Exception as e:
            logger.error(f"Failed to store document {document_id} in Weaviate: {e}")
            return None
    
    async def search_documents(
        self,
        case_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search documents using vector similarity with Weaviate v4."""
        try:
            if not self.weaviate_client:
                logger.warning("Weaviate not available for document search")
                return []
            
            collection_name = config.weaviate_collection_name or "Documents"
            
            # Perform vector search with v4 syntax
            async with self.weaviate_client as client:
                collection = client.collections.get(collection_name)
                
                # Import filter classes
                from weaviate.classes.query import Filter
                
                result = collection.query.near_text(
                    query=query,
                    limit=limit,
                    where=Filter.by_property("case_id").equal(case_id),
                    return_properties=["case_id", "filename", "content", "file_type", "upload_date"]
                )
                
                # Convert result format to match expected output
                documents = []
                for obj in result.objects:
                    doc_dict = obj.properties.copy()
                    doc_dict["_id"] = str(obj.uuid)
                    documents.append(doc_dict)
            
            logger.debug(f"Found {len(documents)} documents for query: {query}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to search documents for case {case_id}: {e}")
            return []
    
    async def delete_document(
        self,
        document_id: str,
        db_session: Session
    ) -> None:
        """Delete a document from filesystem, database, and Weaviate."""
        try:
            # Get document from database
            document_db = db_session.query(DocumentDB).filter(DocumentDB.id == document_id).first()
            if not document_db:
                raise ValueError(f"Document {document_id} not found")
            
            # Delete from filesystem
            if os.path.exists(document_db.file_path):
                os.remove(document_db.file_path)
                logger.debug(f"Deleted file: {document_db.file_path}")
            
            # Delete from Weaviate v4
            if self.weaviate_client and document_db.weaviate_id:
                try:
                    collection_name = config.weaviate_collection_name or "Documents"
                    async with self.weaviate_client as client:
                        collection = client.collections.get(collection_name)
                        collection.data.delete_by_id(document_db.weaviate_id)
                    logger.debug(f"Deleted document {document_id} from Weaviate")
                except Exception as e:
                    logger.warning(f"Failed to delete document {document_id} from Weaviate: {e}")
            
            # Delete from database
            db_session.delete(document_db)
            db_session.commit()
            
            logger.info(f"Deleted document {document_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise
    
    async def cleanup_analysis_documents(self, analysis_id: str) -> None:
        """Clean up documents associated with an analysis."""
        try:
            # This is a placeholder for cleaning up analysis-specific documents
            # In a full implementation, you might have analysis-specific document processing
            logger.debug(f"Cleaned up documents for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup documents for analysis {analysis_id}: {e}")
    
    def _make_safe_filename(self, filename: str) -> str:
        """Make a filename safe for filesystem storage."""
        # Remove or replace unsafe characters
        safe_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        safe_filename = "".join(c for c in filename if c in safe_chars)
        
        # Ensure it's not empty
        if not safe_filename:
            safe_filename = "document"
        
        # Limit length
        if len(safe_filename) > 100:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:95] + ext
        
        return safe_filename
    
    async def get_document_stats(self, case_id: str, db_session: Session) -> Dict[str, Any]:
        """Get document statistics for a case."""
        try:
            documents = db_session.query(DocumentDB).filter(DocumentDB.case_id == case_id).all()
            
            total_files = len(documents)
            total_size = sum(doc.file_size for doc in documents)
            file_types = {}
            
            for doc in documents:
                file_type = doc.file_type
                if file_type in file_types:
                    file_types[file_type] += 1
                else:
                    file_types[file_type] = 1
            
            return {
                "total_files": total_files,
                "total_size": total_size,
                "file_types": file_types,
                "has_searchable_content": bool(self.weaviate_client)
            }
            
        except Exception as e:
            logger.error(f"Failed to get document stats for case {case_id}: {e}")
            return {
                "total_files": 0,
                "total_size": 0,
                "file_types": {},
                "has_searchable_content": False
            }