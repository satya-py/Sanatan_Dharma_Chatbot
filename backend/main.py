import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .utils.logger import logger

# Import API Routers
from .api.chat import router as chat_router
from .api.voice import router as voice_router
from .api.scriptures import router as scriptures_router
from .api.database_api import router as db_router
from .api.admin import router as admin_router

app = FastAPI(
    title="Sanatana Dharma AI Chatbot API",
    description="Production RAG Backend for ISKCON temples and devotees using LangGraph, LangChain, and FastAPI.",
    version="1.0.0"
)

# Configure CORS Middleware for Frontend React App (typically runs on 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Actions
@app.on_event("startup")
def on_startup():
    logger.info("Initializing Sanatana Dharma Chatbot backend...")
    
    # 1. Initialize SQLite Database Tables
    try:
        init_db()
        logger.info("SQLite database tables successfully initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        
    # 2. Create static directories if they don't exist
    static_dir = Path(__file__).resolve().parent / "static"
    (static_dir / "audio").mkdir(parents=True, exist_ok=True)
    (static_dir / "uploads").mkdir(parents=True, exist_ok=True)
    logger.info(f"Static media directories ensured at {static_dir}")
    
    # Pre-load embedding manager and retrievers to warm up GPU memory
    from .embeddings.models import embedding_manager
    from .retrievers.gita_retriever import gita_retriever_instance
    from .retrievers.scripture_retriever import scripture_retriever_instance
    
    logger.info("Warm-up complete. Models loaded successfully onto GPU/CPU.")

# Register API Routers
app.include_router(chat_router)
app.include_router(voice_router)
app.include_router(scriptures_router)
app.include_router(db_router)
app.include_router(admin_router)

# Mount Static Files to serve audio MP3s and uploads
static_path = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.get("/api/health", tags=["System Utility"])
def health_check():
    """
    Service health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "Sanatana Dharma AI Chatbot Backend",
        "api_version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    # Start the server locally
    uvicorn.run(
        "backend.main:app", 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=False
    )
