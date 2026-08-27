import os
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path

from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/api/scriptures", tags=["Scripture Explorer API"])

# Cache the Bhagavad Gita DataFrame on startup
_gita_df: Optional[pd.DataFrame] = None

def get_gita_df() -> pd.DataFrame:
    global _gita_df
    if _gita_df is None:
        csv_path = settings.GITA_CSV_PATH
        if os.path.exists(csv_path):
            try:
                # Force UTF-8 encoding
                _gita_df = pd.read_csv(csv_path, encoding="utf-8")
            except Exception as e:
                print(f"[ScripturesAPI] Error loading Bhagavad Gita CSV: {e}")
                # Fallback to empty df with standard columns
                _gita_df = pd.DataFrame(columns=['ID', 'Chapter', 'Verse', 'Shloka', 'Transliteration', 'HinMeaning', 'EngMeaning', 'WordMeaning'])
        else:
            print(f"[ScripturesAPI] Warning: Bhagavad Gita CSV not found at {csv_path}")
            _gita_df = pd.DataFrame(columns=['ID', 'Chapter', 'Verse', 'Shloka', 'Transliteration', 'HinMeaning', 'EngMeaning', 'WordMeaning'])
    return _gita_df

# --- Pydantic Models ---
class VerseOut(BaseModel):
    id: str
    chapter: int
    verse: int
    shloka: str
    transliteration: str
    hindi_meaning: str
    english_meaning: str
    word_meaning: str

class ChapterSummary(BaseModel):
    chapter: int
    verse_count: int

# --- Endpoints ---

@router.get("/gita/chapters", response_model=List[ChapterSummary])
def get_chapters():
    """
    Get lists of all 18 chapters of Bhagavad Gita and their verse counts.
    """
    df = get_gita_df()
    if df.empty:
        return []
    
    # Group by Chapter and count verses
    grouped = df.groupby("Chapter").size().reset_index(name="count")
    return [
        ChapterSummary(chapter=int(row["Chapter"]), verse_count=int(row["count"]))
        for _, row in grouped.iterrows()
    ]

@router.get("/gita/chapters/{chapter_num}", response_model=List[VerseOut])
def get_chapter_verses(chapter_num: int):
    """
    Get all verses in a specific chapter.
    """
    df = get_gita_df()
    chapter_df = df[df["Chapter"] == chapter_num]
    
    if chapter_df.empty:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter_num} not found")
        
    verses = []
    for _, row in chapter_df.iterrows():
        verses.append(VerseOut(
            id=str(row.get("ID", f"BG{row['Chapter']}.{row['Verse']}")),
            chapter=int(row["Chapter"]),
            verse=int(row["Verse"]),
            shloka=str(row.get("Shloka", "")),
            transliteration=str(row.get("Transliteration", "")),
            hindi_meaning=str(row.get("HinMeaning", "")),
            english_meaning=str(row.get("EngMeaning", "")),
            word_meaning=str(row.get("WordMeaning", ""))
        ))
    return verses

@router.get("/gita/chapters/{chapter_num}/verses/{verse_num}", response_model=VerseOut)
def get_specific_verse(chapter_num: int, verse_num: int):
    """
    Get details of a specific verse (e.g. Chapter 2, Verse 47).
    """
    df = get_gita_df()
    verse_row = df[(df["Chapter"] == chapter_num) & (df["Verse"] == verse_num)]
    
    if verse_row.empty:
        raise HTTPException(status_code=404, detail=f"Verse BG {chapter_num}.{verse_num} not found")
        
    row = verse_row.iloc[0]
    return VerseOut(
        id=str(row.get("ID", f"BG{row['Chapter']}.{row['Verse']}")),
        chapter=int(row["Chapter"]),
        verse=int(row["Verse"]),
        shloka=str(row.get("Shloka", "")),
        transliteration=str(row.get("Transliteration", "")),
        hindi_meaning=str(row.get("HinMeaning", "")),
        english_meaning=str(row.get("EngMeaning", "")),
        word_meaning=str(row.get("WordMeaning", ""))
    )

@router.get("/search", response_model=List[VerseOut])
def search_verses(query: str):
    """
    Keyword search across English Meaning, Hindi Meaning, and Shloka text.
    """
    df = get_gita_df()
    if df.empty or not query:
        return []
        
    # Case-insensitive query matches
    query_lower = query.lower()
    matches = df[
        df["EngMeaning"].str.lower().str.contains(query_lower, na=False) |
        df["HinMeaning"].str.lower().str.contains(query_lower, na=False) |
        df["Shloka"].str.lower().str.contains(query_lower, na=False)
    ]
    
    results = []
    # Limit to top 20 search results for performance
    for _, row in matches.head(20).iterrows():
        results.append(VerseOut(
            id=str(row.get("ID", f"BG{row['Chapter']}.{row['Verse']}")),
            chapter=int(row["Chapter"]),
            verse=int(row["Verse"]),
            shloka=str(row.get("Shloka", "")),
            transliteration=str(row.get("Transliteration", "")),
            hindi_meaning=str(row.get("HinMeaning", "")),
            english_meaning=str(row.get("EngMeaning", "")),
            word_meaning=str(row.get("WordMeaning", ""))
        ))
    return results

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_scripture(file: UploadFile = File(...)):
    """
    Upload a new scripture document (PDF) to the Data directory.
    Note: Re-chunks and re-generates the database caches on upload.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents are supported for upload currently."
        )
        
    target_path = Path(settings.DATA_DIR) / file.filename
    try:
        with open(target_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        # Delete chunk cache so it forces a re-parse next time scripture_retriever is requested
        cache_path = Path(settings.DATA_DIR).parent / "scripture_chunks_cache.json"
        if cache_path.exists():
            os.remove(cache_path)
            print("[ScripturesAPI] Deleted chunks cache to trigger re-indexing.")
            
        return {"message": f"Successfully uploaded {file.filename}. Document will be indexed automatically."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save document: {str(e)}"
        )
