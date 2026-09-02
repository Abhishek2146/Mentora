import { useState, useRef, useEffect, useCallback } from "react";
import AppLayout from "@/components/layout/AppLayout";
import {
  Mic,
  MicOff,
  Volume2,
  Play,
  Pause,
  Bot,
  User,
  RotateCcw,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { voiceService } from "@/services/voiceService";
import { syllabusService } from "@/services/syllabusService";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  transcript?: string;
  audioUrl?: string;
  time: Date;
}

interface Syllabus {
  id: number;
  title: string;
  status: string;
}

const suggestions = [
  "Explain what normalization is",
  "What are the ACID properties?",
  "How does a B+ tree work?",
  "Quiz me on SQL joins",
];

export default function VoiceLearning() {
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content:
        "Hi! I'm your voice learning assistant. Click the mic button and ask me anything about your studies. I'll respond with both voice and text!",
      time: new Date(),
    },
  ]);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<number | undefined>();
  const [syllabi, setSyllabi] = useState<Syllabus[]>([]);
  const [selectedSyllabusId, setSelectedSyllabusId] = useState<number | undefined>();
  const [syllabiLoading, setSyllabiLoading] = useState(true);
  const [playingAudio, setPlayingAudio] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const loadSyllabi = async () => {
      try {
        const data = await syllabusService.getAllSyllabi();
        setSyllabi(data);
        if (data.length > 0) {
          setSelectedSyllabusId(data[0].id);
        }
      } catch (e) {
        console.error("Failed to load syllabi:", e);
      } finally {
        setSyllabiLoading(false);
      }
    };
    loadSyllabi();
  }, []);

  const selectedSyllabus = syllabi.find((s) => s.id === selectedSyllabusId);

  const clearChat = () => {
    setMessages([
      {
        id: "1",
        role: "assistant",
        content:
          "Hi! I'm your voice learning assistant. Click the mic button and ask me anything about your studies. I'll respond with both voice and text!",
        time: new Date(),
      },
    ]);
    setSessionId(undefined);
    setError(null);
  };

  const handleSyllabusChange = (id: number) => {
    setSelectedSyllabusId(id);
    setSessionId(undefined);
    clearChat();
  };

  const playAudio = useCallback((url: string) => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    const audio = new Audio(url);
    audioRef.current = audio;
    setPlayingAudio(url);
    audio.onended = () => setPlayingAudio(null);
    audio.onerror = () => setPlayingAudio(null);
    audio.play().catch(() => setPlayingAudio(null));
  }, []);

  const stopRecording = useCallback(async () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setRecording(false);
  }, []);

  const startRecording = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm",
      });

      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());

        if (audioChunksRef.current.length === 0) return;

        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        audioChunksRef.current = [];

        setProcessing(true);
        try {
          const result = await voiceService.listen(
            audioBlob,
            selectedSyllabusId,
            sessionId,
          );

          setSessionId(result.session_id);

          const userMsg: Message = {
            id: Date.now().toString(),
            role: "user",
            content: result.transcript,
            transcript: result.transcript,
            time: new Date(),
          };

          const assistantMsg: Message = {
            id: (Date.now() + 1).toString(),
            role: "assistant",
            content: result.response,
            audioUrl: result.audio_url ?? undefined,
            time: new Date(),
          };

          setMessages((prev) => [...prev, userMsg, assistantMsg]);

          if (result.audio_url) {
            const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
            playAudio(`${baseUrl}${result.audio_url}`);
          }
        } catch (e: any) {
          let errorMsg =
            e?.response?.data?.detail ||
            "Failed to process voice input. Please make sure the backend server is running and try again.";
          if (e?.response?.status === 429) {
            errorMsg = "You're sending requests too quickly. Please wait a moment and try again.";
          }
          setError(errorMsg);
          setMessages((prev) => [
            ...prev,
            {
              id: (Date.now() + 1).toString(),
              role: "assistant",
              content: errorMsg,
              time: new Date(),
            },
          ]);
        } finally {
          setProcessing(false);
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setRecording(true);
    } catch (e) {
      setError("Microphone access denied. Please allow microphone access and try again.");
    }
  }, [selectedSyllabusId, sessionId, playAudio]);

  const toggleRecording = () => {
    if (recording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const sendSuggestion = async (text: string) => {
    if (processing) return;
    setError(null);
    setProcessing(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      time: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const formData = new FormData();
      const emptyBlob = new Blob([], { type: "audio/webm" });
      formData.append("audio", emptyBlob, "empty.webm");
      if (selectedSyllabusId) formData.append("syllabus_id", selectedSyllabusId.toString());
      if (sessionId) formData.append("session_id", sessionId.toString());

      const res = await fetch(
        `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/v1/voice/speak?text=${encodeURIComponent(text)}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("mentora_tokens") ? JSON.parse(localStorage.getItem("mentora_tokens")!).access_token : ""}`,
          },
        }
      );
      const data = await res.json();

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: text,
        audioUrl: data.audio_url ?? undefined,
        time: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      if (data.audio_url) {
        const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
        playAudio(`${baseUrl}${data.audio_url}`);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: "Couldn't process your request. Please try again.",
          time: new Date(),
        },
      ]);
    } finally {
      setProcessing(false);
    }
  };

  return (
    <AppLayout title="Voice Learning">
      <div className="max-w-4xl mx-auto h-[calc(100vh-10rem)] flex flex-col">
        {/* Header */}
        <div className="card p-4 mb-4 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <div
            className={`w-12 h-12 rounded-2xl flex items-center justify-center shadow-glow-primary transition-all ${
              recording
                ? "bg-danger-500 animate-pulse"
                : "bg-gradient-to-br from-primary-500 to-secondary-500"
            }`}
          >
            {recording ? (
              <MicOff className="w-7 h-7 text-white" />
            ) : (
              <Mic className="w-7 h-7 text-white" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="font-bold text-slate-800 dark:text-slate-100">Voice Learning</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {selectedSyllabus ? selectedSyllabus.title : "No subject selected"} •{" "}
              {recording ? "Listening..." : processing ? "Processing..." : "Ready"}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 sm:gap-4">
            {syllabiLoading ? (
              <span className="text-sm text-slate-400">Loading syllabi…</span>
            ) : syllabi.length > 0 ? (
              <select
                value={selectedSyllabusId ?? ""}
                onChange={(e) => handleSyllabusChange(Number(e.target.value))}
                className="text-sm bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {syllabi.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title}
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-sm text-slate-400">No syllabi uploaded yet</span>
            )}
            <button onClick={clearChat} className="btn-ghost btn-sm p-2 rounded-lg" title="Clear chat">
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-3 p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-700 rounded-xl flex items-center gap-2 text-danger-700 dark:text-danger-300 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-auto hover:opacity-70">
              ×
            </button>
          </div>
        )}

        {/* Chat History */}
        <div className="flex-1 overflow-y-auto space-y-4 mb-4">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex gap-3 min-w-0 ${m.role === "user" ? "flex-row-reverse" : ""}`}
            >
              <div
                className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
                  m.role === "assistant"
                    ? "bg-gradient-to-br from-primary-500 to-secondary-500"
                    : "bg-gradient-to-br from-slate-600 to-slate-700"
                }`}
              >
                {m.role === "assistant" ? (
                  <Bot className="w-5 h-5 text-white" />
                ) : (
                  <User className="w-5 h-5 text-white" />
                )}
              </div>
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed break-words ${
                  m.role === "user"
                    ? "bg-gradient-to-br from-primary-500 to-primary-600 text-white rounded-tr-sm"
                    : "bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 rounded-tl-sm"
                }`}
              >
                <p>{m.content}</p>
                {m.role === "assistant" && m.audioUrl && (
                  <button
                    onClick={() => {
                      const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
                      const url = m.audioUrl!.startsWith("http") ? m.audioUrl! : `${baseUrl}${m.audioUrl}`;
                      if (playingAudio === url) {
                        audioRef.current?.pause();
                        setPlayingAudio(null);
                      } else {
                        playAudio(url);
                      }
                    }}
                    className="mt-2 flex items-center gap-1.5 text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 transition-colors"
                  >
                    {playingAudio ===
                    `${import.meta.env.VITE_API_URL || "http://localhost:8000"}${m.audioUrl}` ? (
                      <Pause className="w-3.5 h-3.5" />
                    ) : (
                      <Play className="w-3.5 h-3.5" />
                    )}
                    {playingAudio ===
                    `${import.meta.env.VITE_API_URL || "http://localhost:8000"}${m.audioUrl}`
                      ? "Playing..."
                      : "Play audio"}
                  </button>
                )}
              </div>
            </div>
          ))}
          {(processing || recording) && (
            <div className="flex gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl rounded-tl-sm px-4 py-3">
                {recording ? (
                  <div className="flex items-center gap-2 text-sm text-slate-500">
                    <div className="w-2 h-2 bg-danger-500 rounded-full animate-pulse" />
                    Listening...
                  </div>
                ) : (
                  <div className="flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <div
                        key={i}
                        className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
                        style={{ animationDelay: `${i * 0.15}s` }}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Suggestions */}
        {messages.length <= 1 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => sendSuggestion(s)}
                disabled={processing}
                className="text-xs px-3 py-1.5 rounded-full bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-100 transition-colors border border-primary-200 dark:border-primary-700 disabled:opacity-50"
              >
                <Volume2 className="inline w-3 h-3 mr-1" />
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Mic Button */}
        <div className="card p-4 flex items-center justify-center">
          <button
            onClick={toggleRecording}
            disabled={processing}
            className={`w-20 h-20 rounded-full flex items-center justify-center transition-all shadow-lg disabled:opacity-50 ${
              recording
                ? "bg-danger-500 hover:bg-danger-600 animate-pulse shadow-danger-500/50"
                : "bg-gradient-to-br from-primary-500 to-secondary-500 hover:from-primary-600 hover:to-secondary-600 shadow-primary-500/30"
            }`}
          >
            {processing ? (
              <Loader2 className="w-10 h-10 text-white animate-spin" />
            ) : recording ? (
              <MicOff className="w-10 h-10 text-white" />
            ) : (
              <Mic className="w-10 h-10 text-white" />
            )}
          </button>
          <p className="ml-4 text-sm text-slate-500 dark:text-slate-400">
            {recording
              ? "Listening... Click to stop"
              : processing
                ? "Processing your voice..."
                : "Click to start speaking"}
          </p>
        </div>
      </div>
    </AppLayout>
  );
}
