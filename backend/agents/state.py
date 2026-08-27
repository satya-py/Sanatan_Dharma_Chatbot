from typing import List, Dict, Any, TypedDict
from langchain_core.messages import BaseMessage
from langchain_core.documents import Document

class AgentState(TypedDict):
    """
    State representation for the Sanatana Dharma Self-RAG agent.
    """
    question: str                   # Original user query
    language: str                   # Detected language code (e.g. 'en', 'hi', 'bn')
    translated_question: str        # Query translated to English
    intent: str                     # Classified intent: 'gita', 'other_scriptures', 'web_search', 'greeting', 'general_llm'
    documents: List[Document]       # Retrieved & reranked scripture/web documents
    generation: str                 # Generated response in English
    final_response: str             # Final formatted and translated response in the user's language
    citations: List[Dict[str, Any]] # Extracted references (e.g., book, chapter, verse, meaning, text)
    validation_result: str          # Groundedness/hallucination validation: "pass" or "fail"
    feedback_reason: str            # Reason for failure to aid query re-writing
    loop_count: int                 # Count of retrieval loop retries (prevents infinite loops)
    chat_history: List[BaseMessage] # Previous conversation logs
