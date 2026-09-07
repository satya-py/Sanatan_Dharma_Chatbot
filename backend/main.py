import os
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path

# Log lines carry Devanagari, Tamil, and typographic punctuation. On a console
# that is not UTF-8 (Windows defaults to cp1252) a print() inside a request
# handler raises UnicodeEncodeError and turns a working answer into a 500.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

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

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _warm_up():
    """Build the retrievers off the critical path. Failures are logged, not fatal."""
    from .retrievers.gita_retriever import gita_retriever_instance
    from .retrievers.scripture_retriever import scripture_retriever_instance

    for name, proxy in (
        ("gita index", gita_retriever_instance),
        ("scripture index", scripture_retriever_instance),
    ):
        try:
            proxy.lazy_resolve()
            logger.info(f"Warm-up: {name} ready.")
        except Exception as e:
            logger.error(f"Warm-up: {name} failed: {e}")
    logger.info("Warm-up complete.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Sanatana Dharma Chatbot backend...")

    # 1. Initialize SQLite Database Tables
    try:
        init_db()
        logger.info("Database tables successfully initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    # 2. Create static directories if they don't exist
    (STATIC_DIR / "audio").mkdir(parents=True, exist_ok=True)
    (STATIC_DIR / "uploads").mkdir(parents=True, exist_ok=True)
    logger.info(f"Static media directories ensured at {STATIC_DIR}")

    # 3. Report configuration so a misconfigured deploy is obvious in the logs.
    missing = settings.missing_keys()
    if missing:
        logger.warning(f"Missing API keys (set these in the dashboard): {missing}")
    logger.info(
        f"Embedding backend={settings.EMBEDDING_BACKEND} "
        f"rerank={settings.ENABLE_RERANK} bm25={settings.ENABLE_BM25} "
        f"multiquery={settings.ENABLE_MULTIQUERY}"
    )

    # 4. Warm the models up on a background thread.
    #
    #    uvicorn does not bind its listening socket until this handler returns,
    #    so doing the work here keeps the port closed for as long as it takes to
    #    download ~210 MB of ONNX weights and map a 60 MB FAISS index. On a small
    #    instance that overruns the platform's port scan and the deploy is killed
    #    with "no open ports detected". Returning immediately lets the port open;
    #    the models finish loading a few seconds later, and any request that
    #    arrives first simply blocks on the same lock instead of failing.
    threading.Thread(target=_warm_up, name="warmup", daemon=True).start()

    yield

    logger.info("Shutting down Sanatana Dharma Chatbot backend.")


app = FastAPI(
    title="Sanatana Dharma AI Chatbot API",
    description="Production RAG Backend for ISKCON temples and devotees using LangGraph, LangChain, and FastAPI.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for the React frontend.
# Note: the CORS spec forbids credentials together with a "*" origin, and
# browsers silently reject such responses. So allow_credentials is only
# switched on when an explicit origin list is configured.
_origins = settings.cors_origin_list
_allow_credentials = "*" not in _origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(chat_router)
app.include_router(voice_router)
app.include_router(scriptures_router)
app.include_router(db_router)
app.include_router(admin_router)

# Mount Static Files to serve audio MP3s and uploads.
# Created up front because StaticFiles validates the directory at mount time,
# which happens before the lifespan handler runs.
(STATIC_DIR / "audio").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "uploads").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", tags=["System Utility"])
def root():
    return {
        "service": "Sanatana Dharma AI Chatbot Backend",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health", tags=["System Utility"])
def health_check():
    """
    Service health check endpoint.
    Also reports which subsystems came up, so a partial deploy is diagnosable
    without shelling into the container.
    """
    from .retrievers.gita_retriever import gita_retriever_instance
    from .retrievers.scripture_retriever import scripture_retriever_instance

    def describe(proxy):
        # Must not touch the proxy's attributes: that would force the models to
        # load and turn the platform's health probe into a multi-minute request.
        if not proxy.lazy_initialized:
            return ("loading", proxy.lazy_error)
        return (
            "ready" if proxy.available else "unavailable",
            proxy.load_error,
        )

    gita_state, gita_error = describe(gita_retriever_instance)
    scripture_state, scripture_error = describe(scripture_retriever_instance)

    return {
        "status": "healthy",
        "service": "Sanatana Dharma AI Chatbot Backend",
        "api_version": "1.0.0",
        "config": {
            "embedding_backend": settings.EMBEDDING_BACKEND,
            "rerank_enabled": settings.ENABLE_RERANK,
            "bm25_enabled": settings.ENABLE_BM25,
            "multiquery_enabled": settings.ENABLE_MULTIQUERY,
        },
        "retrievers": {
            "gita_index": gita_state,
            "gita_error": gita_error,
            "scripture_index": scripture_state,
            "scripture_error": scripture_error,
        },
        "missing_api_keys": settings.missing_keys(),
    }


if __name__ == "__main__":
    import uvicorn

    # Hosting platforms inject the port to bind through $PORT.
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run("backend.main:app", host=settings.HOST, port=port, reload=False)
