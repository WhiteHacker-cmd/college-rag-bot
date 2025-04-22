# Pydantic schemas
# app/models/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# College schemas
class CollegeBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None

class CollegeCreate(CollegeBase):
    pass

class College(CollegeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Document schemas
class DocumentBase(BaseModel):
    title: str
    mime_type: str

class DocumentCreate(DocumentBase):
    college_id: int
    file_path: str

class Document(DocumentBase):
    id: int
    college_id: int
    file_path: str
    processed: bool
    embedding_path: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Image schemas
class ImageBase(BaseModel):
    title: str
    description: Optional[str] = None
    tags: Optional[str] = None

class ImageCreate(ImageBase):
    college_id: int
    file_path: str

class Image(ImageBase):
    id: int
    college_id: int
    file_path: str
    created_at: datetime

    class Config:
        from_attributes = True

# Chat schemas
class ChatRequest(BaseModel):
    college_id: int
    user_id: str
    query: str
    include_images: bool = False

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []
    images: Optional[List[Dict[str, Any]]] = None