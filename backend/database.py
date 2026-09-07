import json
from datetime import datetime
import uuid
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from .config import settings

# check_same_thread is a SQLite-only argument; passing it to any other driver
# (e.g. if DATABASE_URL is switched to Postgres for persistent storage on
# Render) raises TypeError at import time.
_connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    language = Column(String(10), default="en")
    
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(10), nullable=False)  # "user" or "assistant"
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    language = Column(String(10), default="en")
    
    # JSON array containing references and citations
    citations = Column(JSON, nullable=True) 
    
    session = relationship("ChatSession", back_populates="messages")

class Bookmark(Base):
    __tablename__ = "bookmarks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    book = Column(String(100), nullable=False)  # e.g., "Bhagavad Gita", "Mahabharata"
    chapter = Column(String(50), nullable=True)
    verse = Column(String(50), nullable=True)
    shloka = Column(Text, nullable=True)
    translation = Column(Text, nullable=True)
    meaning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(36), nullable=False)
    score = Column(Integer, nullable=False)  # 1 for thumb-up, -1 for thumb-down
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AnalyticsMetric(Base):
    __tablename__ = "analytics_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    query_time_ms = Column(Float, nullable=False)
    intent = Column(String(50), nullable=False)
    language = Column(String(10), nullable=False)
    tokens_used = Column(Integer, default=0)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
