import axios from "axios";

// Backend origin. Set API_BASE_URL in the hosting dashboard (Vercel ->
// Settings -> Environment Variables) to the deployed backend URL; it is baked
// in at build time, so changing it needs a redeploy. Falls back to the local
// dev server. The trailing slash is stripped because these paths are joined
// by string concatenation for the SSE and audio URLs, and "//api/..." 404s.
const API_BASE_URL = (
  import.meta.env.API_BASE_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export interface Citation {
  id: number;
  source: string;
  reference: string;
  url?: string;
  snippet: string;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
  language: string;
  citations?: Citation[];
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  language: string;
}

export interface AdminMetrics {
  db_stats: {
    sessions: number;
    messages: number;
    bookmarks: number;
    feedback: number;
    db_size_kb: number;
  };
  vector_stats: {
    gita_index_size: number;
    scriptures_index_size: number;
  };
  system_health: {
    gpu_acceleration: boolean;
    gpu_device_name: string;
    pytorch_version: string;
  };
  keys_configured: {
    google_gemini: boolean;
    groq: boolean;
    tavily: boolean;
    assemblyai: boolean;
  };
}

export interface Verse {
  id: string;
  chapter: number;
  verse: number;
  shloka: string;
  transliteration: string;
  hindi_meaning: string;
  english_meaning: string;
  word_meaning: string;
}

export const chatService = {
  createSession: async (title: string, language: string = "en"): Promise<ChatSession> => {
    const resp = await api.post("/api/db/sessions", { title, language });
    return resp.data;
  },
  
  getSessions: async (): Promise<ChatSession[]> => {
    const resp = await api.get("/api/db/sessions");
    return resp.data;
  },
  
  deleteSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/api/db/sessions/${sessionId}`);
  },
  
  getMessages: async (sessionId: string): Promise<ChatMessage[]> => {
    const resp = await api.get(`/api/db/sessions/${sessionId}/messages`);
    return resp.data;
  },
  
  sendMessageSync: async (sessionId: string, text: string): Promise<any> => {
    const resp = await api.post("/api/chat", { session_id: sessionId, text });
    return resp.data;
  },
  
  sendVoiceMessage: async (sessionId: string, audioBlob: Blob): Promise<any> => {
    const formData = new FormData();
    formData.append("session_id", sessionId);
    formData.append("file", audioBlob, "query.wav");
    
    const resp = await api.post("/api/voice", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return resp.data;
  },
  
  submitFeedback: async (messageId: string, score: number, comments?: string): Promise<void> => {
    await api.post("/api/db/feedback", { message_id: messageId, score, comments });
  },
};

export const scriptureService = {
  getChapters: async (): Promise<{ chapter: number; verse_count: number }[]> => {
    const resp = await api.get("/api/scriptures/gita/chapters");
    return resp.data;
  },
  
  getChapterVerses: async (chapter: number): Promise<Verse[]> => {
    const resp = await api.get(`/api/scriptures/gita/chapters/${chapter}`);
    return resp.data;
  },
  
  getSpecificVerse: async (chapter: number, verse: number): Promise<Verse> => {
    const resp = await api.get(`/api/scriptures/gita/chapters/${chapter}/verses/${verse}`);
    return resp.data;
  },
  
  searchVerses: async (query: string): Promise<Verse[]> => {
    const resp = await api.get("/api/scriptures/search", { params: { query } });
    return resp.data;
  },
  
  addBookmark: async (bookmark: {
    book: string;
    chapter?: string;
    verse?: string;
    shloka?: string;
    translation?: string;
    meaning?: string;
  }): Promise<any> => {
    const resp = await api.post("/api/db/bookmarks", bookmark);
    return resp.data;
  },
  
  getBookmarks: async (): Promise<any[]> => {
    const resp = await api.get("/api/db/bookmarks");
    return resp.data;
  },
  
  deleteBookmark: async (bookmarkId: number): Promise<void> => {
    await api.delete(`/api/db/bookmarks/${bookmarkId}`);
  },
  
  uploadScripturePdf: async (pdfFile: File): Promise<any> => {
    const formData = new FormData();
    formData.append("file", pdfFile);
    
    const resp = await api.post("/api/scriptures/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return resp.data;
  },
};

export const adminService = {
  getMetrics: async (): Promise<AdminMetrics> => {
    const resp = await api.get("/api/admin/metrics");
    return resp.data;
  },
  
  getLogs: async (lines: number = 100): Promise<{ logs: string; total_lines: number }> => {
    const resp = await api.get("/api/admin/logs", { params: { lines } });
    return resp.data;
  },
};
export { API_BASE_URL };
