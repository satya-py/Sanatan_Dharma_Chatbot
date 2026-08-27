import os
from pathlib import Path
import assemblyai as aai
from gtts import gTTS
from ..config import settings

# Initialize AssemblyAI settings
aai.settings.api_key = settings.ASSEMBLYAI_API_KEY

# Determine temp storage for generated speech files
AUDIO_CACHE_DIR = Path(__file__).resolve().parent.parent / "static" / "audio"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def transcribe_audio(file_path: str, language_code: str = None) -> str:
    """
    Transcribes an audio file using AssemblyAI.
    """
    if not os.path.exists(file_path):
        print(f"[STT] Audio file not found at: {file_path}")
        return ""
        
    print(f"[STT] Transcribing audio file: {file_path}")
    try:
        transcriber = aai.Transcriber()
        config = None
        if language_code:
            config = aai.TranscriptionConfig(language_code=language_code)
            
        transcript = transcriber.transcribe(file_path, config=config)
        
        if transcript.status == aai.TranscriptStatus.error:
            print(f"[STT] AssemblyAI transcription error: {transcript.error}")
            return ""
            
        return transcript.text
    except Exception as e:
        print(f"[STT] AssemblyAI transcription failed: {e}")
        return ""

def text_to_speech(text: str, lang_code: str = "en") -> str:
    """
    Converts text to an MP3 file using Google Text-to-Speech (gTTS).
    Returns the absolute path to the generated file.
    """
    # Clean language code for gTTS (e.g. 'en-US' -> 'en', 'hi-IN' -> 'hi')
    clean_lang = lang_code.split("-")[0]
    
    # Supported gTTS languages fallback (simplified mapping)
    # gTTS supports: en, hi, bn, gu, mr, ta, te, kn, ml, pa, etc.
    supported_langs = ["en", "hi", "bn", "gu", "mr", "ta", "te", "kn", "ml", "pa", "es", "fr"]
    if clean_lang not in supported_langs:
        print(f"[TTS] Language '{clean_lang}' not fully supported by gTTS. Falling back to 'en'.")
        clean_lang = "en"
        
    # Generate unique filename using hash of text & language
    import hashlib
    text_hash = hashlib.md5(f"{text}_{clean_lang}".encode("utf-8")).hexdigest()
    output_filename = f"tts_{text_hash}.mp3"
    output_path = AUDIO_CACHE_DIR / output_filename
    
    # Return existing cached file if already generated
    if output_path.exists():
        return str(output_path)
        
    print(f"[TTS] Generating speech file: {output_path} (Lang: {clean_lang})")
    try:
        # gTTS generates high-quality speech for most languages
        tts = gTTS(text=text, lang=clean_lang, slow=False)
        tts.save(str(output_path))
        return str(output_path)
    except Exception as e:
        print(f"[TTS] Google Text-to-Speech failed: {e}")
        return ""
