# Authentication and authorization
# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os

from app.models.database import get_db, User

# Generate a secret key for JWT
# In production, set this via environment variable
SECRET_KEY = os.getenv("SECRET_KEY", "4f3eaf58b0309c3bb740df3f30e3d8f529c9a9e716b5decf9d1341f988ad0d15")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# For backwards compatibility during transition
fake_users_db = {
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$WrYbDl0U9s3J5VC/kIVM7O2ACW8Y2LeA0UwMF/0hT.W8h1SvUBTui",  # "adminpassword"
        "role": "admin"
    },
    "user": {
        "username": "user",
        "hashed_password": "$2b$12$WrYbDl0U9s3J5VC/kIVM7O2ACW8Y2LeA0UwMF/0hT.W8h1SvUBTui",  # "userpassword"
        "role": "user"
    }
}

def verify_password(plain_password, hashed_password):
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Generate password hash"""
    return pwd_context.hash(password)

def get_user(username: str, db: Session):
    """Get user from database"""
    # First try the database
    db_user = db.query(User).filter(User.username == username).first()
    if db_user:
        return db_user
    
    # Fall back to fake_users_db during transition
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return user_dict
    
    return None

def authenticate_user(username: str, password: str, db: Session):
    """Authenticate user with username and password"""
    user = get_user(username, db)
    if not user:
        return False
    
    # Handle both DB model and dict cases
    if hasattr(user, 'hashed_password'):
        # DB user model
        if not verify_password(password, user.hashed_password):
            return False
    else:
        # Dict from fake_users_db
        if not verify_password(password, user["hashed_password"]):
            return False
    
    return user

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None):
    """Create JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get current user from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=payload.get("role"))
    except JWTError:
        raise credentials_exception
    
    user = get_user(username=token_data.username, db=db)
    if user is None:
        raise credentials_exception
    
    # Convert DB model to dict if needed
    if hasattr(user, 'username'):
        # It's a DB model, convert to dict
        user_dict = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active
        }
        return user_dict
    
    # It's already a dict (from fake_users_db)
    return user

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    """Get current active user"""
    if hasattr(current_user, 'is_active'):
        if not current_user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
    elif isinstance(current_user, dict) and 'is_active' in current_user:
        if not current_user['is_active']:
            raise HTTPException(status_code=400, detail="Inactive user")
    
    return current_user

def get_admin_user(current_user: dict = Depends(get_current_user)):
    """Check if user is admin"""
    # Handle both DB model and dict cases
    role = current_user.get("role") if isinstance(current_user, dict) else getattr(current_user, "role", None)
    
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user