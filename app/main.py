# FastAPI main application
# app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
import os
import logging
from app.core.config import settings
from app.models.database import create_tables
from app.routers import chat_router, admin_router, auth_router
from app.core.security import get_current_active_user

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="RAG Chatbot API for multiple colleges",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router.router)
app.include_router(chat_router.router, prefix=settings.API_PREFIX)
app.include_router(
    admin_router.router,
    prefix=f"{settings.API_PREFIX}/admin",
    dependencies=[Depends(get_current_active_user)],
    tags=["admin"]
)

# Mount static files
os.makedirs(settings.BASE_DATA_PATH, exist_ok=True)
app.mount("/static", StaticFiles(directory=settings.BASE_DATA_PATH), name="static")

@app.get("/", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "version": "1.0.0"
    }

@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    create_tables()
    logging.info("Database tables created")
    logging.info(f"Application {settings.APP_NAME} started")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)