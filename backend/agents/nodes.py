import json
import re
from typing import Dict, Any, List
from langchain_core.documents import Document
from tavily import TavilyClient

from ..config import settings
from ..utils.languages import (
    detect_language, 
    translate_to_english, 
    translate_answer,
    get_translation_llm,
)
from ..retrievers.gita_retriever import gita_retriever_instance
from ..retrievers.scripture_retriever import scripture_retriever_instance
from .prompt_templates import (
    INTENT_CLASSIFIER_PROMPT,
    QUERY_REWRITE_PROMPT,
    ANSWER_GENERATION_PROMPT,
    VALIDATOR_PROMPT,
    CITATION_VALIDATOR_PROMPT
)

# Tavily is created lazily for the same reason as the Groq client: a missing
# key should fail the one request that needs it, not the whole process.
_tavily_client = None


def get_tavily_client():
    global _tavily_client
    if _tavily_client is None:
        if not settings.TAVILY_API_KEY:
            raise RuntimeError("TAVILY_API_KEY is not set.")
        _tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    return _tavily_client
TRUSTED_DOMAINS = ["sacred-texts.com", "iskcon.org", "valmikiramayan.net", "gbc.iskcon.org", "communications.iskcon.org"]

def detect_and_translate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detects language of query and translates to English if necessary.
    """
    question = state["question"]
    lang = detect_language(question)
    
    # Translate to English for unified retrieval
    translated = translate_to_english(question, lang)
    
    print(f"[Node: Detect & Translate] Detected: {lang} | Translated: {translated}")
    return {
        "language": lang,
        "translated_question": translated,
        "loop_count": 0
    }

def classify_intent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classifies the intent of the query using the translation LLM.
    """
    query = state["translated_question"]
    prompt = INTENT_CLASSIFIER_PROMPT.format(query=query)
    
    intent = "general_llm"
    try:
        response = get_translation_llm().invoke(prompt)
        content = response.content.strip()
        
        # Clean JSON markdown fences if the LLM included them
        content_cleaned = re.sub(r"^```json\s*", "", content)
        content_cleaned = re.sub(r"\s*```$", "", content_cleaned).strip()
        
        data = json.loads(content_cleaned)
        intent = data.get("intent", "general_llm")
    except Exception as e:
        print(f"[Node: Intent Classifier] Error classifying query: {e}. Defaulting to general_llm.")
        
    print(f"[Node: Intent Classifier] Classified intent: {intent}")
    return {"intent": intent}

