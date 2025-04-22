# Embedding utilities
# app/utils/embeddings.py
import os
from typing import List, Dict, Any, Union
from langchain_community.embeddings import HuggingFaceEmbeddings, OllamaEmbeddings
from langchain.docstore.document import Document
import numpy as np
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingManager:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        """Initialize the embedding model"""
        try:
            # Try to use Ollama for embeddings first
            self.embeddings = OllamaEmbeddings(
                model="llama3.1",
                base_url=settings.OLLAMA_BASE_URL
            )
            logger.info("Using Ollama embeddings")
        except Exception as e:
            logger.warning(f"Failed to initialize Ollama embeddings: {str(e)}. Falling back to HuggingFace embeddings.")
            # Fall back to HuggingFace embeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info(f"Using HuggingFace embeddings with model {model_name}")
    
    def embed_documents(self, documents: List[Document]) -> List[List[float]]:
        """Generate embeddings for a list of documents"""
        texts = [doc.page_content for doc in documents]
        return self.embeddings.embed_documents(texts)
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a query string"""
        return self.embeddings.embed_query(query)
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    @staticmethod
    def batch_cosine_similarity(query_vector: List[float], document_vectors: List[List[float]]) -> List[float]:
        """Calculate cosine similarity between a query vector and multiple document vectors"""
        query_vector = np.array(query_vector)
        document_vectors = np.array(document_vectors)
        
        # Normalize query vector
        query_norm = np.linalg.norm(query_vector)
        if query_norm > 0:
            query_vector = query_vector / query_norm
            
        # Normalize document vectors
        doc_norms = np.linalg.norm(document_vectors, axis=1, keepdims=True)
        doc_norms[doc_norms == 0] = 1
        normalized_docs = document_vectors / doc_norms
        
        # Calculate similarities
        similarities = np.dot(normalized_docs, query_vector)
        return similarities.tolist()