# Text chunking utilities
# app/utils/chunking.py
import os
import re
from typing import List, Dict, Any, Tuple, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader, 
    PyPDFLoader, 
    Docx2txtLoader, 
    CSVLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader  # Added Markdown loader
)
from langchain.docstore.document import Document as LangchainDocument
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
    def get_loader(self, file_path: str):
        """Return the appropriate document loader based on file extension"""
        extension = os.path.splitext(file_path)[1].lower()
        
        if extension == '.pdf':
            return PyPDFLoader(file_path)
        elif extension in ['.docx', '.doc']:
            return Docx2txtLoader(file_path)
        elif extension == '.txt':
            return TextLoader(file_path)
        elif extension == '.csv':
            return CSVLoader(file_path)
        elif extension in ['.html', '.htm']:
            return UnstructuredHTMLLoader(file_path)
        elif extension == '.md':
            return UnstructuredMarkdownLoader(file_path)  # Added Markdown support
        else:
            raise ValueError(f"Unsupported file type: {extension}")
    
    def process_file(self, file_path: str, metadata: Dict[str, Any] = None) -> List[LangchainDocument]:
        """Process a file and split it into chunks"""
        try:
            loader = self.get_loader(file_path)
            documents = loader.load()
            
            # Add metadata to each document
            if metadata:
                for doc in documents:
                    doc.metadata.update(metadata)
            
            # Special handling for markdown files to maintain structure
            extension = os.path.splitext(file_path)[1].lower()
            if extension == '.md':
                # Adjust separator weights for markdown to better preserve structure
                md_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " ", ""]
                )
                chunks = md_splitter.split_documents(documents)
            else:
                # Use the default splitter for other document types
                chunks = self.text_splitter.split_documents(documents)
            
            # Add chunk index to metadata
            for i, chunk in enumerate(chunks):
                chunk.metadata['chunk_index'] = i
                
                # For markdown files, try to extract header information to enhance metadata
                if extension == '.md':
                    chunk.metadata.update(self.extract_markdown_headers(chunk.page_content))
            
            return chunks
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            raise
    
    def extract_structured_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from text using regex patterns"""
        structured_data = {}
        
        # Extract dates (format: MM/DD/YYYY or Month DD, YYYY)
        date_pattern = r'(\d{1,2}/\d{1,2}/\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, \d{4})'
        dates = re.findall(date_pattern, text)
        if dates:
            structured_data['dates'] = dates
        
        # Extract emails
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        if emails:
            structured_data['emails'] = emails
        
        # Extract phone numbers
        phone_pattern = r'(\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'
        phones = re.findall(phone_pattern, text)
        if phones:
            structured_data['phones'] = phones
            
        # Extract URLs
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, text)
        if urls:
            structured_data['urls'] = urls
        
        return structured_data
    
    def extract_markdown_headers(self, text: str) -> Dict[str, Any]:
        """Extract header information from markdown text"""
        header_info = {}
        
        # Extract main header (h1) if present
        h1_pattern = r'^# (.+)$'
        h1_match = re.search(h1_pattern, text, re.MULTILINE)
        if h1_match:
            header_info['title'] = h1_match.group(1).strip()
        
        # Extract secondary headers (h2)
        h2_pattern = r'^## (.+)$'
        h2_matches = re.findall(h2_pattern, text, re.MULTILINE)
        if h2_matches:
            header_info['sections'] = h2_matches
        
        # Extract YAML frontmatter if present
        frontmatter_pattern = r'---\n(.*?)\n---'
        frontmatter_match = re.search(frontmatter_pattern, text, re.DOTALL)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            # Extract key-value pairs from frontmatter
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    header_info[key.strip()] = value.strip()
        
        return header_info