def retrieve_documents_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieves relevant documents from Gita, Scripture, or Tavily Web Search based on intent.
    """
    intent = state["intent"]
    query = state["translated_question"]
    docs: List[Document] = []
    
    if intent == "gita":
        print(f"[Node: Retriever] Fetching from Gita Index for query: {query}")
        docs = gita_retriever_instance.retrieve(query, k=4)
        
    elif intent == "other_scriptures":
        print(f"[Node: Retriever] Fetching from Scripture Index for query: {query}")
        # Leverage MultiQuery and Cross-Encoder reranking
        docs = scripture_retriever_instance.retrieve(
            query, 
            llm=get_translation_llm(), 
            use_multiquery=True, 
            top_k=5
        )
        
    elif intent == "web_search":
        print(f"[Node: Retriever] Searching Tavily for query: {query}")
        try:
            results = get_tavily_client().search(
                query=query, 
                include_domains=TRUSTED_DOMAINS, 
                max_results=3
            )
            for r in results.get("results", []):
                doc = Document(
                    page_content=r["content"],
                    metadata={
                        "source": "Web Search",
                        "reference": r["title"],
                        "url": r["url"]
                    }
                )
                docs.append(doc)
        except Exception as e:
            print(f"[Node: Retriever] Tavily search error: {e}")
            
    else:
        # For greetings or general questions, retrieve no documents (use LLM general knowledge)
        print(f"[Node: Retriever] Skipping document retrieval for intent: {intent}")
        docs = []
        
    print(f"[Node: Retriever] Retrieved {len(docs)} documents.")
    return {"documents": docs}

def describe_llm_error(exc: Exception) -> str:
    """
    Turn an LLM transport failure into something a reader can act on.

    Every failure used to surface as "I was unable to compile the answer",
    which is indistinguishable between a spent quota, a bad key and a network
    blip -- and the quota case is by far the most common, because the Groq free
    tier allows 200k tokens/day and one question through this graph costs
    roughly 10k-25k.
    """
    text = str(exc)
    lowered = text.lower()

    if "rate_limit" in lowered or "rate limit" in lowered or "429" in text:
        detail = ""
        # The API reports how long the caller has to wait; pass it through.
        match = re.search(r"try again in ([0-9hms.]+)", text)
        if match:
            # The character class also swallows the sentence's full stop.
            wait = match.group(1).rstrip(".")
            detail = f" Please try again in {wait}."
        if "per day" in lowered or "tpd" in lowered:
            return (
                "The daily quota for the language model has been used up."
                f"{detail} The Groq free tier allows 200,000 tokens per day, "
                "which is roughly 10-20 questions."
            )
        return (
            "Too many requests to the language model in a short window."
            f"{detail}"
        )

    if "invalid_api_key" in lowered or "401" in text or "unauthorized" in lowered:
        return (
            "The language model rejected the API key. Check GROQ_API_KEY in the "
            "server environment."
        )

    if "GROQ_API_KEY is not set" in text:
        return "The server is missing its GROQ_API_KEY. Set it and redeploy."

    if "timeout" in lowered or "timed out" in lowered:
        return "The language model took too long to respond. Please try again."

    return "I was unable to compile the answer. Please try again."


def generate_answer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates an answer using the retrieved documents.
    """
    question = state["translated_question"]
    docs = state["documents"]
    
    gita_excerpts = []
    scripture_excerpts = []
    web_excerpts = []
    
    for d in docs:
        source = d.metadata.get("source", "").lower()
        ref = d.metadata.get("reference", "Unknown")
        
        if "gita" in source or "gita" in ref.lower():
            gita_excerpts.append(f"[{ref}]: {d.page_content}")
        elif source == "web search":
            web_excerpts.append(f"[{ref} ({d.metadata.get('url', '')})]: {d.page_content}")
        else:
            scripture_excerpts.append(f"[{ref}]: {d.page_content}")
            
    gita_context = "\n\n".join(gita_excerpts) if gita_excerpts else "No Bhagavad Gita excerpts retrieved."
    scripture_context = "\n\n".join(scripture_excerpts) if scripture_excerpts else "No other scripture excerpts retrieved."
    web_context = "\n\n".join(web_excerpts) if web_excerpts else "No web search excerpts retrieved."
    
    prompt = ANSWER_GENERATION_PROMPT.format(
        gita_context=gita_context,
        scripture_context=scripture_context,
        web_context=web_context,
        question=question
    )
    
    print("[Node: Generator] Generating answer from context...")
    try:
        response = get_translation_llm().invoke(prompt)
        generation = response.content.strip()
    except Exception as e:
        print(f"[Node: Generator] Error generating response: {e}")
        generation = describe_llm_error(e)

    return {"generation": generation}

REFUSAL_MARKERS = (
    "could not find a directly relevant teaching",
    "could not find a relevant teaching",
    "unable to compile the answer",
    "quota for the language model",
    "too many requests to the language model",
    "rejected the api key",
    "missing its groq_api_key",
    "took too long to respond",
)


def _is_refusal(generation: str) -> bool:
    text = (generation or "").lower()
    return any(marker in text for marker in REFUSAL_MARKERS)


