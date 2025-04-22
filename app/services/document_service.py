# Document processing
# app/services/document_service.py
import json
import os
import shutil
from typing import List, Dict, Any, Optional
from fastapi import UploadFile, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import logging
from datetime import datetime
from app.models.database import College, Document, DocumentChunk, Image
from app.utils.chunking import DocumentProcessor
from app.utils.embeddings import EmbeddingManager
from app.utils.vectorstore import CollegeVectorStore
from app.core.config import settings
from langchain.docstore.document import Document as LangchainDocument

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.document_processor = DocumentProcessor()
        self.embedding_manager = EmbeddingManager()
    
    async def upload_document(self, file: UploadFile, college_id: int, background_tasks: BackgroundTasks) -> Document:
        """Upload a document and process it in the background"""
        # Check if college exists
        college = self.db.query(College).filter(College.id == college_id).first()
        if not college:
            raise HTTPException(status_code=404, detail=f"College with ID {college_id} not found")
        
        # Create college directory if it doesn't exist
        college_dir = os.path.join(settings.BASE_DATA_PATH, f"college_{college_id:03d}")
        documents_dir = os.path.join(college_dir, "documents")
        os.makedirs(documents_dir, exist_ok=True)
        
        # Save uploaded file
        file_path = os.path.join(documents_dir, file.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Create document in database
        db_document = Document(
            college_id=college_id,
            title=file.filename,
            file_path=file_path,
            mime_type=file.content_type,
            processed=False
        )
        
        self.db.add(db_document)
        self.db.commit()
        self.db.refresh(db_document)
        
        # Process document in background
        background_tasks.add_task(self.process_document, db_document.id)
        
        return db_document
    
    def process_document(self, document_id: int):
        """Process a document: extract text, chunk it, create embeddings, and store in vector store"""
        try:
            # Get document from database
            db_document = self.db.query(Document).filter(Document.id == document_id).first()
            if not db_document:
                logger.error(f"Document with ID {document_id} not found")
                return
            
            # Process file
            metadata = {
                "document_id": str(db_document.id),
                "title": db_document.title,
                "college_id": db_document.college_id,
                "source": db_document.file_path
            }
            
            chunks = self.document_processor.process_file(db_document.file_path, metadata)
            
            # Store chunks in database
            for i, chunk in enumerate(chunks):
                structured_data = self.document_processor.extract_structured_data(chunk.page_content)
                
                # Store as JSON string
                metadata_json = json.dumps({
                    **chunk.metadata,
                    "structured_data": structured_data
                })
                
                db_chunk = DocumentChunk(
                    document_id=db_document.id,
                    content=chunk.page_content,
                    chunk_index=i,
                    metadata=metadata_json
                )
                
                self.db.add(db_chunk)
            
            # Generate embeddings
            embeddings = self.embedding_manager.embed_documents(chunks)
            
            # Store in vector store
            vector_store = CollegeVectorStore.get_or_create(db_document.college_id)
            vector_store.add_documents(chunks, embeddings)
            
            # Update document status
            db_document.processed = True
            db_document.embedding_path = vector_store.vectorstore_dir
            db_document.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Successfully processed document {document_id} with {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            # Update document status to indicate error
            db_document = self.db.query(Document).filter(Document.id == document_id).first()
            if db_document:
                db_document.processed = False
                db_document.updated_at = datetime.utcnow()
                self.db.commit()
    
    # app/services/document_service.py (continued)
    async def upload_image(self, file: UploadFile, college_id: int, title: str, description: str = None, tags: str = None) -> Image:
        """Upload an image for a college"""
        # Check if college exists
        college = self.db.query(College).filter(College.id == college_id).first()
        if not college:
            raise HTTPException(status_code=404, detail=f"College with ID {college_id} not found")
        
        # Validate file extension
        _, file_ext = os.path.splitext(file.filename)
        if file_ext.lower() not in settings.SUPPORTED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported image format. Supported formats: {', '.join(settings.SUPPORTED_IMAGE_EXTENSIONS)}"
            )
        
        # Create image directory if it doesn't exist
        college_dir = os.path.join(settings.BASE_DATA_PATH, f"college_{college_id:03d}")
        images_dir = os.path.join(college_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() else "_" for c in title)
        filename = f"{safe_title}_{timestamp}{file_ext}"
        file_path = os.path.join(images_dir, filename)
        
        # Save uploaded file
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Create image in database
        db_image = Image(
            college_id=college_id,
            title=title,
            file_path=file_path,
            description=description,
            tags=tags
        )
        
        self.db.add(db_image)
        self.db.commit()
        self.db.refresh(db_image)
        
        return db_image
    
    def get_college_images(self, college_id: int, tag: Optional[str] = None) -> List[Image]:
        """Get all images for a college, optionally filtered by tag"""
        query = self.db.query(Image).filter(Image.college_id == college_id)
        
        if tag:
            # Filter images that have the tag (case-insensitive)
            query = query.filter(Image.tags.ilike(f"%{tag}%"))
        
        return query.all()
    
    def search_images_by_text(self, college_id: int, text: str) -> List[Image]:
        """Search images by title, description, or tags"""
        return self.db.query(Image).filter(
            Image.college_id == college_id,
            (
                Image.title.ilike(f"%{text}%") | 
                Image.description.ilike(f"%{text}%") | 
                Image.tags.ilike(f"%{text}%")
            )
        ).all()
    
    def delete_document(self, document_id: int) -> bool:
        """Delete a document and its associated chunks and embeddings"""
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return False
        
        # Delete chunks
        self.db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        
        # Delete from vector store
        try:
            vector_store = CollegeVectorStore.get_or_create(document.college_id)
            vector_store.delete_document(str(document_id))
        except Exception as e:
            logger.error(f"Error deleting document from vector store: {str(e)}")
        
        # Delete file if it exists
        if os.path.exists(document.file_path):
            try:
                os.remove(document.file_path)
            except Exception as e:
                logger.error(f"Error deleting file {document.file_path}: {str(e)}")
        
        # Delete document from database
        self.db.delete(document)
        self.db.commit()
        
        return True
    
    def delete_image(self, image_id: int) -> bool:
        """Delete an image"""
        image = self.db.query(Image).filter(Image.id == image_id).first()
        if not image:
            return False
        
        # Delete file if it exists
        if os.path.exists(image.file_path):
            try:
                os.remove(image.file_path)
            except Exception as e:
                logger.error(f"Error deleting file {image.file_path}: {str(e)}")
        
        # Delete image from database
        self.db.delete(image)
        self.db.commit()
        
        return True

