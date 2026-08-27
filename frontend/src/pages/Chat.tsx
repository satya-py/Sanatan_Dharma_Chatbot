import React, { useState, useEffect, useRef } from "react";
import { Send, ThumbsUp, ThumbsDown, MessageSquare, Volume2, Globe, AlertCircle, Copy, Check } from "lucide-react";
import { chatService as chatAPI, type ChatMessage, API_BASE_URL } from "../services/api";

interface ChatProps {
  currentSessionId: string | null;
  onCreateSession: () => void;
}

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी (Hindi)" },
  { code: "bn", label: "বাংলা (Bengali)" },
  { code: "gu", label: "ગુજરાતી (Gujarati)" },
  { code: "mr", label: "मराठी (Marathi)" },
  { code: "ta", label: "தமிழ் (Tamil)" },
  { code: "te", label: "తెలుగు (Telugu)" },
  { code: "kn", label: "ಕನ್ನಡ (Kannada)" },
  { code: "ml", label: "മലയാളം (Malayalam)" },
  { code: "sa", label: "संस्कृतम् (Sanskrit)" },
  { code: "pa", label: "ਪੰਜਾਬੀ (Punjabi)" }
];

export const Chat: React.FC<ChatProps> = ({ currentSessionId, onCreateSession }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [selectedLang, setSelectedLang] = useState("en");
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  
  // Feedback states
  const [ratedMessages, setRatedMessages] = useState<Record<string, "up" | "down">>({});
  const [feedbackComment, setFeedbackComment] = useState<string>("");
  const [activeFeedbackId, setActiveFeedbackId] = useState<string | null>(null);
  
  // Audio state
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
  
  // Copied text state
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Fetch history when currentSessionId changes
  useEffect(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    
    if (currentSessionId) {
      setIsLoading(true);
      setErrorMsg(null);
      chatAPI.getMessages(currentSessionId)
        .then((data: ChatMessage[]) => {
          setMessages(data);
          setIsLoading(false);
          setTimeout(scrollToBottom, 50);
        })
        .catch((err: any) => {
          console.error("Failed to load messages:", err);
          setErrorMsg("Could not retrieve conversation history.");
          setIsLoading(false);
        });
    } else {
      setMessages([]);
    }
  }, [currentSessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, statusMessage]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    let activeSessionId = currentSessionId;
    
    // Create new session if none exists
    if (!activeSessionId) {
      try {
        setIsLoading(true);
        const newSession = await chatAPI.createSession(`Chat in ${LANGUAGES.find(l => l.code === selectedLang)?.label || 'English'}`, selectedLang);
        activeSessionId = newSession.id;
        // Trigger session selection in parent component
        onCreateSession(); 
        // Manually push standard react callback state or let parent handle
      } catch (err) {
        console.error("Failed to create session:", err);
        setErrorMsg("Failed to start a new chat session.");
        setIsLoading(false);
        return;
      }
    }

    const userText = inputText;
    setInputText("");
    setErrorMsg(null);
    setIsLoading(true);
    setStatusMessage("Hare Krishna! Processing...");

    // Optimistically add User Message
    const userMessage: ChatMessage = {
      id: Math.random().toString(),
      sender: "user",
      text: userText,
      timestamp: new Date().toISOString(),
      language: selectedLang
    };
    setMessages((prev) => [...prev, userMessage]);

    // Setup streaming connection
    const streamUrl = `${API_BASE_URL}/api/chat/stream?session_id=${activeSessionId}&text=${encodeURIComponent(userText)}`;
    
    const eventSource = new EventSource(streamUrl);
    eventSourceRef.current = eventSource;

    // Temporary placeholder for streaming assistant response
    const assistantMessageId = "stream-" + Date.now();
    let assistantText = "";
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === "status") {
          setStatusMessage(data.message);
        } else if (data.type === "text") {
          assistantText = data.full_text;
          setMessages((prev) => {
            const filtered = prev.filter((m) => m.id !== assistantMessageId);
            const newMessage: ChatMessage = {
              id: assistantMessageId,
              sender: "assistant",
              text: assistantText,
              timestamp: new Date().toISOString(),
              language: selectedLang
            };
            return [...filtered, newMessage];
          });
          setStatusMessage(null); // Clear status once text streams in
        } else if (data.type === "done") {
          eventSource.close();
          eventSourceRef.current = null;
          setIsLoading(false);
          setStatusMessage(null);
          
          // Replace temp streaming message with final server-saved message
          setMessages((prev) => {
            const filtered = prev.filter((m) => m.id !== assistantMessageId);
            const finalMessage: ChatMessage = {
              id: data.message_id,
              sender: "assistant",
              text: assistantText,
              timestamp: new Date().toISOString(),
              language: selectedLang,
              citations: data.citations
            };
            return [...filtered, finalMessage];
          });
        } else if (data.type === "error") {
          console.error("SSE stream error event:", data.message);
          setErrorMsg(data.message);
          eventSource.close();
          eventSourceRef.current = null;
          setIsLoading(false);
          setStatusMessage(null);
        }
      } catch (err) {
        console.error("Error parsing stream content:", err);
      }
    };

    eventSource.onerror = (err) => {
      console.error("EventSource failed:", err);
      setErrorMsg("Connection lost. Please try again.");
      eventSource.close();
      eventSourceRef.current = null;
      setIsLoading(false);
      setStatusMessage(null);
    };
  };

  const handleFeedback = async (messageId: string, rating: "up" | "down") => {
    try {
      const score = rating === "up" ? 1 : -1;
      await chatAPI.submitFeedback(messageId, score);
      setRatedMessages((prev) => ({ ...prev, [messageId]: rating }));
      if (rating === "down") {
        setActiveFeedbackId(messageId);
        setFeedbackComment("");
      }
    } catch (err) {
      console.error("Failed to submit rating:", err);
    }
  };

  const handleCommentSubmit = async (messageId: string) => {
    try {
      await chatAPI.submitFeedback(messageId, -1, feedbackComment);
      setActiveFeedbackId(null);
      setFeedbackComment("");
    } catch (err) {
      console.error("Failed to submit detailed feedback:", err);
    }
  };

  const handleCopyText = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleTextToSpeech = (text: string, id: string) => {
    if (speakingMessageId === id) {
      window.speechSynthesis.cancel();
      setSpeakingMessageId(null);
      return;
    }

    window.speechSynthesis.cancel();
    // Remove formatting headers for smoother speech
    const cleanText = text.replace(/###/g, "").replace(/\*\*?/g, "");
    const utterance = new SpeechSynthesisUtterance(cleanText);
    
    // Choose appropriate voice based on selected/detected language
    utterance.lang = selectedLang;
    
    utterance.onend = () => {
      setSpeakingMessageId(null);
    };
    utterance.onerror = () => {
      setSpeakingMessageId(null);
    };

    setSpeakingMessageId(id);
    window.speechSynthesis.speak(utterance);
  };

  // Helper to format structured scriptural answers beautifully
  const renderFormattedMessageText = (text: string) => {
    const sections = text.split(/(?=### )/);
    return sections.map((section, idx) => {
      if (section.startsWith("### ")) {
        const titleEnd = section.indexOf("\n");
        const title = section.slice(4, titleEnd).trim();
        const content = section.slice(titleEnd).trim();
        
        return (
          <div key={idx} className="mb-4">
            <h4 className="text-saffron-600 dark:text-saffron-400 font-semibold text-sm border-b border-saffron-500/10 pb-1 mb-2 tracking-wide uppercase font-sans">
              {title}
            </h4>
            <div className="text-stone-700 dark:text-stone-300 text-sm whitespace-pre-line leading-relaxed pl-1">
              {content}
            </div>
          </div>
        );
      }
      return (
        <p key={idx} className="text-stone-700 dark:text-stone-300 text-sm mb-4 leading-relaxed whitespace-pre-line">
          {section}
        </p>
      );
    });
  };

  return (
    <div className="flex-1 flex flex-col h-screen bg-stone-50/50 dark:bg-[#120a05] overflow-hidden">
      {/* Top Header */}
      <header className="h-16 border-b border-stone-200 dark:border-stone-800 bg-white/70 dark:bg-[#18110b]/70 backdrop-blur-md px-6 flex items-center justify-between z-10">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-saffron-500" />
          <span className="font-semibold text-stone-800 dark:text-stone-200">AI Scriptural Chatbot</span>
        </div>
        
        {/* Language Selection */}
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-stone-400" />
          <select
            value={selectedLang}
            onChange={(e) => setSelectedLang(e.target.value)}
            className="text-xs bg-stone-100 dark:bg-stone-800 border border-stone-200 dark:border-stone-700 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-saffron-500 text-stone-700 dark:text-stone-300 font-medium"
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </div>
      </header>

      {/* Main Chat Display */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {messages.length === 0 ? (
          <div className="max-w-2xl mx-auto text-center mt-12 space-y-6 p-8 rounded-3xl border border-stone-200/50 dark:border-stone-800/40 bg-white/50 dark:bg-[#18110b]/30 shadow-sm backdrop-blur-sm">
            <div className="w-16 h-16 mx-auto bg-gradient-to-tr from-saffron-500 to-gold-400 rounded-full flex items-center justify-center text-white text-2xl font-bold shadow-md shadow-saffron-500/10">
              ॐ
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-bold text-stone-800 dark:text-stone-200 font-sans tracking-wide">
                Ask the Sanatana Dharma Assistant
              </h2>
              <p className="text-sm text-stone-500 dark:text-stone-400 max-w-md mx-auto leading-relaxed">
                Seek guidance from the Bhagavad Gita, Upanishads, Mahabharata, Vedas, and Srimad Bhagavatam. Ask questions in English, Hindi, Bengali, or other Indian languages.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-left max-w-lg mx-auto pt-2">
              <button
                onClick={() => setInputText("What is Lord Krishna's teaching on Nishkama Karma in Gita?")}
                className="p-3 text-xs rounded-xl border border-stone-200 dark:border-stone-800 hover:border-saffron-500/30 bg-stone-50 dark:bg-stone-900/30 text-stone-600 dark:text-stone-400 hover:text-saffron-600 dark:hover:text-saffron-400 hover:bg-saffron-500/5 transition-all text-left"
              >
                "What is Lord Krishna's teaching on Nishkama Karma in Gita?"
              </button>
              <button
                onClick={() => setInputText("How does one attain mental peace according to Upanishads?")}
                className="p-3 text-xs rounded-xl border border-stone-200 dark:border-stone-800 hover:border-saffron-500/30 bg-stone-50 dark:bg-stone-900/30 text-stone-600 dark:text-stone-400 hover:text-saffron-600 dark:hover:text-saffron-400 hover:bg-saffron-500/5 transition-all text-left"
              >
                "How does one attain mental peace according to Upanishads?"
              </button>
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((msg) => {
              const isUser = msg.sender === "user";
              return (
                <div key={msg.id} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[85%] rounded-3xl p-6 shadow-sm border ${
                      isUser
                        ? "bg-gradient-to-tr from-saffron-500/90 to-saffron-600 text-white border-saffron-500/20"
                        : "bg-white dark:bg-[#18110b] text-stone-800 dark:text-stone-200 border-stone-200 dark:border-stone-800"
                    }`}
                  >
                    {/* Message Body */}
                    {isUser ? (
                      <p className="text-sm whitespace-pre-line leading-relaxed">{msg.text}</p>
                    ) : (
                      <div className="space-y-4">
                        {renderFormattedMessageText(msg.text)}

                        {/* Citations List */}
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="mt-4 pt-4 border-t border-stone-100 dark:border-stone-800/80">
                            <span className="text-xs font-bold text-stone-400 dark:text-stone-500 uppercase tracking-widest block mb-2">
                              Retrieved Passages & References
                            </span>
                            <div className="grid grid-cols-1 gap-2">
                              {msg.citations.map((cit) => (
                                <div
                                  key={cit.id}
                                  className="p-3 rounded-xl bg-stone-50 dark:bg-stone-900/40 border border-stone-100 dark:border-stone-800/60"
                                >
                                  <div className="flex justify-between items-start mb-1 text-xs">
                                    <span className="font-bold text-saffron-600 dark:text-saffron-400">
                                      {cit.source}
                                    </span>
                                    <span className="text-stone-400 font-medium">
                                      {cit.reference}
                                    </span>
                                  </div>
                                  <p className="text-xs text-stone-500 dark:text-stone-400 italic leading-relaxed">
                                    "{cit.snippet}"
                                  </p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Message Toolbar Actions */}
                        <div className="flex items-center justify-between pt-2 text-stone-400 dark:text-stone-500 border-t border-stone-100 dark:border-stone-800/80 mt-2">
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleCopyText(msg.text, msg.id)}
                              className="p-1.5 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
                              title="Copy response"
                            >
                              {copiedId === msg.id ? (
                                <Check className="w-4 h-4 text-green-500" />
                              ) : (
                                <Copy className="w-4 h-4" />
                              )}
                            </button>
                            <button
                              onClick={() => handleTextToSpeech(msg.text, msg.id)}
                              className={`p-1.5 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors ${
                                speakingMessageId === msg.id ? "text-saffron-500" : ""
                              }`}
                              title="Speak response"
                            >
                              <Volume2 className="w-4 h-4" />
                            </button>
                          </div>

                          <div className="flex gap-1">
                            <button
                              onClick={() => handleFeedback(msg.id, "up")}
                              className={`p-1.5 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors ${
                                ratedMessages[msg.id] === "up" ? "text-green-500" : ""
                              }`}
                              title="Helpful response"
                            >
                              <ThumbsUp className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleFeedback(msg.id, "down")}
                              className={`p-1.5 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors ${
                                ratedMessages[msg.id] === "down" ? "text-red-500" : ""
                              }`}
                              title="Unhelpful or inaccurate response"
                            >
                              <ThumbsDown className="w-4 h-4" />
                            </button>
                          </div>
                        </div>

                        {/* Detailed feedback input */}
                        {activeFeedbackId === msg.id && (
                          <div className="mt-3 p-3 rounded-xl bg-red-500/5 border border-red-500/10 space-y-2">
                            <span className="text-xs text-stone-500 dark:text-stone-400 font-medium">
                              Help us improve: What was incorrect or ungrounded?
                            </span>
                            <textarea
                              value={feedbackComment}
                              onChange={(e) => setFeedbackComment(e.target.value)}
                              rows={2}
                              className="w-full p-2.5 text-xs bg-white dark:bg-[#120a05] border border-stone-200 dark:border-stone-800 rounded-lg text-stone-800 dark:text-stone-200 focus:outline-none focus:ring-1 focus:ring-red-500"
                              placeholder="e.g. invalid citation Chapter 2 Verse 47..."
                            />
                            <div className="flex justify-end gap-2">
                              <button
                                onClick={() => setActiveFeedbackId(null)}
                                className="px-3 py-1.5 rounded-lg text-xs bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400 hover:bg-stone-200 dark:hover:bg-stone-700"
                              >
                                Cancel
                              </button>
                              <button
                                onClick={() => handleCommentSubmit(msg.id)}
                                className="px-3 py-1.5 rounded-lg text-xs bg-red-500 text-white hover:bg-red-600 transition-colors"
                              >
                                Submit Feedback
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Transition Loaders */}
        {isLoading && statusMessage && (
          <div className="max-w-3xl mx-auto flex justify-start">
            <div className="rounded-3xl p-5 border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#18110b] flex items-center gap-3">
              <div className="w-4 h-4 rounded-full border-2 border-saffron-500 border-t-transparent animate-spin"></div>
              <span className="text-xs font-semibold text-stone-600 dark:text-stone-400 animate-pulse font-sans">
                {statusMessage}
              </span>
            </div>
          </div>
        )}

        {/* Error message */}
        {errorMsg && (
          <div className="max-w-3xl mx-auto p-4 bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 rounded-2xl flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="text-xs font-medium">{errorMsg}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Message Input Area */}
      <div className="p-6 border-t border-stone-200 dark:border-stone-800 bg-white/70 dark:bg-[#18110b]/70 backdrop-blur-md">
        <form onSubmit={handleSendMessage} className="max-w-3xl mx-auto flex items-center gap-3">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={isLoading}
            className="flex-1 bg-stone-100 dark:bg-[#1e140d]/40 border border-stone-200/80 dark:border-stone-800/80 rounded-2xl px-5 py-4 text-sm focus:outline-none focus:ring-1 focus:ring-saffron-500 text-stone-800 dark:text-stone-200 placeholder-stone-400 dark:placeholder-stone-600 shadow-inner"
            placeholder="Type your question (e.g. Explain how to manage anger in Bhagavad Gita...)"
          />
          <button
            type="submit"
            disabled={isLoading || !inputText.trim()}
            className="h-[52px] w-[52px] rounded-2xl bg-gradient-to-tr from-saffron-500 to-saffron-600 hover:from-saffron-600 hover:to-saffron-700 text-white flex items-center justify-center shadow-lg shadow-saffron-500/20 transition-all active:scale-95 disabled:opacity-50 disabled:scale-100 disabled:shadow-none"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
export default Chat;
