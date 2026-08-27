import React, { useEffect, useState } from "react";
import { 
  MessageSquare, 
  BookOpen, 
  Bookmark, 
  ShieldAlert, 
  Trash2, 
  Plus, 
  Moon, 
  Sun,
  LayoutDashboard,
  Mic
} from "lucide-react";
import { chatService, type ChatSession } from "../services/api";

interface SidebarProps {
  currentSessionId: string | null;
  onSelectSession: (id: string) => void;
  onCreateSession: () => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentSessionId,
  onSelectSession,
  onCreateSession,
  activeTab,
  setActiveTab,
}) => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [isDarkMode, setIsDarkMode] = useState<boolean>(true);

  // Load chat sessions from API
  const loadSessions = async () => {
    try {
      const data = await chatService.getSessions();
      setSessions(data);
    } catch (e) {
      console.error("Failed to load chat history:", e);
    }
  };

  useEffect(() => {
    loadSessions();
  }, [currentSessionId]);

  // Toggle Theme between Dark and Light mode
  const toggleTheme = () => {
    const root = window.document.documentElement;
    if (isDarkMode) {
      root.classList.remove("dark");
      setIsDarkMode(false);
    } else {
      root.classList.add("dark");
      setIsDarkMode(true);
    }
  };

  // Delete chat session
  const handleDeleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm("Are you sure you want to delete this chat session?")) {
      try {
        await chatService.deleteSession(id);
        loadSessions();
        if (currentSessionId === id) {
          onCreateSession();
        }
      } catch (err) {
        console.error("Error deleting session:", err);
      }
    }
  };

  const navItems = [
    { id: "chat", label: "AI Chatbot", icon: MessageSquare },
    { id: "voice", label: "Voice Assistant", icon: Mic },
    { id: "scriptures", label: "Scripture Explorer", icon: BookOpen },
    { id: "bookmarks", label: "Saved Bookmarks", icon: Bookmark },
    { id: "admin", label: "Admin Panel", icon: LayoutDashboard },
  ];

  return (
    <aside className="w-80 h-screen flex flex-col border-r border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-[#120a05] text-stone-700 dark:text-stone-300">
      {/* Devotional Header */}
      <div className="p-6 border-b border-stone-200 dark:border-stone-800 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-saffron-500 to-gold-400 flex items-center justify-center text-white font-bold text-lg shadow-md animate-pulse">
          ॐ
        </div>
        <div>
          <h1 className="font-bold text-lg text-saffron-600 dark:text-saffron-400 tracking-wide font-sans">
            Sanatana Dharma
          </h1>
          <p className="text-xs text-stone-400 dark:text-stone-500 uppercase tracking-widest font-medium">
            ISKCON Companion
          </p>
        </div>
      </div>

      {/* Nav Tab items */}
      <nav className="p-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                isActive 
                  ? "bg-gradient-to-r from-saffron-500/10 to-gold-400/5 text-saffron-600 dark:text-saffron-400 border border-saffron-500/20 shadow-sm" 
                  : "hover:bg-stone-200/50 dark:hover:bg-stone-800/40 text-stone-600 dark:text-stone-400"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-saffron-500" : ""}`} />
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* Chat History List (only visible when in Chat or Voice tabs) */}
      <div className="flex-1 flex flex-col overflow-hidden px-4 border-t border-stone-200/50 dark:border-stone-800/50 mt-2">
        <div className="py-3 px-2 flex justify-between items-center text-xs font-semibold text-stone-400 dark:text-stone-500 uppercase tracking-widest">
          <span>Recent Conversations</span>
          <button
            onClick={onCreateSession}
            title="Start New Chat"
            className="p-1 rounded-md hover:bg-stone-200 dark:hover:bg-stone-800 text-saffron-600 dark:text-saffron-400 transition-colors"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto space-y-1 pr-1">
          {sessions.length === 0 ? (
            <div className="text-center py-6 text-xs text-stone-400 dark:text-stone-600">
              No recent chats.
            </div>
          ) : (
            sessions.map((s) => (
              <div
                key={s.id}
                onClick={() => {
                  setActiveTab("chat");
                  onSelectSession(s.id);
                }}
                className={`group flex justify-between items-center px-4 py-3 rounded-xl text-xs font-medium cursor-pointer transition-all duration-150 ${
                  currentSessionId === s.id && activeTab === "chat"
                    ? "bg-stone-200/70 dark:bg-stone-800/50 text-stone-900 dark:text-stone-100 font-semibold"
                    : "text-stone-500 dark:text-stone-400 hover:bg-stone-100 dark:hover:bg-stone-900/30"
                }`}
              >
                <div className="flex items-center gap-2 overflow-hidden mr-2">
                  <MessageSquare className="w-3.5 h-3.5 flex-shrink-0 text-stone-400" />
                  <span className="truncate">{s.title}</span>
                </div>
                <button
                  onClick={(e) => handleDeleteSession(e, s.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/10 text-stone-400 hover:text-red-500 transition-all duration-150"
                  title="Delete Chat"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Footer Settings & Theme Switch */}
      <div className="p-4 border-t border-stone-200 dark:border-stone-800 flex flex-col gap-2 bg-stone-100/40 dark:bg-[#0c0603]">
        <div className="flex items-center justify-between">
          <span className="text-xs text-stone-400 dark:text-stone-500">Theme</span>
          <button 
            onClick={toggleTheme}
            className="p-2 rounded-xl bg-stone-200 dark:bg-stone-800 hover:bg-stone-300 dark:hover:bg-stone-700 text-stone-700 dark:text-stone-300 transition-colors"
          >
            {isDarkMode ? <Sun className="w-4 h-4 text-gold-400" /> : <Moon className="w-4 h-4 text-saffron-600" />}
          </button>
        </div>

        <div className="flex items-center justify-between text-xs text-stone-400 dark:text-stone-500 pt-1">
          <span className="flex items-center gap-1.5 hover:underline cursor-pointer">
            <ShieldAlert className="w-3.5 h-3.5" /> Privacy & Terms
          </span>
          <span>v1.0.0</span>
        </div>
      </div>
    </aside>
  );
};
export default Sidebar;
