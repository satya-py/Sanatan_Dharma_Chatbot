import React, { useState, useEffect, useRef } from "react";
import { Mic, MicOff, Volume2, VolumeX, RefreshCw, AlertCircle, Play, Square, Headphones } from "lucide-react";
import { chatService as chatAPI, API_BASE_URL } from "../services/api";

interface VoiceAssistantProps {
  currentSessionId: string | null;
  onCreateSession: () => void;
}

export const VoiceAssistant: React.FC<VoiceAssistantProps> = ({
  currentSessionId,
  onCreateSession,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState<"idle" | "listening" | "transcribing" | "thinking" | "speaking" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  
  const [userQuery, setUserQuery] = useState<string>("");
  const [assistantAnswer, setAssistantAnswer] = useState<string>("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  
  const [volume, setVolume] = useState<number>(0.8);
  const [isMuted, setIsMuted] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioPlaybackRef = useRef<HTMLAudioElement | null>(null);

  // Initialize audio element
  useEffect(() => {
    return () => {
      if (audioPlaybackRef.current) {
        audioPlaybackRef.current.pause();
        audioPlaybackRef.current = null;
      }
    };
  }, []);

  const startRecording = async () => {
    setErrorMessage(null);
    setUserQuery("");
    setAssistantAnswer("");
    setAudioUrl(null);
    
    if (audioPlaybackRef.current) {
      audioPlaybackRef.current.pause();
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const options = { mimeType: "audio/webm" };
      
      let mediaRecorder: MediaRecorder;
      try {
        mediaRecorder = new MediaRecorder(stream, options);
      } catch (e) {
        // Fallback for browsers that don't support audio/webm
        mediaRecorder = new MediaRecorder(stream);
      }

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((track) => track.stop());
        
        if (audioBlob.size > 0) {
          await uploadAndProcessVoice(audioBlob);
        } else {
          setStatus("error");
          setErrorMessage("Failed to record audio. Please try again.");
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
      setStatus("listening");
    } catch (err) {
      console.error("Microphone access denied:", err);
      setStatus("error");
      setErrorMessage("Could not access microphone. Please check permissions.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setStatus("transcribing");
    }
  };

  const uploadAndProcessVoice = async (audioBlob: Blob) => {
    let activeSessionId = currentSessionId;
    
    // Create new session if none exists
    if (!activeSessionId) {
      try {
        const newSession = await chatAPI.createSession("Voice Conversation", "en");
        activeSessionId = newSession.id;
        onCreateSession();
      } catch (err) {
        console.error("Failed to create voice session:", err);
        setStatus("error");
        setErrorMessage("Could not initialize chat session.");
        return;
      }
    }

    try {
      setStatus("thinking");
      const result = await chatAPI.sendVoiceMessage(activeSessionId, audioBlob);
      
      setUserQuery(result.question);
      setAssistantAnswer(result.answer);
      setStatus("idle");
      
      if (result.audio_url) {
        const fullAudioUrl = `${API_BASE_URL}${result.audio_url}`;
        setAudioUrl(fullAudioUrl);
        playAudio(fullAudioUrl);
      }
    } catch (err: any) {
      console.error("Voice process error:", err);
      setStatus("error");
      setErrorMessage(err.response?.data?.detail || "Error processing voice query.");
    }
  };

  const playAudio = (url: string) => {
    if (audioPlaybackRef.current) {
      audioPlaybackRef.current.pause();
    }

    const audio = new Audio(url);
    audioPlaybackRef.current = audio;
    audio.volume = isMuted ? 0 : volume;
    
    audio.onplay = () => setStatus("speaking");
    audio.onended = () => setStatus("idle");
    audio.onerror = () => {
      console.error("Audio playback error");
      setStatus("idle");
    };

    audio.play().catch((err) => {
      console.error("Audio autoplay block:", err);
      setStatus("idle");
    });
  };

  const stopPlayback = () => {
    if (audioPlaybackRef.current) {
      audioPlaybackRef.current.pause();
      setStatus("idle");
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (audioPlaybackRef.current) {
      audioPlaybackRef.current.volume = isMuted ? 0 : val;
    }
  };

  const handleMuteToggle = () => {
    const nextMute = !isMuted;
    setIsMuted(nextMute);
    if (audioPlaybackRef.current) {
      audioPlaybackRef.current.volume = nextMute ? 0 : volume;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case "listening": return "Listening to your voice...";
      case "transcribing": return "Transcribing with AI...";
      case "thinking": return "Searching scriptures...";
      case "speaking": return "Chanting response...";
      case "error": return "Process Failed";
      default: return "Chant or Ask Question";
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-stone-50/50 dark:bg-[#120a05] h-screen p-6 overflow-y-auto">
      <div className="max-w-xl w-full text-center space-y-8 p-10 rounded-3xl border border-stone-200/50 dark:border-stone-800/40 bg-white dark:bg-[#18110b] shadow-xl shadow-saffron-500/[0.02]">
        
        {/* Header */}
        <div className="space-y-2">
          <div className="mx-auto w-12 h-12 bg-gradient-to-tr from-saffron-500 to-gold-400 rounded-full flex items-center justify-center text-white shadow-md">
            <Headphones className="w-5 h-5" />
          </div>
          <h2 className="text-xl font-bold text-stone-800 dark:text-stone-200 tracking-wide font-sans">
            Devotional Voice Assistant
          </h2>
          <p className="text-xs text-stone-400 dark:text-stone-500 uppercase tracking-widest font-semibold">
            Real-time Voice-to-Voice
          </p>
        </div>

        {/* Visual Animation Box */}
        <div className="h-44 rounded-2xl bg-stone-50 dark:bg-[#120a05] border border-stone-100 dark:border-stone-850 flex flex-col items-center justify-center relative overflow-hidden shadow-inner p-6">
          {status === "listening" && (
            <div className="flex items-end gap-1.5 h-16">
              {[...Array(9)].map((_, i) => (
                <span 
                  key={i} 
                  className="wave-bar" 
                  style={{ animationDelay: `${i * 0.12}s`, width: '5px' }}
                />
              ))}
            </div>
          )}

          {status === "thinking" && (
            <div className="flex flex-col items-center gap-3">
              <RefreshCw className="w-8 h-8 text-saffron-500 animate-spin" />
              <span className="text-xs font-semibold text-stone-400 animate-pulse">Retrieving Wisdom...</span>
            </div>
          )}

          {status === "speaking" && (
            <div className="flex items-end gap-1.5 h-16">
              {[...Array(6)].map((_, i) => (
                <span 
                  key={i} 
                  className="wave-bar bg-gold-400" 
                  style={{ animationDelay: `${i * 0.15}s`, width: '5px' }}
                />
              ))}
            </div>
          )}

          {status === "transcribing" && (
            <div className="flex flex-col items-center gap-3">
              <div className="w-6 h-6 rounded-full border-2 border-saffron-500 border-t-transparent animate-spin"></div>
              <span className="text-xs font-semibold text-stone-400">Transcribing...</span>
            </div>
          )}

          {status === "idle" && (
            <p className="text-stone-400 dark:text-stone-600 text-xs italic font-medium">
              Click the microphone button below and begin speaking
            </p>
          )}

          {status === "error" && (
            <div className="flex flex-col items-center text-red-500 gap-2">
              <AlertCircle className="w-8 h-8" />
              <span className="text-xs font-semibold">{errorMessage || "An error occurred."}</span>
            </div>
          )}
        </div>

        {/* Process Status text */}
        <div className="font-sans font-semibold text-sm tracking-wide text-saffron-600 dark:text-saffron-400">
          {getStatusText()}
        </div>

        {/* Microphone Click Button */}
        <div className="flex justify-center items-center gap-4">
          {isRecording ? (
            <button
              onClick={stopRecording}
              className="w-20 h-20 rounded-full bg-red-600 text-white flex items-center justify-center shadow-lg shadow-red-500/20 hover:bg-red-700 active:scale-95 transition-all animate-pulse"
            >
              <MicOff className="w-8 h-8" />
            </button>
          ) : (
            <button
              onClick={startRecording}
              disabled={status === "thinking" || status === "transcribing"}
              className="w-20 h-20 rounded-full bg-gradient-to-tr from-saffron-500 to-saffron-600 text-white flex items-center justify-center shadow-lg shadow-saffron-500/25 hover:from-saffron-600 hover:to-saffron-700 active:scale-95 transition-all disabled:opacity-50 disabled:scale-100"
            >
              <Mic className="w-8 h-8" />
            </button>
          )}

          {status === "speaking" && (
            <button
              onClick={stopPlayback}
              className="w-12 h-12 rounded-full border border-stone-200 dark:border-stone-850 hover:bg-stone-100 dark:hover:bg-stone-900 text-stone-600 dark:text-stone-400 flex items-center justify-center transition-colors"
              title="Stop recitation"
            >
              <Square className="w-5 h-5 fill-current" />
            </button>
          )}
        </div>

        {/* Display response details if available */}
        {(userQuery || assistantAnswer) && (
          <div className="text-left space-y-4 pt-4 border-t border-stone-100 dark:border-stone-850">
            {userQuery && (
              <div>
                <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest block mb-1">Your Question</span>
                <p className="text-sm font-semibold text-stone-700 dark:text-stone-300 italic">
                  "{userQuery}"
                </p>
              </div>
            )}

            {assistantAnswer && (
              <div>
                <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest block mb-1">Answer Summary</span>
                <p className="text-xs text-stone-500 dark:text-stone-400 leading-relaxed max-h-36 overflow-y-auto pr-1">
                  {assistantAnswer.split("### Detailed Explanation")[0].replace("### Short Summary", "").trim()}
                </p>
              </div>
            )}

            {/* Audio Playback Toolbar */}
            {audioUrl && (
              <div className="flex items-center gap-3 bg-stone-50 dark:bg-stone-900/40 p-3 rounded-2xl border border-stone-100 dark:border-stone-850/60 mt-2">
                <button
                  onClick={() => playAudio(audioUrl)}
                  className="w-8 h-8 rounded-full bg-saffron-500 text-white flex items-center justify-center hover:bg-saffron-600 active:scale-90 transition-all flex-shrink-0"
                >
                  <Play className="w-4 h-4 fill-current ml-0.5" />
                </button>
                
                {/* Volume slider */}
                <div className="flex-1 flex items-center gap-2">
                  <button onClick={handleMuteToggle} className="text-stone-400 hover:text-stone-600">
                    {isMuted || volume === 0 ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                  </button>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={volume}
                    onChange={handleVolumeChange}
                    className="w-full h-1 bg-stone-200 dark:bg-stone-800 rounded-lg appearance-none cursor-pointer accent-saffron-500"
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
export default VoiceAssistant;