def validate_answer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates if the generated answer is grounded in retrieved documents and doesn't hallucinate.
    """
    docs = state["documents"]
    generation = state["generation"]
    loop_count = state["loop_count"]
    
    # If no documents were retrieved (greeting or general conversation), always pass validation
    if not docs:
        print("[Node: Validator] Skipping validation for query with no documents (Greeting/General).")
        return {"validation_result": "pass", "feedback_reason": ""}

    # A refusal is a statement about the retrieval, not a claim about scripture.
    # Validating it just fails it for "not being in the excerpts", which sends
    # the graph round the retry loop until the budget runs out and then returns
    # the refusal anyway -- several wasted LLM calls and ~2 extra minutes.
    if _is_refusal(generation):
        print("[Node: Validator] Answer is a refusal; nothing to ground. Passing.")
        return {"validation_result": "pass", "feedback_reason": ""}
        
    # Collate context
    context = "\n\n".join([f"[{d.metadata.get('reference')}]: {d.page_content}" for d in docs])
    
    # 1. Groundedness/Hallucination Check
    print("[Node: Validator] Running Groundedness / Hallucination Check...")
    grounded_prompt = VALIDATOR_PROMPT.format(context=context, generation=generation)
    
    try:
        response = get_translation_llm().invoke(grounded_prompt)
        content = re.sub(r"^```json\s*", "", response.content.strip())
        content = re.sub(r"\s*```$", "", content).strip()
        res_data = json.loads(content)
        
        if not res_data.get("grounded", True):
            reason = f"Groundedness check failed: {res_data.get('reason', 'Unreferenced claims found.')}"
            print(f"[Node: Validator] FAIL: {reason}")
            return {"validation_result": "fail", "feedback_reason": reason}
            
    except Exception as e:
        print(f"[Node: Validator] Warning: Groundedness check parsed failed: {e}. Passing anyway.")
        
    # 2. Citation Check
    print("[Node: Validator] Running Citation Verification Check...")
    citation_prompt = CITATION_VALIDATOR_PROMPT.format(context=context, generation=generation)
    
    try:
        response = get_translation_llm().invoke(citation_prompt)
        content = re.sub(r"^```json\s*", "", response.content.strip())
        content = re.sub(r"\s*```$", "", content).strip()
        res_data = json.loads(content)
        
        if not res_data.get("citations_valid", True):
            reason = f"Citation check failed: {res_data.get('reason', 'Invalid or missing chapter/verse references.')}"
            print(f"[Node: Validator] FAIL: {reason}")
            return {"validation_result": "fail", "feedback_reason": reason}
            
    except Exception as e:
        print(f"[Node: Validator] Warning: Citation check parsed failed: {e}. Passing anyway.")
        
    print("[Node: Validator] PASS: Answer is faithful and grounded.")
    return {"validation_result": "pass", "feedback_reason": ""}

def query_rewrite_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rewrites the search query to improve document retrieval when validation fails.
    """
    original_query = state["question"]
    prev_query = state["translated_question"]
    feedback = state["feedback_reason"]
    loop = state["loop_count"] + 1
    
    prompt = QUERY_REWRITE_PROMPT.format(
        original_query=original_query,
        previous_query=prev_query,
        feedback_reason=feedback
    )
    
    print(f"[Node: Query Rewrite] Rewriting search query (Attempt #{loop})...")
    try:
        response = get_translation_llm().invoke(prompt)
        rewritten = (response.content or "").strip()
    except Exception as e:
        print(f"[Node: Query Rewrite] Error rewriting query: {e}. Retrying with original.")
        rewritten = prev_query

    # The model sometimes returns an empty string (or a bare fence/quote). Searching
    # on that retrieves arbitrary documents and guarantees the next validation
    # round also fails, burning the whole retry budget. Fall back instead.
    rewritten = rewritten.strip('`"\' \n\t')
    if len(rewritten) < 3:
        print("[Node: Query Rewrite] Rewrite was empty; keeping the previous query.")
        rewritten = prev_query or original_query
        
    print(f"[Node: Query Rewrite] Old: {prev_query} | New: {rewritten}")
    return {
        "translated_question": rewritten,
        "loop_count": loop
    }

def format_and_translate_response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats the answer, prepends language-appropriate greetings, and translates back to user language.
    """
    generation = state["generation"]
    lang = state["language"]
    intent = state["intent"]
    docs = state["documents"]
    
    # 1. Select Greeting based on language
    greetings = {
        "hi": "हरे कृष्ण! 🙏",
        "bn": "হরে কৃষ্ণ! 🙏",
        "gu": "હરે કૃષ્ણ! 🙏",
        "mr": "हरे कृष्ण! 🙏",
        "ta": "ஹரே கிருஷ்ணா! 🙏",
        "te": "హరే కృష్ణ! 🙏",
        "kn": "హరే కృష్ణ! 🙏",
        "ml": "ഹരേ കൃഷ്ണ! 🙏",
        "sa": "हरे कृष्ण! 🙏",
        "pa": "ਹਰੇ ਕ੍ਰਿਸ਼ਨਾ! 🙏"
    }
    greeting = greetings.get(lang, "Hare Krishna! 🙏")
    
    # 2. Translate body if not English
    body_translated = translate_answer(generation, lang)
    
    # Assemble final output
    final_output = f"{greeting}\n\n{body_translated}"
    
    # 3. Extract Citations list from documents metadata
    citations = []
    for idx, d in enumerate(docs):
        meta = d.metadata
        citations.append({
            "id": idx + 1,
            "source": meta.get("source", "Scripture"),
            "reference": meta.get("reference", "Reference"),
            "url": meta.get("url"),
            "snippet": d.page_content[:300] + "..."
        })
        
    print(f"[Node: Response Formatter] Response assembled in language: {lang}")
    return {
        "final_response": final_output,
        "citations": citations
    }
