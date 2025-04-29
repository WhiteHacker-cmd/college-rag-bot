# Application configuration
# app/core/config.py
import os
from pydantic_settings import BaseSettings
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    APP_NAME: str = "College RAG Chatbot"
    API_PREFIX: str = "/api"
    DEBUG: bool = True
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./college_chatbot.db")
    
    # LLM settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    # LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3.1:8b")

    # In app/core/config.py
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    # Update LLM_MODEL to use a Groq model like "llama3-70b-8192" or "mixtral-8x7b-32768"
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3-70b-8192")
    
    # Path settings
    BASE_DATA_PATH: str = os.getenv("BASE_DATA_PATH", "./data/colleges")
    
    # Chunking settings
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    
    # Retrieval settings
    TOP_K_RETRIEVAL: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    
    # Image settings
    SUPPORTED_IMAGE_EXTENSIONS: list = [".jpg", ".jpeg", ".png", ".gif"]
    
    class Config:
        env_file = ".env"

settings = Settings()