import React, { useState, useEffect } from "react";
import { BookOpen, Search, Bookmark, UploadCloud, ChevronRight, FileText, Check, AlertCircle } from "lucide-react";
import { scriptureService, type Verse } from "../services/api";

export const ScriptureExplorer: React.FC = () => {
  const [chapters, setChapters] = useState<{ chapter: number; verse_count: number }[]>([]);
  const [selectedChapter, setSelectedChapter] = useState<number | null>(null);
  const [verses, setVerses] = useState<Verse[]>([]);
  const [selectedVerse, setSelectedVerse] = useState<Verse | null>(null);
  
  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Verse[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [viewMode, setViewMode] = useState<"browse" | "search">("browse");

  // PDF Upload state
  const [uploadStatus, setUploadStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [uploadMessage, setUploadMessage] = useState("");

  // Bookmark tracking
  const [bookmarkedIds, setBookmarkedIds] = useState<Record<string, boolean>>({});

  useEffect(() => {
    // Load chapters on start
    scriptureService.getChapters()
      .then((data) => setChapters(data))
      .catch((e) => console.error("Error fetching chapters:", e));

    // Load current bookmarks to initialize button states
    scriptureService.getBookmarks()
      .then((data) => {
        const bookmarksMap: Record<string, boolean> = {};
        data.forEach((b: any) => {
          if (b.chapter && b.verse) {
            bookmarksMap[`BG-${b.chapter}-${b.verse}`] = true;
          }
        });
        setBookmarkedIds(bookmarksMap);
      })
      .catch((e) => console.error("Error loading bookmarks:", e));
  }, []);

  // Fetch verses when chapter changes
  useEffect(() => {
    if (selectedChapter !== null) {
      setVerses([]);
      setSelectedVerse(null);
      scriptureService.getChapterVerses(selectedChapter)
        .then((data) => {
          setVerses(data);
          if (data.length > 0) {
            setSelectedVerse(data[0]); // Select first verse by default
          }
        })
        .catch((e) => console.error(`Error loading verses for chapter ${selectedChapter}:`, e));
    }
  }, [selectedChapter]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const data = await scriptureService.searchVerses(searchQuery);
      setSearchResults(data);
      if (data.length > 0) {
        setSelectedVerse(data[0]);
      } else {
        setSelectedVerse(null);
      }
    } catch (e) {
      console.error("Search error:", e);
    } finally {
      setIsSearching(false);
    }
  };

  const handleBookmarkToggle = async (verse: Verse) => {
    const key = `BG-${verse.chapter}-${verse.verse}`;
    const isBookmarked = bookmarkedIds[key];

    if (isBookmarked) {
      // Find the bookmark ID and delete it
      try {
        const list = await scriptureService.getBookmarks();
        const found = list.find((b: any) => parseInt(b.chapter) === verse.chapter && parseInt(b.verse) === verse.verse);
        if (found) {
          await scriptureService.deleteBookmark(found.id);
          setBookmarkedIds((prev) => ({ ...prev, [key]: false }));
        }
      } catch (err) {
        console.error("Failed to delete bookmark:", err);
      }
    } else {
      // Add bookmark
      try {
        await scriptureService.addBookmark({
          book: "Bhagavad Gita",
          chapter: verse.chapter.toString(),
          verse: verse.verse.toString(),
          shloka: verse.shloka,
          translation: verse.english_meaning,
          meaning: verse.word_meaning
        });
        setBookmarkedIds((prev) => ({ ...prev, [key]: true }));
      } catch (err) {
        console.error("Failed to save bookmark:", err);
      }
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith(".pdf")) {
      setUploadStatus("error");
      setUploadMessage("Only PDF files are supported.");
      return;
    }

    setUploadStatus("uploading");
    setUploadMessage("Uploading and indexing PDF. This might take a few moments...");

    try {
      const resp = await scriptureService.uploadScripturePdf(file);
      setUploadStatus("success");
      setUploadMessage(resp.message || "Scripture PDF successfully uploaded and indexed!");
    } catch (err: any) {
      console.error("PDF upload error:", err);
      setUploadStatus("error");
      setUploadMessage(err.response?.data?.detail || "Failed to upload scripture document.");
    }
  };

  return (
    <div className="flex-1 flex flex-col h-screen bg-stone-50/50 dark:bg-[#120a05] overflow-hidden">
      {/* Page Header */}
      <header className="h-16 border-b border-stone-200 dark:border-stone-800 bg-white/70 dark:bg-[#18110b]/70 backdrop-blur-md px-6 flex items-center justify-between z-10 flex-shrink-0">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-saffron-500" />
          <span className="font-semibold text-stone-800 dark:text-stone-200">Bhagavad Gita Explorer</span>
        </div>
        
        {/* Toggle View Mode Buttons */}
        <div className="flex bg-stone-100 dark:bg-stone-800 p-1 rounded-xl border border-stone-200/50 dark:border-stone-700/50">
          <button
            onClick={() => { setViewMode("browse"); setSelectedChapter(1); }}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-205 ${
              viewMode === "browse"
                ? "bg-white dark:bg-[#120a05] text-saffron-600 dark:text-saffron-400 shadow-sm"
                : "text-stone-500 hover:text-stone-700 dark:hover:text-stone-300"
            }`}
          >
            Browse Chapters
          </button>
          <button
            onClick={() => setViewMode("search")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-205 ${
              viewMode === "search"
                ? "bg-white dark:bg-[#120a05] text-saffron-600 dark:text-saffron-400 shadow-sm"
                : "text-stone-500 hover:text-stone-700 dark:hover:text-stone-300"
            }`}
          >
            Search Verses
          </button>
        </div>
      </header>

      {/* Main Body Layout */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left Sidebar (Chapters list or search inputs) */}
        <div className="w-80 border-r border-stone-200 dark:border-stone-800 bg-white/40 dark:bg-[#18110b]/30 flex flex-col flex-shrink-0">
          {viewMode === "browse" ? (
            <div className="flex-1 overflow-y-auto p-4 space-y-1">
              <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest pl-2 mb-2 block">
                Chapters
              </span>
              {chapters.map((ch) => (
                <button
                  key={ch.chapter}
                  onClick={() => setSelectedChapter(ch.chapter)}
                  className={`w-full text-left px-4 py-3 rounded-xl text-xs font-semibold flex justify-between items-center transition-all ${
                    selectedChapter === ch.chapter
                      ? "bg-gradient-to-r from-saffron-500/10 to-gold-400/5 text-saffron-600 dark:text-saffron-400 border border-saffron-500/10 shadow-sm"
                      : "text-stone-600 dark:text-stone-400 hover:bg-stone-100 dark:hover:bg-stone-900/40"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-lg bg-stone-100 dark:bg-stone-850 flex items-center justify-center text-[10px] font-bold">
                      {ch.chapter}
                    </span>
                    <span>Chapter {ch.chapter}</span>
                  </div>
                  <span className="text-[10px] text-stone-400 font-medium">
                    {ch.verse_count} Verses
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <div className="flex-1 flex flex-col p-4 space-y-4">
              <form onSubmit={handleSearch} className="space-y-2">
                <label className="text-[10px] font-bold text-stone-400 uppercase tracking-widest pl-1">
                  Search keyword
                </label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="e.g. duty, yoga, mind..."
                      className="w-full pl-8 pr-3 py-2 text-xs bg-stone-100 dark:bg-[#18110b]/60 border border-stone-200 dark:border-stone-800 rounded-xl focus:outline-none focus:ring-1 focus:ring-saffron-500 text-stone-800 dark:text-stone-200"
                    />
                    <Search className="w-3.5 h-3.5 text-stone-400 absolute left-2.5 top-2.5" />
                  </div>
                  <button
                    type="submit"
                    disabled={isSearching || !searchQuery.trim()}
                    className="px-3 rounded-xl bg-saffron-500 text-white text-xs font-semibold hover:bg-saffron-600 active:scale-95 transition-all disabled:opacity-50"
                  >
                    Go
                  </button>
                </div>
              </form>

              {/* Search results */}
              <div className="flex-1 overflow-y-auto space-y-1">
                <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest pl-1 block mb-2">
                  Results ({searchResults.length})
                </span>
                
                {isSearching ? (
                  <div className="text-center py-6 text-xs text-stone-400 animate-pulse">
                    Searching vectors...
                  </div>
                ) : searchResults.length === 0 ? (
                  <div className="text-center py-6 text-xs text-stone-400 italic">
                    No results found.
                  </div>
                ) : (
                  searchResults.map((verse) => (
                    <button
                      key={verse.id}
                      onClick={() => setSelectedVerse(verse)}
                      className={`w-full text-left p-3 rounded-xl text-xs flex flex-col gap-1 border transition-all ${
                        selectedVerse?.id === verse.id
                          ? "bg-gradient-to-r from-saffron-500/10 to-gold-400/5 text-saffron-600 dark:text-saffron-400 border-saffron-500/20"
                          : "bg-white dark:bg-stone-900/10 hover:bg-stone-50 dark:hover:bg-stone-900/40 border-stone-200/50 dark:border-stone-800/40"
                      }`}
                    >
                      <div className="flex justify-between items-center font-bold">
                        <span>BG {verse.chapter}.{verse.verse}</span>
                        <ChevronRight className="w-3 h-3 text-stone-400" />
                      </div>
                      <p className="text-stone-500 dark:text-stone-400 line-clamp-2 leading-relaxed">
                        {verse.english_meaning}
                      </p>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}

          {/* PDF Scripture Uploader */}
          <div className="p-4 border-t border-stone-200 dark:border-stone-800 bg-stone-100/30 dark:bg-[#0c0603]/30">
            <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest pl-1 mb-2 block">
              Knowledge Base Uploader
            </span>
            <div className="relative group border border-dashed border-stone-200 dark:border-stone-800 rounded-xl hover:border-saffron-500/30 p-4 text-center transition-all bg-white/40 dark:bg-stone-900/20">
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileUpload}
                disabled={uploadStatus === "uploading"}
                className="absolute inset-0 opacity-0 cursor-pointer"
              />
              <UploadCloud className="w-6 h-6 mx-auto text-stone-400 group-hover:text-saffron-500 mb-1.5 transition-colors" />
              <span className="text-[10px] font-semibold text-stone-500 dark:text-stone-400 block">
                {uploadStatus === "uploading" ? "Uploading PDF..." : "Upload Scripture PDF"}
              </span>
              <span className="text-[9px] text-stone-400 block mt-0.5">PDF limit 10MB</span>
            </div>
            
            {uploadStatus !== "idle" && (
              <div className={`mt-3 p-3 rounded-lg border text-[10px] font-medium leading-normal flex items-start gap-2 ${
                uploadStatus === "success" 
                  ? "bg-green-500/5 border-green-500/10 text-green-600 dark:text-green-400" 
                  : uploadStatus === "uploading"
                    ? "bg-saffron-500/5 border-saffron-500/10 text-saffron-600 dark:text-saffron-400"
                    : "bg-red-500/5 border-red-500/10 text-red-600 dark:text-red-400"
              }`}>
                {uploadStatus === "success" ? <Check className="w-3.5 h-3.5 flex-shrink-0" /> : <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />}
                <span>{uploadMessage}</span>
              </div>
            )}
          </div>
        </div>

        {/* Center Display (Verse navigation or Detailed view) */}
        <div className="flex-1 flex overflow-hidden">
          {selectedChapter !== null && viewMode === "browse" && (
            <div className="w-72 border-r border-stone-200 dark:border-stone-800 overflow-y-auto p-4 space-y-1 bg-white/20 dark:bg-stone-900/10 flex-shrink-0">
              <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest pl-2 mb-2 block">
                Verses ({verses.length})
              </span>
              {verses.map((verse) => (
                <button
                  key={verse.id}
                  onClick={() => setSelectedVerse(verse)}
                  className={`w-full text-left px-4 py-3 rounded-xl text-xs font-semibold flex justify-between items-center transition-all ${
                    selectedVerse?.id === verse.id
                      ? "bg-stone-200/50 dark:bg-stone-800/40 text-stone-900 dark:text-stone-100 shadow-sm border border-stone-200/20"
                      : "text-stone-500 dark:text-stone-400 hover:bg-stone-100 dark:hover:bg-stone-900/30"
                  }`}
                >
                  <span>Verse {verse.verse}</span>
                  <ChevronRight className="w-3.5 h-3.5 text-stone-400" />
                </button>
              ))}
            </div>
          )}

          {/* Details Panel */}
          <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8 bg-white dark:bg-[#18110b]">
            {selectedVerse ? (
              <div className="max-w-2xl mx-auto space-y-6">
                
                {/* Verse citation and Bookmark */}
                <div className="flex justify-between items-center border-b border-stone-100 dark:border-stone-850 pb-4">
                  <div>
                    <h3 className="text-lg font-bold text-stone-800 dark:text-stone-200 tracking-wide font-sans">
                      Bhagavad Gita {selectedVerse.chapter}.{selectedVerse.verse}
                    </h3>
                    <p className="text-xs text-stone-400 dark:text-stone-500 uppercase tracking-widest font-semibold mt-0.5">
                      Scripture Passage
                    </p>
                  </div>
                  <button
                    onClick={() => handleBookmarkToggle(selectedVerse)}
                    className={`p-2.5 rounded-xl border flex items-center justify-center gap-1.5 text-xs font-semibold transition-all duration-200 ${
                      bookmarkedIds[`BG-${selectedVerse.chapter}-${selectedVerse.verse}`]
                        ? "bg-gradient-to-tr from-saffron-500/10 to-gold-400/5 text-saffron-600 dark:text-saffron-400 border-saffron-500/25 shadow-sm"
                        : "border-stone-200 dark:border-stone-800 hover:bg-stone-50 dark:hover:bg-stone-900 text-stone-500"
                    }`}
                  >
                    <Bookmark className={`w-4 h-4 ${bookmarkedIds[`BG-${selectedVerse.chapter}-${selectedVerse.verse}`] ? "fill-current text-saffron-500" : ""}`} />
                    <span>{bookmarkedIds[`BG-${selectedVerse.chapter}-${selectedVerse.verse}`] ? "Bookmarked" : "Save"}</span>
                  </button>
                </div>

                {/* Sanskrit Shloka Box */}
                <div className="py-8 px-6 rounded-2xl bg-[#fffcf5] dark:bg-[#1e140d]/40 border border-saffron-500/10 text-center space-y-4 shadow-sm shadow-saffron-500/[0.01]">
                  <p className="text-lg md:text-xl font-bold text-saffron-700 dark:text-saffron-400 font-sans tracking-wide leading-loose">
                    {selectedVerse.shloka}
                  </p>
                </div>

                {/* Transliteration */}
                {selectedVerse.transliteration && (
                  <div className="space-y-1">
                    <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest block">
                      Transliteration
                    </span>
                    <p className="text-sm text-stone-600 dark:text-stone-400 italic leading-relaxed">
                      {selectedVerse.transliteration}
                    </p>
                  </div>
                )}

                {/* Word Meaning */}
                {selectedVerse.word_meaning && (
                  <div className="space-y-2">
                    <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest block">
                      Word-by-word meaning
                    </span>
                    <p className="text-xs text-stone-600 dark:text-stone-400 leading-relaxed bg-stone-50 dark:bg-stone-900/30 p-4 rounded-xl border border-stone-100 dark:border-stone-850">
                      {selectedVerse.word_meaning}
                    </p>
                  </div>
                )}

                {/* English Translation */}
                {selectedVerse.english_meaning && (
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest block">
                      English Translation
                    </span>
                    <p className="text-sm font-semibold text-stone-800 dark:text-stone-250 leading-relaxed font-sans">
                      {selectedVerse.english_meaning}
                    </p>
                  </div>
                )}

                {/* Hindi Meaning */}
                {selectedVerse.hindi_meaning && (
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest block">
                      हिन्दी अनुवाद (Hindi Meaning)
                    </span>
                    <p className="text-sm text-stone-700 dark:text-stone-300 leading-relaxed">
                      {selectedVerse.hindi_meaning}
                    </p>
                  </div>
                )}

              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-stone-400 dark:text-stone-650 space-y-4">
                <FileText className="w-12 h-12 text-stone-300 dark:text-stone-800" />
                <p className="text-sm italic">
                  Select a chapter and verse from the navigation menu to browse.
                </p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
export default ScriptureExplorer;
