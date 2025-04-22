# Admin endpoints for document management
# app/routers/admin_router.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from app.models.database import get_db
from app.models.schemas import College, CollegeCreate, Document, DocumentCreate, Image, ImageCreate
from app.services.document_service import DocumentService
from app.core.security import get_admin_user
from app.core.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])

# College endpoints
@router.post("/colleges", response_model=College)
async def create_college(
    college: CollegeCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user)
):
    """Create a new college"""
    # Check if college with same code already exists
    existing = db.query(College).filter(College.code == college.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="College with this code already exists")
    
    db_college = College(**college.dict())
    db.add(db_college)
    db.commit()
    db.refresh(db_college)
    
    # Create college directory structure
    college_dir = os.path.join(settings.BASE_DATA_PATH, f"college_{db_college.id:03d}")
    os.makedirs(os.path.join(college_dir, "documents"), exist_ok=True)
    os.makedirs(os.path.join(college_dir, "images"), exist_ok=True)
    os.makedirs(os.path.join(college_dir, "vectorstore"), exist_ok=True)
    
    return db_college

@router.get("/colleges", response_model=List[College])
async def get_colleges(
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user)
):
    """Get all colleges"""
    return db.query(College).all()

@router.get("/colleges/{college_id}", response_model=College)
async def get_college(
    college_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user)
):
    """Get a specific college"""
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    return college

# Document endpoints
@router.post("/documents", response_model=Document)
async def upload_document(
    file: UploadFile = File(...),
    college_id: int = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user)
):
    """Upload a document for a specific college"""
    document_service = DocumentService(db)
    return await document_service.upload_document(file, college_id, background_tasks)

@router.get("/documents/{college_id}", response_model=List[Document])
async def get_college_documents(
    college_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user)
):
    """Get all documents for a specific college"""
    documents = db.query(Document).filter(Document.college_id == college_id).all()
    return documents

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user)
):
    """Delete a document"""
    document_service = DocumentService(db)
    success = document_service.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}

# Image endpoints
@router.post("/images", response_model=Image)
async def upload_image(
    file: UploadFile = File(...),
    college_id: int = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user)
):
    """Upload an image for a specific college"""
    document_service = DocumentService(db)
    return await document_service.upload_image(file, college_id, title, description, tags)

@router.get("/images/{college_id}", response_model=List[Image])
async def get_college_images(
    college_id: int,
    tag: Optional[str] = None,
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user)
):
    """Get all images for a specific college, optionally filtered by tag"""
    document_service = DocumentService(db)
    return document_service.get_college_images(college_id, tag)

@router.get("/images/file/{image_id}")
async def get_image_file(
    image_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user)
):
    """Get image file"""
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image or not os.path.exists(image.file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(image.file_path)

@router.delete("/images/{image_id}")
async def delete_image(
    image_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user)
):
    """Delete an image"""
    document_service = DocumentService(db)
    success = document_service.delete_image(image_id)
    if not success:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"message": "Image deleted successfully"}