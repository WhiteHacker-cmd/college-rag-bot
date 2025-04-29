# Chat endpoints
# app/routers/chat_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.database import get_db
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.core.security import get_current_active_user

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/query", response_model=ChatResponse)
async def process_chat_query(
    chat_request: ChatRequest,
    db: Session = Depends(get_db),
    # _: dict = Depends(get_current_active_user)
):
    """Process a chat query and return a response with relevant context"""
    chat_service = ChatService(db)
    response = await chat_service.process_query(chat_request)
    return response

@router.get("/history/{college_id}/{user_id}", response_model=List[dict])
async def get_chat_history(
    college_id: int,
    user_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_active_user)
):
    """Get chat history for a specific user and college"""
    chat_service = ChatService(db)
    history = chat_service.get_chat_history(college_id, user_id, limit)
    return history