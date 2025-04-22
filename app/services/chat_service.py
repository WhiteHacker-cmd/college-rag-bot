# Chat processing
# app/services/chat_service.py
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
import logging
from app.models.database import College, ChatHistory, Image
from app.utils.embeddings import EmbeddingManager
from app.utils.vectorstore import CollegeVectorStore
from app.services.llm_service import LLMService
from app.models.schemas import ChatRequest, ChatResponse
from app.core.config import settings

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_manager = EmbeddingManager()
        self.llm_service = LLMService()
    
    def get_chat_history(self, college_id: int, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Get recent chat history for a user and college"""
        history = self.db.query(ChatHistory).filter(
            ChatHistory.college_id == college_id,
            ChatHistory.user_id == user_id
        ).order_by(ChatHistory.timestamp.desc()).limit(limit).all()
        
        # Format history for LLM context
        formatted_history = []
        for msg in reversed(history):
            formatted_history.append({"role": "user", "content": msg.user_message})
            formatted_history.append({"role": "assistant", "content": msg.bot_response})
        
        return formatted_history
    
    def _get_relevant_images(self, college_id: int, query: str) -> List[Dict[str, Any]]:
        """Get relevant images based on query text matching"""
        # This is a simple implementation that matches query terms against image metadata
        # A more sophisticated approach would use embeddings for image retrieval
        query_terms = [term.lower() for term in query.split() if len(term) > 3]
        
        images = []
        for term in query_terms:
            results = self.db.query(Image).filter(
                Image.college_id == college_id,
                (
                    Image.title.ilike(f"%{term}%") | 
                    Image.description.ilike(f"%{term}%") | 
                    Image.tags.ilike(f"%{term}%")
                )
            ).all()
            
            for img in results:
                image_data = {
                    "id": img.id,
                    "title": img.title,
                    "file_path": img.file_path,
                    "description": img.description,
                    "tags": img.tags
                }
                
                # Add image only if not already in the list
                if not any(i["id"] == img.id for i in images):
                    images.append(image_data)
        
        return images
    
    async def process_query(self, chat_request: ChatRequest) -> ChatResponse:
        """Process a chat query, retrieve context, and generate response"""
        college_id = chat_request.college_id
        user_id = chat_request.user_id
        query = chat_request.query
        include_images = chat_request.include_images
        
        # Get college information
        college = self.db.query(College).filter(College.id == college_id).first()
        if not college:
            return ChatResponse(
                response="I'm sorry, but I couldn't find information for this college.",
                sources=[]
            )
        
        # Get recent chat history
        chat_history = self.get_chat_history(college_id, user_id, limit=5)
        
        # Generate query embedding
        query_embedding = self.embedding_manager.embed_query(query)
        
        # Retrieve relevant documents from vector store
        vector_store = CollegeVectorStore.get_or_create(college_id)
        documents, metadata = vector_store.search(query_embedding, top_k=settings.TOP_K_RETRIEVAL)
        
        # If no relevant documents found
        if not documents:
            response = f"I'm sorry, but I don't have enough information to answer your question about {college.name}. Please try asking something else or contact the college directly."
            return ChatResponse(
                response=response,
                sources=[]
            )
        
        # Get relevant images if requested
        images = None
        if include_images:
            images = self._get_relevant_images(college_id, query)
        
        # Generate response
        response_text = self.llm_service.generate_response(
            query=query,
            documents=documents,
            metadata=metadata,
            college_name=college.name,
            chat_history=chat_history,
            images=images
        )
        
        # Store chat in history
        chat_entry = ChatHistory(
            college_id=college_id,
            user_id=user_id,
            user_message=query,
            bot_response=response_text
        )
        self.db.add(chat_entry)
        self.db.commit()
        
        # Format metadata for response
        sources = []
        for meta in metadata:
            source_info = {
                "title": meta.get("title", "Unknown"),
                "source": meta.get("source", "Unknown"),
                "similarity": meta.get("similarity", 0.0)
            }
            sources.append(source_info)
        
        # Prepare image data for response
        image_data = None
        if images:
            image_data = []
            for img in images:
                image_info = {
                    "title": img.get("title", ""),
                    "description": img.get("description", ""),
                    "file_path": img.get("file_path", "")
                }
                image_data.append(image_info)
        
        return ChatResponse(
            response=response_text,
            sources=sources,
            images=image_data
        )