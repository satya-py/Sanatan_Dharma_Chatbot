import os
import torch
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Dict, Any

from ..database import get_db, ChatSession, ChatMessage, Bookmark, Feedback
from ..config import settings
from ..retrievers.gita_retriever import gita_retriever_instance
from ..retrievers.scripture_retriever import scripture_retriever_instance
from ..utils.logger import LOG_FILE_PATH

router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard API"])

@router.get("/metrics")
def get_admin_metrics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Retrieves system health, vector database size, and relational database row counts.
    """
    # 1. Relational Database Counts
    try:
        session_count = db.query(ChatSession).count()
        message_count = db.query(ChatMessage).count()
        bookmark_count = db.query(Bookmark).count()
        feedback_count = db.query(Feedback).count()
    except Exception as e:
        print(f"[AdminAPI] Error reading database statistics: {e}")
        session_count = message_count = bookmark_count = feedback_count = 0

    # 2. Vector Database Stats
    gita_vectors = 0
    scripture_vectors = 0
    if gita_retriever_instance.vector_store:
        gita_vectors = gita_retriever_instance.vector_store.index.ntotal
    if scripture_retriever_instance.vector_store:
        scripture_vectors = scripture_retriever_instance.vector_store.index.ntotal
        
    # 3. Environment Key Setup Status
    keys_status = {
        "google_gemini": bool(settings.GOOGLE_API_KEY),
        "groq": bool(settings.GROQ_API_KEY),
        "tavily": bool(settings.TAVILY_API_KEY),
        "assemblyai": bool(settings.ASSEMBLYAI_API_KEY)
    }
    
    # 4. System / GPU hardware health
    gpu_available = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if gpu_available else "N/A"
    
    # 5. Database File Size
    db_file_path = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
    db_size_bytes = 0
    if db_file_path.exists():
        db_size_bytes = db_file_path.stat().st_size
        
    return {
        "db_stats": {
            "sessions": session_count,
            "messages": message_count,
            "bookmarks": bookmark_count,
            "feedback": feedback_count,
            "db_size_kb": round(db_size_bytes / 1024, 2)
        },
        "vector_stats": {
            "gita_index_size": gita_vectors,
            "scriptures_index_size": scripture_vectors
        },
        "system_health": {
            "gpu_acceleration": gpu_available,
            "gpu_device_name": gpu_name,
            "pytorch_version": torch.__version__
        },
        "keys_configured": keys_status
    }

@router.get("/logs")
def get_system_logs(lines: int = 100) -> Dict[str, Any]:
    """
    Reads the tail of the backend execution log file.
    """
    log_path = LOG_FILE_PATH
    if not log_path.exists():
        return {"logs": "Log file not found."}
        
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            
        # Get last 'lines' rows
        tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return {
            "logs": "".join(tail_lines),
            "total_lines": len(all_lines)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")
