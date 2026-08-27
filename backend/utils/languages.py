from langdetect import detect
from langchain_groq import ChatGroq
from ..config import settings

# Shared LLM instance for translation and utility tasks
translation_llm = ChatGroq(
    model="openai/gpt-oss-120b", 
    temperature=0.0,  # 0.0 for deterministic translations
    groq_api_key=settings.GROQ_API_KEY
)

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "mr": "Marathi",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "or": "Odia",
    "sa": "Sanskrit",
    "ne": "Nepali",
    "ur": "Urdu"
}

def detect_language(text: str) -> str:
    """
    Detect the ISO 639-1 language code of the text.
    Defaults to 'en' on failure.
    """
    try:
        lang = detect(text)
        return lang
    except Exception:
        return "en"

def translate_to_english(text: str, source_lang: str) -> str:
    """
    Translate source text to English.
    """
    if source_lang == "en":
        return text
        
    lang_name = LANGUAGE_NAMES.get(source_lang, source_lang)
    
    prompt = (
        f"Translate the following {lang_name} text to English. "
        f"Provide ONLY the plain English translation. Do not add any introductory or explanatory text. "
        f"If the text is already in English, return it unchanged.\n\n"
        f"Text to translate:\n{text}"
    )
    
    try:
        response = translation_llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        print(f"[Languages] Translation to English failed: {e}")
        return text

def translate_answer(answer_text: str, target_lang: str) -> str:
    """
    Translate English answer back to the user's language.
    Strictly preserves Sanskrit shlokas and chapter/verse citations.
    """
    if target_lang == "en":
        return answer_text
        
    lang_name = LANGUAGE_NAMES.get(target_lang, target_lang)
    
    prompt = (
        f"You are a translator. Translate this English text containing Hindu scripture citations to {lang_name}.\n"
        f"CRITICAL RULES:\n"
        f"1. Keep any Sanskrit shlokas (written in Devanagari or transliteration) EXACTLY as they are. Do not translate them.\n"
        f"2. Keep all citations, chapter numbers, and verse numbers (e.g., 'Chapter 2, Verse 47' or '[BG 2.47]') EXACTLY as they are.\n"
        f"3. Provide ONLY the translated text in {lang_name}. Do not add notes, chatter, or introductory text.\n\n"
        f"English Text:\n{answer_text}"
    )
    
    try:
        response = translation_llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        print(f"[Languages] Translation to {lang_name} failed: {e}")
        return answer_text
