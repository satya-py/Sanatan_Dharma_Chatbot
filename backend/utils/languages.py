from langdetect import DetectorFactory, detect

from ..config import settings

# Deterministic language detection (langdetect is randomised by default).
DetectorFactory.seed = 0

GROQ_MODEL = "openai/gpt-oss-120b"

# Shared LLM instance for translation and utility tasks.
# Built lazily so that a missing GROQ_API_KEY surfaces as a handled runtime
# error on the affected request rather than crashing the whole service at
# import time (which on a hosted instance means an endless restart loop).
_translation_llm = None


def get_translation_llm():
    """Return the shared Groq chat model, constructing it on first use."""
    global _translation_llm
    if _translation_llm is None:
        if not settings.GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it in the Render dashboard under "
                "Environment, then redeploy."
            )
        from langchain_groq import ChatGroq

        _translation_llm = ChatGroq(
            model=GROQ_MODEL,
            temperature=0.0,  # 0.0 for deterministic translations
            groq_api_key=settings.GROQ_API_KEY,
        )
    return _translation_llm

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

# Indic scripts map cleanly onto the languages this app serves, and a script
# check is far more reliable than statistical detection -- especially on short
# input, where langdetect happily calls "Hare Krishna!" Albanian and then
# translates the entire reply into Albanian.
SCRIPT_RANGES = (
    ((0x0900, 0x097F), "hi"),  # Devanagari (Hindi, Marathi, Sanskrit, Nepali)
    ((0x0980, 0x09FF), "bn"),  # Bengali
    ((0x0A00, 0x0A7F), "pa"),  # Gurmukhi
    ((0x0A80, 0x0AFF), "gu"),  # Gujarati
    ((0x0B00, 0x0B7F), "or"),  # Odia
    ((0x0B80, 0x0BFF), "ta"),  # Tamil
    ((0x0C00, 0x0C7F), "te"),  # Telugu
    ((0x0C80, 0x0CFF), "kn"),  # Kannada
    ((0x0D00, 0x0D7F), "ml"),  # Malayalam
    ((0x0600, 0x06FF), "ur"),  # Arabic script (Urdu)
)

# Minimum characters before a statistical guess on Latin text is trustworthy.
MIN_CHARS_FOR_DETECTION = 20


def _script_language(text: str):
    """Return a language code if the text is written in a non-Latin script."""
    counts = {}
    for ch in text:
        cp = ord(ch)
        for (lo, hi), code in SCRIPT_RANGES:
            if lo <= cp <= hi:
                counts[code] = counts.get(code, 0) + 1
                break
    if not counts:
        return None
    return max(counts, key=counts.get)


def detect_language(text: str) -> str:
    """
    Detect the ISO 639-1 language code of the text.
    Defaults to 'en' on failure or when the guess is not one we support.
    """
    text = (text or "").strip()
    if not text:
        return "en"

    # 1. Non-Latin script is decisive.
    scripted = _script_language(text)
    if scripted:
        return scripted

    # 2. Latin script: too short to judge, so assume English rather than
    #    mistranslating the reply into whatever langdetect guessed.
    if len(text) < MIN_CHARS_FOR_DETECTION:
        return "en"

    try:
        lang = detect(text)
    except Exception:
        return "en"

    # 3. Only trust a guess that is a language this app actually serves.
    #    Romanised Hindi, typos and short phrases otherwise get flagged as
    #    unrelated European languages.
    return lang if lang in LANGUAGE_NAMES else "en"

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
        response = get_translation_llm().invoke(prompt)
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
        response = get_translation_llm().invoke(prompt)
        return response.content.strip()
    except Exception as e:
        print(f"[Languages] Translation to {lang_name} failed: {e}")
        return answer_text
