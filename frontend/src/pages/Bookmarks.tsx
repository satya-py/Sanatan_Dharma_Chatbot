import React, { useState, useEffect } from "react";
import { Bookmark, Trash2, BookOpen, AlertCircle } from "lucide-react";
import { scriptureService } from "../services/api";

export const Bookmarks: React.FC = () => {
  const [bookmarks, setBookmarks] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadBookmarks = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await scriptureService.getBookmarks();
      setBookmarks(data);
    } catch (err) {
      console.error("Failed to load bookmarks:", err);
      setError("Could not retrieve bookmarked verses.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadBookmarks();
  }, []);

  const handleDeleteBookmark = async (id: number) => {
    if (confirm("Are you sure you want to remove this bookmark?")) {
      try {
        await scriptureService.deleteBookmark(id);
        // Refresh local state
        setBookmarks((prev) => prev.filter((b) => b.id !== id));
      } catch (err) {
        console.error("Failed to delete bookmark:", err);
      }
    }
  };

  return (
    <div className="flex-1 flex flex-col h-screen bg-stone-50/50 dark:bg-[#120a05] overflow-hidden">
      {/* Page Header */}
      <header className="h-16 border-b border-stone-200 dark:border-stone-800 bg-white/70 dark:bg-[#18110b]/70 backdrop-blur-md px-6 flex items-center justify-between z-10 flex-shrink-0">
        <div className="flex items-center gap-2">
          <Bookmark className="w-5 h-5 text-saffron-500 fill-current" />
          <span className="font-semibold text-stone-800 dark:text-stone-200">Saved Bookmarks</span>
        </div>
      </header>

      {/* Main content display */}
      <div className="flex-1 overflow-y-auto p-6 md:p-8">
        <div className="max-w-3xl mx-auto space-y-6">
          <div className="space-y-1">
            <h2 className="text-xl font-bold text-stone-800 dark:text-stone-200 font-sans tracking-wide">
              Your Bookmarked Verses
            </h2>
            <p className="text-xs text-stone-400 dark:text-stone-500 uppercase tracking-widest font-semibold">
              Persisted Wisdom & Teachings
            </p>
          </div>

          {isLoading ? (
            <div className="text-center py-12 text-xs text-stone-400 dark:text-stone-600 animate-pulse">
              Loading bookmarks...
            </div>
          ) : error ? (
            <div className="p-4 bg-red-500/10 border border-red-500/25 text-red-600 dark:text-red-400 rounded-2xl flex items-center gap-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span className="text-xs font-semibold">{error}</span>
            </div>
          ) : bookmarks.length === 0 ? (
            <div className="text-center py-20 border border-dashed border-stone-200 dark:border-stone-800 rounded-3xl p-8 bg-white/40 dark:bg-stone-900/10 space-y-4">
              <BookOpen className="w-12 h-12 text-stone-300 dark:text-stone-800 mx-auto" />
              <div className="space-y-1">
                <h3 className="font-semibold text-sm text-stone-700 dark:text-stone-300">No bookmarks saved yet</h3>
                <p className="text-xs text-stone-400 dark:text-stone-550 max-w-xs mx-auto">
                  Browse the Scripture Explorer and click the save button on any verse to store it here.
                </p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6">
              {bookmarks.map((b) => (
                <div
                  key={b.id}
                  className="rounded-3xl border border-stone-200/60 dark:border-stone-800/60 bg-white dark:bg-[#18110b] p-6 shadow-sm hover:shadow-md transition-all duration-200 relative group"
                >
                  {/* Delete Bookmark Button */}
                  <button
                    onClick={() => handleDeleteBookmark(b.id)}
                    className="absolute top-5 right-5 p-2 rounded-xl hover:bg-red-500/5 text-stone-400 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                    title="Remove bookmark"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>

                  <div className="space-y-4 pr-8">
                    {/* Source label */}
                    <div>
                      <span className="text-xs font-bold text-saffron-600 dark:text-saffron-400">
                        {b.book || "Bhagavad Gita"}
                      </span>
                      <h4 className="text-sm font-bold text-stone-800 dark:text-stone-250">
                        Chapter {b.chapter}, Verse {b.verse}
                      </h4>
                    </div>

                    {/* Sanskrit Shloka */}
                    {b.shloka && (
                      <div className="p-4 rounded-2xl bg-[#fffcf5] dark:bg-[#1e140d]/30 border border-saffron-500/5 text-center">
                        <p className="text-sm font-semibold text-saffron-700 dark:text-saffron-400 font-sans tracking-wide leading-relaxed">
                          {b.shloka}
                        </p>
                      </div>
                    )}

                    {/* Translation */}
                    {b.translation && (
                      <div className="space-y-1">
                        <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest block">
                          English Translation
                        </span>
                        <p className="text-xs text-stone-600 dark:text-stone-400 leading-relaxed italic">
                          "{b.translation}"
                        </p>
                      </div>
                    )}

                    {/* Word Meaning */}
                    {b.meaning && (
                      <div className="space-y-1">
                        <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest block">
                          Word-by-word meaning
                        </span>
                        <p className="text-xs text-stone-500 dark:text-stone-500 leading-relaxed">
                          {b.meaning}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default Bookmarks;
