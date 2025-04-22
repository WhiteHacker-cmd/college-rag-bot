# app/routers/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any
from datetime import timedelta
import logging

from app.core.security import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    Token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_active_user,
    get_admin_user
)
from app.models.database import get_db, User
from app.models.schemas import UserCreate, UserCreateAdmin, User as UserSchema

router = APIRouter(tags=["authentication"])
logger = logging.getLogger(__name__)

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticate user and generate JWT token"""
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserSchema)
async def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new regular user"""
    # Check if username already exists
    db_user = db.query(User).filter(User.username == user_in.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user (always with user role from this endpoint)
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_password,
        role="user"  # Force role to be user for this endpoint
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"New user registered: {user_in.username}")
    return db_user

@router.post("/register/admin", response_model=UserSchema)
async def register_admin(
    admin_in: UserCreateAdmin,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_admin_user)
):
    """Register a new admin user (only existing admins can create new admins)"""
    # Check if username already exists
    db_user = db.query(User).filter(User.username == admin_in.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    db_user = db.query(User).filter(User.email == admin_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new admin
    hashed_password = get_password_hash(admin_in.password)
    db_user = User(
        username=admin_in.username,
        email=admin_in.email,
        hashed_password=hashed_password,
        role="admin"
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"New admin registered: {admin_in.username} (created by admin: {current_admin['username']})")
    return db_user

@router.post("/initialize-admin", response_model=UserSchema)
async def initialize_first_admin(
    admin_in: UserCreateAdmin,
    db: Session = Depends(get_db)
):
    """
    Initialize the first admin user if no users exist in the system.
    This endpoint is only available when the database is empty.
    """
    # Check if any users exist
    user_count = db.query(User).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin already initialized. Use regular admin registration."
        )
    
    # Create first admin
    hashed_password = get_password_hash(admin_in.password)
    db_user = User(
        username=admin_in.username,
        email=admin_in.email,
        hashed_password=hashed_password,
        role="admin"
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"First admin initialized: {admin_in.username}")
    return db_user