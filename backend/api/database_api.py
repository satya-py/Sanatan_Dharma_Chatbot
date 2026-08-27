from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from ..database import get_db, ChatSession, ChatMessage, Bookmark, Feedback, AnalyticsMetric

router = APIRouter(prefix="/api/db", tags=["Database API"])

# --- Pydantic Models ---
class SessionCreate(BaseModel):
    title: str
    language: Optional[str] = "en"

class SessionOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    language: str

    class Config:
        from_attributes = True

class MessageOut(BaseModel):
    id: str
    sender: str
    text: str
    timestamp: datetime
    language: str
    citations: Optional[List[dict]] = None

    class Config:
        from_attributes = True

class FeedbackCreate(BaseModel):
    message_id: str
    score: int
    comments: Optional[str] = None

class BookmarkCreate(BaseModel):
    book: str
    chapter: Optional[str] = None
    verse: Optional[str] = None
    shloka: Optional[str] = None
    translation: Optional[str] = None
    meaning: Optional[str] = None

class BookmarkOut(BaseModel):
    id: int
    book: str
    chapter: Optional[str] = None
    verse: Optional[str] = None
    shloka: Optional[str] = None
    translation: Optional[str] = None
    meaning: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Endpoints ---

@router.post("/sessions", response_model=SessionOut)
def create_session(session_data: SessionCreate, db: Session = Depends(get_db)):
    session = ChatSession(title=session_data.title, language=session_data.language)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.get("/sessions", response_model=List[SessionOut])
def get_sessions(db: Session = Depends(get_db)):
    return db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return None

@router.get("/sessions/{session_id}/messages", response_model=List[MessageOut])
def get_messages(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.timestamp.asc()).all()

@router.post("/feedback", status_code=status.HTTP_201_CREATED)
def submit_feedback(feedback_data: FeedbackCreate, db: Session = Depends(get_db)):
    fb = Feedback(
        message_id=feedback_data.message_id,
        score=feedback_data.score,
        comments=feedback_data.comments
    )
    db.add(fb)
    db.commit()
    return {"message": "Feedback submitted successfully"}

@router.post("/bookmarks", response_model=BookmarkOut)
def add_bookmark(bookmark_data: BookmarkCreate, db: Session = Depends(get_db)):
    bm = Bookmark(**bookmark_data.model_dump())
    db.add(bm)
    db.commit()
    db.refresh(bm)
    return bm

@router.get("/bookmarks", response_model=List[BookmarkOut])
def get_bookmarks(db: Session = Depends(get_db)):
    return db.query(Bookmark).order_by(Bookmark.created_at.desc()).all()

@router.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(bookmark_id: int, db: Session = Depends(get_db)):
    bm = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    db.delete(bm)
    db.commit()
    return None
