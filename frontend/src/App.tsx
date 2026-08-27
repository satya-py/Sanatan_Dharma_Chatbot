import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import Chat from "./pages/Chat";
import VoiceAssistant from "./pages/VoiceAssistant";
import ScriptureExplorer from "./pages/ScriptureExplorer";
import Bookmarks from "./pages/Bookmarks";
import AdminDashboard from "./pages/AdminDashboard";
import { chatService } from "./services/api";

function App() {
  const [activeTab, setActiveTab] = useState<string>("chat");
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  // Fetch session history and select the latest session on mount
  useEffect(() => {
    const initializeSession = async () => {
      try {
        const sessions = await chatService.getSessions();
        if (sessions.length > 0) {
          setCurrentSessionId(sessions[0].id);
        } else {
          // If no session exists, create a default first chat session
          const newSession = await chatService.createSession("New Chat");
          setCurrentSessionId(newSession.id);
        }
      } catch (err) {
        console.error("Failed to initialize session:", err);
      }
    };

    initializeSession();
  }, []);

  const handleSelectSession = (id: string) => {
    setCurrentSessionId(id);
  };

  const handleCreateSession = async () => {
    try {
      const newSession = await chatService.createSession("New Chat");
      setCurrentSessionId(newSession.id);
      setActiveTab("chat");
    } catch (err) {
      console.error("Failed to create new chat session:", err);
    }
  };

  // Render active view mode page
  const renderActivePage = () => {
    switch (activeTab) {
      case "chat":
        return (
          <Chat 
            currentSessionId={currentSessionId} 
            onCreateSession={handleCreateSession} 
          />
        );
      case "voice":
        return (
          <VoiceAssistant 
            currentSessionId={currentSessionId} 
            onCreateSession={handleCreateSession} 
          />
        );
      case "scriptures":
        return <ScriptureExplorer />;
      case "bookmarks":
        return <Bookmarks />;
      case "admin":
        return <AdminDashboard />;
      default:
        return (
          <Chat 
            currentSessionId={currentSessionId} 
            onCreateSession={handleCreateSession} 
          />
        );
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-stone-50/50 dark:bg-[#120a05] antialiased">
      {/* Devotional Sidebar */}
      <Sidebar
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onCreateSession={handleCreateSession}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />
      
      {/* Dynamic Main Workspace Content */}
      <main className="flex-1 h-full flex flex-col overflow-hidden">
        {renderActivePage()}
      </main>
    </div>
  );
}

export default App;
