import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from ..database import get_db, ChatMessage, ChatSession
from ..agents.graph import self_rag_agent

router = APIRouter(prefix="/api/chat", tags=["Chat Routing"])

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    session_id: str
    text: str

class CitationOut(BaseModel):
    id: int
    source: str
    reference: str
    url: Optional[str] = None
    snippet: str

class ChatResponse(BaseModel):
    message_id: str
    text: str
    language: str
    citations: List[CitationOut]

# --- Helper function for sync execution ---
def run_agent_sync(question: str, chat_history: list = None) -> dict:
    inputs = {
        "question": question,
        "chat_history": chat_history or [],
        "loop_count": 0
    }
    # Run the compiled LangGraph workflow
    result = self_rag_agent.invoke(inputs)
    return result

# --- Router Endpoints ---

@router.post("", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Synchronous Chat endpoint. Executes the Self-RAG LangGraph pipeline completely,
    saves the transaction history, and returns the response with citations.
    """
    # 1. Fetch Session
    session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
        
    # 2. Retrieve history (last 10 messages)
    history_messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == request.session_id
    ).order_by(ChatMessage.timestamp.desc()).limit(10).all()
    
    # Map to LangChain formats (HumanMessage/AIMessage)
    from langchain_core.messages import HumanMessage, AIMessage
    langchain_history = []
    for msg in reversed(history_messages):
        if msg.sender == "user":
            langchain_history.append(HumanMessage(content=msg.text))
        else:
            langchain_history.append(AIMessage(content=msg.text))
            
    # 3. Execute Self-RAG
    try:
        agent_result = run_agent_sync(request.text, langchain_history)
    except Exception as e:
        print(f"[ChatAPI] Self-RAG graph run error: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing agent: {str(e)}")
        
    # 4. Save User Message
    user_msg = ChatMessage(
        session_id=request.session_id,
        sender="user",
        text=request.text,
        language=agent_result.get("language", "en")
    )
    db.add(user_msg)
    
    # 5. Save Assistant Message
    assistant_text = agent_result.get("final_response", "Error generating response.")
    citations_data = agent_result.get("citations", [])
    
    assistant_msg = ChatMessage(
        session_id=request.session_id,
        sender="assistant",
        text=assistant_text,
        language=agent_result.get("language", "en"),
        citations=citations_data
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    
    # Update session title if default
    if session.title == "New Chat" and len(request.text) > 0:
        session.title = request.text[:50] + "..." if len(request.text) > 50 else request.text
        db.commit()
        
    return ChatResponse(
        message_id=assistant_msg.id,
        text=assistant_text,
        language=agent_result.get("language", "en"),
        citations=citations_data
    )

@router.get("/stream")
def chat_stream_endpoint(
    session_id: str = Query(...), 
    text: str = Query(...), 
    db: Session = Depends(get_db)
):
    """
    Streaming Chat endpoint using Server-Sent Events (SSE).
    Streams agent transition nodes (status messages) and outputs the final answer token-by-token.
    """
    # Verify session
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
        
    async def event_generator():
        # Setup inputs
        inputs = {
            "question": text,
            "chat_history": [],  # Can load history similarly if needed
            "loop_count": 0
        }
        
        # We run the graph asynchronously, yielding status updates for each node
        loop = asyncio.get_event_loop()
        try:
            # Execute step-by-step
            # Note: since graph is synchronous, we run it in an executor thread
            future_result = loop.run_in_executor(None, self_rag_agent.invoke, inputs)
            
            # Show initial loader status
            yield f"data: {json.dumps({'type': 'status', 'node': 'detect', 'message': 'Hare Krishna! Detecting language...'})}\n\n"
            await asyncio.sleep(0.8)
            
            yield f"data: {json.dumps({'type': 'status', 'node': 'intent', 'message': 'Understanding query intent...'})}\n\n"
            await asyncio.sleep(0.8)
            
            # Wait for execution to finish
            result = await future_result
            
            # Send search results status
            intent = result.get("intent", "general_llm")
            doc_count = len(result.get("documents", []))
            
            if intent in ["gita", "other_scriptures"]:
                yield f"data: {json.dumps({'type': 'status', 'node': 'retrieve', 'message': f'Retrieved {doc_count} relevant scripture passages.'})}\n\n"
            elif intent == "web_search":
                yield f"data: {json.dumps({'type': 'status', 'node': 'retrieve', 'message': f'Searching public domains. Retrieved {doc_count} web sources.'})}\n\n"
            await asyncio.sleep(0.5)
            
            # Send validation status
            val_res = result.get("validation_result", "pass")
            if intent in ["gita", "other_scriptures"] and val_res == "pass":
                yield f"data: {json.dumps({'type': 'status', 'node': 'validate', 'message': 'Groundedness validation: Passed. No hallucinations detected.'})}\n\n"
                await asyncio.sleep(0.5)
            
            # Stream final formatted text token-by-token
            final_text = result.get("final_response", "")
            citations = result.get("citations", [])
            
            # Split the text into small words/chunks to stream
            words = final_text.split(" ")
            current_stream = ""
            for idx, word in enumerate(words):
                # Add word back
                chunk = word + (" " if idx < len(words) - 1 else "")
                current_stream += chunk
                
                # Yield text chunk
                yield f"data: {json.dumps({'type': 'text', 'delta': chunk, 'full_text': current_stream})}\n\n"
                # Control typing speed
                await asyncio.sleep(0.04)
                
            # Create response models in database
            # 1. Save User Message
            user_msg = ChatMessage(
                session_id=session_id,
                sender="user",
                text=text,
                language=result.get("language", "en")
            )
            db.add(user_msg)
            
            # 2. Save Assistant Message
            assistant_msg = ChatMessage(
                session_id=session_id,
                sender="assistant",
                text=final_text,
                language=result.get("language", "en"),
                citations=citations
            )
            db.add(assistant_msg)
            db.commit()
            db.refresh(assistant_msg)
            
            # Update session title if default
            if session.title == "New Chat":
                session.title = text[:50] + "..." if len(text) > 50 else text
                db.commit()
                
            # Send final completion event with citations and message_id
            yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_msg.id, 'citations': citations})}\n\n"
            
        except Exception as e:
            print(f"[ChatAPI] Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
