import csv
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel

from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/api/scriptures", tags=["Scripture Explorer API"])

# The Gita CSV is ~700 rows. The stdlib csv module handles it in a few
# milliseconds; importing pandas for this cost ~55 MB of resident memory,
# which is a large slice of a 512 MB instance's budget.
_gita_rows: Optional[List[Dict[str, str]]] = None

VERSE_FIELDS = (
    "ID", "Chapter", "Verse", "Shloka",
    "Transliteration", "HinMeaning", "EngMeaning", "WordMeaning",
)


def get_gita_rows() -> List[Dict[str, str]]:
    """Load and cache the Bhagavad Gita verses from CSV."""
    global _gita_rows
    if _gita_rows is not None:
        return _gita_rows

    csv_path = settings.GITA_CSV_PATH
    rows: List[Dict[str, str]] = []
    if os.path.exists(csv_path):
        try:
            with open(csv_path, "r", encoding="utf-8", newline="") as f:
                for raw in csv.DictReader(f):
                    # Skip rows without a usable chapter/verse number.
                    try:
                        chapter = int(float(raw.get("Chapter") or ""))
                        verse = int(float(raw.get("Verse") or ""))
                    except (TypeError, ValueError):
                        continue
                    row = {k: (raw.get(k) or "").strip() for k in VERSE_FIELDS}
                    row["Chapter"] = chapter
                    row["Verse"] = verse
                    rows.append(row)
        except Exception as e:
            print(f"[ScripturesAPI] Error loading Bhagavad Gita CSV: {e}")
            rows = []
    else:
        print(f"[ScripturesAPI] Warning: Bhagavad Gita CSV not found at {csv_path}")

    _gita_rows = rows
    print(f"[ScripturesAPI] Loaded {len(rows)} Bhagavad Gita verses.")
    return _gita_rows


def _to_verse(row: Dict[str, Any]) -> "VerseOut":
    return VerseOut(
        id=row.get("ID") or f"BG{row['Chapter']}.{row['Verse']}",
        chapter=row["Chapter"],
        verse=row["Verse"],
        shloka=row.get("Shloka", ""),
        transliteration=row.get("Transliteration", ""),
        hindi_meaning=row.get("HinMeaning", ""),
        english_meaning=row.get("EngMeaning", ""),
        word_meaning=row.get("WordMeaning", ""),
    )


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
    counts: Dict[int, int] = {}
    for row in get_gita_rows():
        counts[row["Chapter"]] = counts.get(row["Chapter"], 0) + 1

    return [
        ChapterSummary(chapter=ch, verse_count=counts[ch])
        for ch in sorted(counts)
    ]

@router.get("/gita/chapters/{chapter_num}", response_model=List[VerseOut])
def get_chapter_verses(chapter_num: int):
    """
    Get all verses in a specific chapter.
    """
    matches = [r for r in get_gita_rows() if r["Chapter"] == chapter_num]

    if not matches:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter_num} not found")

    matches.sort(key=lambda r: r["Verse"])
    return [_to_verse(r) for r in matches]

@router.get("/gita/chapters/{chapter_num}/verses/{verse_num}", response_model=VerseOut)
def get_specific_verse(chapter_num: int, verse_num: int):
    """
    Get details of a specific verse (e.g. Chapter 2, Verse 47).
    """
    for row in get_gita_rows():
        if row["Chapter"] == chapter_num and row["Verse"] == verse_num:
            return _to_verse(row)

    raise HTTPException(
        status_code=404, detail=f"Verse BG {chapter_num}.{verse_num} not found"
    )

@router.get("/search", response_model=List[VerseOut])
def search_verses(query: str):
    """
    Keyword search across English Meaning, Hindi Meaning, and Shloka text.
    """
    rows = get_gita_rows()
    if not rows or not query:
        return []

    q = query.lower()
    results = []
    for row in rows:
        haystack = (
            row.get("EngMeaning", ""),
            row.get("HinMeaning", ""),
            row.get("Shloka", ""),
        )
        if any(q in field.lower() for field in haystack):
            results.append(_to_verse(row))
            # Limit to top 20 search results for performance
            if len(results) == 20:
                break
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
