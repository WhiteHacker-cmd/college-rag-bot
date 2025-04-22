# Vector store management
# app/utils/vectorstore.py
import os
import json
import pickle
import faiss
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from langchain.docstore.document import Document
import logging
import shutil
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)

class CollegeVectorStore:
    """Vector store for college-specific documents using FAISS"""
    
    def __init__(self, college_id: int):
        self.college_id = college_id
        self.college_dir = os.path.join(settings.BASE_DATA_PATH, f"college_{college_id:03d}")
        self.vectorstore_dir = os.path.join(self.college_dir, "vectorstore")
        self.index_path = os.path.join(self.vectorstore_dir, "faiss_index")
        self.metadata_path = os.path.join(self.vectorstore_dir, "metadata.pkl")
        self.documents_path = os.path.join(self.vectorstore_dir, "documents.pkl")
        
        # Create directories if they don't exist
        os.makedirs(self.vectorstore_dir, exist_ok=True)
        
        # Load or initialize index and metadata
        self.index = None
        self.metadata = []
        self.documents = []
        self._load_or_initialize()
    
    def _load_or_initialize(self):
        """Load existing index and metadata or initialize new ones"""
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path) and os.path.exists(self.documents_path):
            try:
                # Load index
                self.index = faiss.read_index(self.index_path)
                
                # Load metadata
                with open(self.metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
                
                # Load documents
                with open(self.documents_path, 'rb') as f:
                    self.documents = pickle.load(f)
                
                logger.info(f"Loaded vector store for college {self.college_id} with {self.index.ntotal} vectors")
            except Exception as e:
                logger.error(f"Error loading vector store: {str(e)}. Initializing new vector store.")
                self._initialize_new_index()
        else:
            logger.info(f"No existing vector store found for college {self.college_id}. Initializing new vector store.")
            self._initialize_new_index()
    
    def _initialize_new_index(self):
        """Initialize a new FAISS index"""
        self.metadata = []
        self.documents = []
        # We'll set the dimension when we add the first vectors
        self.index = None
    
    def add_documents(self, documents: List[Document], embeddings: List[List[float]]):
        """Add documents and their embeddings to the vector store"""
        if not documents or not embeddings:
            logger.warning("No documents or embeddings to add")
            return
        
        # Convert embeddings to numpy array
        embeddings_array = np.array(embeddings).astype('float32')
        
        # Initialize index if it doesn't exist
        if self.index is None:
            dimension = len(embeddings[0])
            self.index = faiss.IndexFlatL2(dimension)
            logger.info(f"Initialized new FAISS index with dimension {dimension}")
        
        # Add embeddings to index
        faiss.normalize_L2(embeddings_array)
        self.index.add(embeddings_array)
        
        # Add metadata and documents
        start_idx = len(self.metadata)
        for i, doc in enumerate(documents):
            doc_id = start_idx + i
            
            # Extract metadata
            meta = {
                "doc_id": doc_id,
                "chunk_index": doc.metadata.get("chunk_index", 0),
                "source": doc.metadata.get("source", "unknown"),
                "document_id": doc.metadata.get("document_id", "unknown"),
                "title": doc.metadata.get("title", ""),
                "timestamp": datetime.now().isoformat()
            }
            
            # Add any additional metadata
            for key, value in doc.metadata.items():
                if key not in meta:
                    meta[key] = value
            
            self.metadata.append(meta)
            self.documents.append(doc.page_content)
        
        # Save updated index and metadata
        self._save_index()
        logger.info(f"Added {len(documents)} documents to vector store. Total: {self.index.ntotal}")
    
    def _save_index(self):
        """Save the FAISS index and metadata to disk"""
        # Save index
        faiss.write_index(self.index, self.index_path)
        
        # Save metadata
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)
        
        # Save documents
        with open(self.documents_path, 'wb') as f:
            pickle.dump(self.documents, f)
        
        logger.info(f"Saved vector store for college {self.college_id} with {self.index.ntotal} vectors")
    
    def search(self, query_embedding: List[float], top_k: int = None) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Search for similar documents"""
        if self.index is None or self.index.ntotal == 0:
            logger.warning(f"No vectors in index for college {self.college_id}")
            return [], []
        
        if top_k is None:
            top_k = settings.TOP_K_RETRIEVAL
        
        # Convert query embedding to numpy array
        query_array = np.array([query_embedding]).astype('float32')
        faiss.normalize_L2(query_array)
        
        # Search index
        distances, indices = self.index.search(query_array, top_k)
        
        # Get documents and metadata
        results_documents = []
        results_metadata = []
        
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents) and idx >= 0:
                results_documents.append(self.documents[idx])
                
                # Add distance score to metadata
                meta = self.metadata[idx].copy()
                meta['distance'] = float(distances[0][i])
                meta['similarity'] = 1.0 - float(distances[0][i]) / 2.0  # Convert L2 distance to similarity
                
                results_metadata.append(meta)
        
        return results_documents, results_metadata
    
    def delete_document(self, document_id: str):
        """Delete a document and its chunks from the vector store"""
        # This is a simple implementation that rebuilds the index
        # A more efficient approach would be to use IDSelector to mark vectors for deletion
        if self.index is None or self.index.ntotal == 0:
            logger.warning(f"No vectors in index for college {self.college_id}")
            return
        
        # Find indices to keep
        indices_to_keep = []
        for i, meta in enumerate(self.metadata):
            if meta.get('document_id') != document_id:
                indices_to_keep.append(i)
        
        if len(indices_to_keep) == len(self.metadata):
            logger.warning(f"Document {document_id} not found in vector store")
            return
        
        # Extract vectors to keep
        if len(indices_to_keep) > 0:
            # Create a new index
            dimension = self.index.d
            new_index = faiss.IndexFlatL2(dimension)
            
            # Add vectors to keep
            vectors_to_keep = np.zeros((len(indices_to_keep), dimension), dtype='float32')
            for new_idx, old_idx in enumerate(indices_to_keep):
                vector = self.index.reconstruct(old_idx)
                vectors_to_keep[new_idx] = vector
            
            # Add to new index
            new_index.add(vectors_to_keep)
            
            # Update metadata and documents
            new_metadata = [self.metadata[i] for i in indices_to_keep]
            new_documents = [self.documents[i] for i in indices_to_keep]
            
            # Replace old index and metadata
            self.index = new_index
            self.metadata = new_metadata
            self.documents = new_documents
        else:
            # No documents left, reinitialize
            self._initialize_new_index()
        
        # Save updated index and metadata
        self._save_index()
        logger.info(f"Deleted document {document_id} from vector store. Remaining: {self.index.ntotal}")
    
    def clear(self):
        """Clear all vectors and metadata"""
        self._initialize_new_index()
        
        # Remove files
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
        if os.path.exists(self.metadata_path):
            os.remove(self.metadata_path)
        if os.path.exists(self.documents_path):
            os.remove(self.documents_path)
        
        logger.info(f"Cleared vector store for college {self.college_id}")
    
    @classmethod
    def get_or_create(cls, college_id: int):
        """Get an existing vector store or create a new one"""
        return cls(college_id)