import os
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
    try:
        if gita_retriever_instance.vector_store:
            gita_vectors = gita_retriever_instance.vector_store.index.ntotal
        if scripture_retriever_instance.vector_store:
            scripture_vectors = scripture_retriever_instance.vector_store.index.ntotal
    except Exception as e:
        print(f"[AdminAPI] Error reading vector store statistics: {e}")
        
    # 3. Environment Key Setup Status
    keys_status = {
        "google_gemini": bool(settings.GOOGLE_API_KEY),
        "groq": bool(settings.GROQ_API_KEY),
        "tavily": bool(settings.TAVILY_API_KEY),
        "assemblyai": bool(settings.ASSEMBLYAI_API_KEY)
    }
    
    # 4. System / GPU hardware health
    # torch is optional: the default "onnx" embedding backend does not install it.
    gpu_available = False
    gpu_name = "N/A"
    torch_version = "not installed"
    try:
        import torch

        torch_version = torch.__version__
        gpu_available = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if gpu_available else "N/A"
    except ImportError:
        gpu_name = "N/A (torch not installed; embedding backend = onnx)"
    
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
            "pytorch_version": torch_version,
            "embedding_backend": settings.EMBEDDING_BACKEND,
            "rerank_enabled": settings.ENABLE_RERANK,
            "bm25_enabled": settings.ENABLE_BM25
        },
        "keys_configured": keys_status
    }

@router.get("/logs")
def get_system_logs(lines: int = 100) -> Dict[str, Any]:
    """
    Reads the tail of the backend execution log file.
    """
    log_path = LOG_FILE_PATH
    if log_path is None or not log_path.exists():
        return {
            "logs": "File logging is disabled (LOG_TO_FILE=false). "
                    "Logs are written to stdout; view them in the Render dashboard."
        }
        
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


@router.get("/check-keys")
def check_api_keys() -> Dict[str, Any]:
    """
    Actively test each API key against its provider.

    /api/health only reports whether a key is *present*, which cannot
    distinguish a correct key from a truncated or mis-pasted one -- both look
    configured, and the failure only shows up as a 401 in the middle of an
    answer. This makes one cheap call per provider and says which are actually
    accepted.

    The response never contains a key. It reports length and prefix only, which
    is what identifies a truncated or swapped paste without disclosing the
    secret itself.
    """
    import requests

    def fingerprint(key: str) -> Dict[str, Any]:
        return {
            "configured": bool(key),
            "length": len(key),
            "prefix": key[:4] if key else None,
            "looks_padded": bool(key) and key != key.strip(),
        }

    results: Dict[str, Any] = {}

    checks = [
        (
            "groq",
            settings.GROQ_API_KEY,
            lambda k: requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {k}"},
                json={
                    "model": "openai/gpt-oss-120b",
                    "messages": [{"role": "user", "content": "ok"}],
                    "max_tokens": 1,
                },
                timeout=20,
            ),
        ),
        (
            "google_gemini",
            settings.GOOGLE_API_KEY,
            lambda k: requests.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                headers={"x-goog-api-key": k},
                timeout=20,
            ),
        ),
        (
            "tavily",
            settings.TAVILY_API_KEY,
            lambda k: requests.post(
                "https://api.tavily.com/search",
                json={"api_key": k, "query": "test", "max_results": 1},
                timeout=20,
            ),
        ),
        (
            "assemblyai",
            settings.ASSEMBLYAI_API_KEY,
            lambda k: requests.get(
                "https://api.assemblyai.com/v2/transcript?limit=1",
                headers={"authorization": k},
                timeout=20,
            ),
        ),
    ]

    for name, key, call in checks:
        info = fingerprint(key)
        if not key:
            info["status"] = "missing"
            results[name] = info
            continue
        try:
            resp = call(key)
            info["http_status"] = resp.status_code
            if resp.status_code == 200:
                info["status"] = "ok"
            elif resp.status_code in (401, 403):
                info["status"] = "rejected"
                info["hint"] = "Key is wrong, revoked, or was pasted with extra characters."
            elif resp.status_code == 429:
                info["status"] = "rate_limited"
                info["hint"] = "Key is valid but the quota is currently exhausted."
            else:
                info["status"] = "error"
                info["detail"] = resp.text[:200]
        except Exception as e:
            info["status"] = "unreachable"
            info["detail"] = str(e)[:200]
        results[name] = info

    return {"keys": results}
