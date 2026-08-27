import os
import uuid
import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from ..database import get_db, ChatMessage, ChatSession
from ..utils.voice_processor import transcribe_audio, text_to_speech
from .chat import run_agent_sync

router = APIRouter(prefix="/api/voice", tags=["Voice Assistant API"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("", status_code=status.HTTP_200_OK)
async def voice_endpoint(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Uploads user recorded audio, transcribes it, runs it through the Self-RAG agent,
    synthesizes the answer to audio, and returns text + audio files.
    """
    # 1. Verify session
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
        
    # 2. Save uploaded audio file locally
    file_ext = Path(file.filename).suffix or ".wav"
    temp_filename = f"upload_{uuid.uuid4()}{file_ext}"
    temp_filepath = UPLOAD_DIR / temp_filename
    
    print(f"[VoiceAPI] Saving uploaded file to {temp_filepath}")
    try:
        with open(temp_filepath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write audio file locally: {str(e)}"
        )
        
    # 3. Transcribe audio with AssemblyAI
    transcribed_text = transcribe_audio(str(temp_filepath))
    
    # Delete uploaded file after transcription to free disk space
    if temp_filepath.exists():
        try:
            os.remove(temp_filepath)
        except Exception:
            pass
            
    if not transcribed_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not transcribe audio. Please speak clearly."
        )
        
    print(f"[VoiceAPI] Transcribed: '{transcribed_text}'")
    
    # 4. Fetch history and run Self-RAG agent
    # Retrieve history (last 10 messages)
    history_messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.timestamp.desc()).limit(10).all()
    
    from langchain_core.messages import HumanMessage, AIMessage
    langchain_history = []
    for msg in reversed(history_messages):
        if msg.sender == "user":
            langchain_history.append(HumanMessage(content=msg.text))
        else:
            langchain_history.append(AIMessage(content=msg.text))
            
    try:
        agent_result = run_agent_sync(transcribed_text, langchain_history)
    except Exception as e:
        print(f"[VoiceAPI] Agent execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing agent: {str(e)}")
        
    # 5. Save messages to DB
    user_msg = ChatMessage(
        session_id=session_id,
        sender="user",
        text=transcribed_text,
        language=agent_result.get("language", "en")
    )
    db.add(user_msg)
    
    assistant_text = agent_result.get("final_response", "Error generating response.")
    citations_data = agent_result.get("citations", [])
    
    assistant_msg = ChatMessage(
        session_id=session_id,
        sender="assistant",
        text=assistant_text,
        language=agent_result.get("language", "en"),
        citations=citations_data
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    
    # 6. Convert final text back to audio (TTS)
    # Using clean language code detected from query
    lang_code = agent_result.get("language", "en")
    # Strip markup / markdown symbols for cleaner speech
    clean_speech_text = re.sub(r"[#*`_\-\[\]\(\)]", " ", assistant_text)
    clean_speech_text = re.sub(r"\s+", " ", clean_speech_text).strip()
    
    tts_filepath = text_to_speech(clean_speech_text[:500], lang_code) # Limit to first 500 chars for speed & performance
    
    audio_url = ""
    if tts_filepath:
        # Create audio URL pointing to static endpoint
        tts_filename = Path(tts_filepath).name
        audio_url = f"/static/audio/{tts_filename}"
        
    return {
        "message_id": assistant_msg.id,
        "question": transcribed_text,
        "answer": assistant_text,
        "audio_url": audio_url,
        "language": lang_code,
        "citations": citations_data
    }
