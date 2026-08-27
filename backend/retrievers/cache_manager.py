import os
import json
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ..config import settings

CACHE_FILE_PATH = Path(settings.DATA_DIR).parent / "scripture_chunks_cache.json"

def load_and_chunk_pdf(path, source_name, skip_first_n_pages=0):
    if not os.path.exists(path):
        print(f"[CacheManager] Warning: PDF not found: {path}")
        return []
        
    print(f"[CacheManager] Parsing and chunking PDF: {source_name}")
    loader = PyPDFLoader(path)
    try:
        pages = loader.load()[skip_first_n_pages:]
    except Exception as e:
        print(f"[CacheManager] Error loading PDF {source_name}: {e}")
        return []
        
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " "]
    )
    
    chunks = []
    for page in pages:
        page_num = page.metadata.get("page", "?")
        if isinstance(page_num, int):
            page_num += 1  # 0-indexed to human-readable
            
        splits = splitter.split_text(page.page_content)
        for chunk_text in splits:
            chunks.append({
                "text": chunk_text,
                "source": source_name,
                "reference": f"{source_name}, p.{page_num}",
                "page": page_num
            })
    return chunks

def get_scripture_chunks():
    """
    Get all PDF scripture chunks. Uses a JSON cache to avoid parsing slow PDFs on every startup.
    """
    if CACHE_FILE_PATH.exists():
        print(f"[CacheManager] Loading scripture chunks from cache: {CACHE_FILE_PATH}")
        with open(CACHE_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
            
    # Cache doesn't exist, build it
    print("[CacheManager] Cache not found. Generating scripture chunks from PDFs...")
    base = settings.DATA_DIR
    
    vedas = load_and_chunk_pdf(os.path.join(base, "Four-Vedas-English-Translation.pdf"), "Four Vedas", skip_first_n_pages=50)
    upanishads = load_and_chunk_pdf(os.path.join(base, "108upanishads.pdf"), "108 Upanishads", skip_first_n_pages=10)
    puranas = load_and_chunk_pdf(os.path.join(base, "18 Puranas.pdf"), "18 Puranas", skip_first_n_pages=10)
    bhagavatam = load_and_chunk_pdf(os.path.join(base, "srimad-bhagavata-mahapurana-english-translations.pdf"), "Srimad Bhagavatam", skip_first_n_pages=10)
    
    all_chunks = vedas + upanishads + puranas + bhagavatam
    
    # Save cache
    try:
        with open(CACHE_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)
        print(f"[CacheManager] Successfully generated cache with {len(all_chunks)} chunks at {CACHE_FILE_PATH}")
    except Exception as e:
        print(f"[CacheManager] Error saving cache file: {e}")
        
    return all_chunks
