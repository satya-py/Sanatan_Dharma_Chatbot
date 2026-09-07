import os
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve root dir
ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # --- API keys -------------------------------------------------------
    # Optional so the service can still boot (and report which keys are
    # missing via /api/health) instead of crash-looping on a hosted
    # instance where one variable was forgotten.
    GOOGLE_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    TAVILY_API_KEY: str = ""
    ASSEMBLYAI_API_KEY: str = ""

    # --- Databases and resource paths -----------------------------------
    DATABASE_URL: str = f"sqlite:///{ROOT_DIR}/sanatan_dharma.db"
    GITA_INDEX_PATH: str = str(ROOT_DIR / "gita_faiss_index")
    SCRIPTURE_INDEX_PATH: str = str(ROOT_DIR / "scripture_faiss_index")
    GITA_CSV_PATH: str = str(ROOT_DIR / "Bhagwad_Gita.csv")
    MAHABHARATA_JSON_PATH: str = str(ROOT_DIR / "mahabharata_progress.json")
    DATA_DIR: str = str(ROOT_DIR / "Data")

    # --- Runtime / resource tuning --------------------------------------
    # "onnx" (fastembed, ~150 MB) or "torch" (sentence-transformers, ~620 MB).
    EMBEDDING_BACKEND: str = "onnx"
    # Cross-encoder reranking. ~80 MB on the onnx backend.
    ENABLE_RERANK: bool = True
    # BM25 hybrid retrieval costs ~335 MB of RAM for this corpus, which does
    # not fit alongside everything else in a 512 MB instance. Off by default;
    # turn on if you run with >= 2 GB.
    ENABLE_BM25: bool = False
    # MultiQueryRetriever fires several extra LLM calls per question.
    ENABLE_MULTIQUERY: bool = True
    # Disable onnxruntime's CPU memory arena and pin to one thread. Saves
    # ~230 MB of resident memory at the cost of a few ms per inference.
    # Turn off only on an instance with plenty of RAM and real CPU.
    ONNX_LOW_MEMORY: bool = True

    # --- App settings ----------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    # Comma-separated list of allowed browser origins, e.g. your Vercel URL.
    CORS_ORIGINS: str = "*"
    LOG_TO_FILE: bool = False

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("EMBEDDING_BACKEND")
    @classmethod
    def _valid_backend(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("onnx", "torch"):
            raise ValueError("EMBEDDING_BACKEND must be 'onnx' or 'torch'")
        return v

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def missing_keys(self) -> List[str]:
        return [
            name
            for name in (
                "GOOGLE_API_KEY",
                "GROQ_API_KEY",
                "TAVILY_API_KEY",
                "ASSEMBLYAI_API_KEY",
            )
            if not getattr(self, name)
        ]


settings = Settings()
