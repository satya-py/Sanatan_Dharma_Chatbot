import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Resolve root dir
ROOT_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(dotenv_path=ROOT_DIR / ".env")

class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    GROQ_API_KEY: str
    TAVILY_API_KEY: str
    ASSEMBLYAI_API_KEY: str
    
    # Databases and resources paths
    DATABASE_URL: str = f"sqlite:///{ROOT_DIR}/sanatan_dharma.db"
    GITA_INDEX_PATH: str = str(ROOT_DIR / "gita_faiss_index")
    SCRIPTURE_INDEX_PATH: str = str(ROOT_DIR / "scripture_faiss_index")
    GITA_CSV_PATH: str = str(ROOT_DIR / "Bhagwad_Gita.csv")
    MAHABHARATA_JSON_PATH: str = str(ROOT_DIR / "mahabharata_progress.json")
    DATA_DIR: str = str(ROOT_DIR / "Data")
    
    # App Settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
