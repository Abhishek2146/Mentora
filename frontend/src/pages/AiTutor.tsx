import { useState, useRef, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import {
  Send, Bot, User, Sparkles, RotateCcw, Mic, MicOff,
  Volume2, VolumeX, Play, X, Radio, Loader2
} from "lucide-react";
import { tutorService } from "@/services/tutorService";
import { syllabusService } from "@/services/syllabusService";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  time: Date;
}

interface Syllabus {
  id: number;
  title: string;
  status: string;
}

const suggestions = [
  "Explain the key concepts",
  "What are the main topics covered?",
  "Summarize the first chapter",
  "Give me a study plan for this subject",
  "What should I focus on for revision?",
];

const voicePhrases = [
  "Explain the key concepts of this syllabus",
  "What are the most important topics?",
  "Quiz me on this subject with 3 questions",
  "Summarize the main takeaways",
];

export default function AiTutor() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content:
        "👋 Hi! I'm Mentora, your AI tutor. I can answer questions about any subject you've uploaded. Select a syllabus to get started, then ask me anything!",
      time: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<number | undefined>();
  const [syllabi, setSyllabi] = useState<Syllabus[]>([]);
  const [selectedSyllabusId, setSelectedSyllabusId] = useState<number | undefined>();
  const [syllabiLoading, setSyllabiLoading] = useState(true);
  
  // Voice Learning state
  const [voiceModalOpen, setVoiceModalOpen] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [voiceAutoSpeak, setVoiceAutoSpeak] = useState(true);
  const recognitionRef = useRef<any>(null);
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

    return () => {
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  const selectedSyllabus = syllabi.find((s) => s.id === selectedSyllabusId);

  const speak = (text: string) => {
    if (!("speechSynthesis" in window) || !voiceAutoSpeak) return;
    window.speechSynthesis.cancel();
    const cleanText = text.replace(/[*#_`~\[\]]/g, "").trim();
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  const stopSpeaking = () => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
  };

  const toggleListening = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Voice speech recognition is not supported in this browser. You can click on the suggestion phrases below!");
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    try {
      stopSpeaking();
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onstart = () => {
        setIsListening(true);
        setTranscript("");
      };

      recognition.onresult = (event: any) => {
        let current = "";
        for (let i = 0; i < event.results.length; i++) {
          current += event.results[i][0].transcript;
        }
        setTranscript(current);
      };

      recognition.onerror = (event: any) => {
        console.error("Speech recognition error:", event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error("Speech recognition start failed:", err);
      setIsListening(false);
    }
  };

  const clearChat = () => {
    stopSpeaking();
    setMessages([
      {
        id: "1",
        role: "assistant",
        content:
          "👋 Hi! I'm Mentora, your AI tutor. I can answer questions about any subject you've uploaded. Select a syllabus to get started, then ask me anything!",
        time: new Date(),
      },
    ]);
    setSessionId(undefined);
  };

  const handleSyllabusChange = (id: number) => {
    setSelectedSyllabusId(id);
    setSessionId(undefined);
    clearChat();
  };

  const send = async (text?: string, fromVoice = false) => {
    const msg = text || input.trim();
    if (!msg) return;
    setInput("");
    if (fromVoice) {
      setTranscript("");
      if (isListening) {
        recognitionRef.current?.stop();
        setIsListening(false);
      }
    }
    stopSpeaking();

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: msg,
      time: new Date(),
    };
    setMessages((p) => [...p, userMsg]);
    setLoading(true);

    try {
      const res = await tutorService.sendMessage(
        msg,
        sessionId,
        selectedSyllabusId,
      );
      setSessionId(res.session_id);
      setMessages((p) => [
        ...p,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: res.response,
          time: new Date(),
        },
      ]);
      if (voiceAutoSpeak && voiceModalOpen) {
        speak(res.response);
      }
    } catch (e: any) {
      let content =
        "I couldn't connect to the AI tutor. Please make sure the backend server is running and try again.";
      if (e?.response?.status === 429) {
        content =
          e?.response?.data?.detail ||
          "You're sending messages too quickly. Please wait a moment and try again.";
      } else if (e?.response?.data?.detail) {
        content = e.response.data.detail;
      }
      setMessages((p) => [
        ...p,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content,
          time: new Date(),
        },
      ]);
      if (fromVoice || voiceModalOpen) {
        speak(content);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout title="AI Tutor">
      <div className="max-w-4xl mx-auto h-[calc(100vh-10rem)] flex flex-col relative">
        {/* Tutor Top Card */}
        <div className="card p-4 mb-4 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center shadow-glow-primary">
            <Bot className="w-7 h-7 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="font-bold text-slate-800 dark:text-slate-100">Mentora AI</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              RAG-powered • {selectedSyllabus ? selectedSyllabus.title : "No subject selected"} • Always available
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
            <span className="w-2 h-2 bg-success-500 rounded-full animate-pulse" />
            <span className="text-sm text-success-600 font-medium">Online</span>
          </div>
          <button
            onClick={clearChat}
            className="btn-ghost btn-sm p-2 rounded-lg"
            title="Clear chat"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>

        {/* Message Stream */}
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
                className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed break-words whitespace-pre-line ${
                  m.role === "user"
                    ? "bg-gradient-to-br from-primary-500 to-primary-600 text-white rounded-tr-sm"
                    : "bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 rounded-tl-sm"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl rounded-tl-sm px-4 py-3">
                <div className="flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <div
                      key={i}
                      className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Suggestion Chips */}
        {messages.length <= 1 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="text-xs px-3 py-1.5 rounded-full bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-100 transition-colors border border-primary-200 dark:border-primary-700"
              >
                <Sparkles className="inline w-3 h-3 mr-1" />
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input bar */}
        <div className="card p-3 flex items-end gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Ask anything about your syllabus…"
            rows={1}
            className="flex-1 min-w-0 resize-none bg-transparent text-sm text-slate-700 dark:text-slate-200 placeholder-slate-400 focus:outline-none py-2"
          />
          <button
            onClick={() => send()}
            disabled={!input.trim() || loading}
            className="btn-primary btn-sm w-10 h-10 rounded-xl disabled:opacity-40 flex items-center justify-center flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>

        {/* ── Floating Voice Learning Popup Modal ── */}
        {voiceModalOpen && (
          <div className="fixed bottom-24 right-4 sm:right-8 z-50 w-[92vw] sm:w-[380px] bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-2xl p-5 animate-fade-in flex flex-col gap-4">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-700 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center shadow-md">
                  <Radio className="w-4 h-4 text-white animate-pulse" />
                </div>
                <div>
                  <h3 className="font-bold text-sm text-slate-800 dark:text-slate-100">Learn from Voice</h3>
                  <p className="text-[11px] text-slate-400">Ask aloud • AI answers with audio</p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => {
                    if (isSpeaking) stopSpeaking();
                    setVoiceAutoSpeak(!voiceAutoSpeak);
                  }}
                  className={`p-1.5 rounded-lg text-xs transition-colors ${
                    voiceAutoSpeak
                      ? "text-primary-600 bg-primary-50 dark:bg-primary-900/30"
                      : "text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
                  }`}
                  title={voiceAutoSpeak ? "AI Voice response is ON" : "AI Voice response is OFF"}
                >
                  {voiceAutoSpeak ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => {
                    stopSpeaking();
                    if (isListening) recognitionRef.current?.stop();
                    setVoiceModalOpen(false);
                  }}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                  aria-label="Close voice modal"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Speaking / Listening central visual */}
            <div className="flex flex-col items-center justify-center py-2 gap-3">
              <div className="relative">
                {isListening && (
                  <>
                    <span className="absolute -inset-2.5 rounded-full bg-danger-500/20 animate-ping" />
                    <span className="absolute -inset-5 rounded-full bg-danger-500/10 animate-pulse" />
                  </>
                )}
                {isSpeaking && (
                  <>
                    <span className="absolute -inset-2.5 rounded-full bg-primary-500/20 animate-ping" />
                    <span className="absolute -inset-5 rounded-full bg-secondary-500/10 animate-pulse" />
                  </>
                )}
                <button
                  onClick={toggleListening}
                  className={`relative w-20 h-20 rounded-full flex items-center justify-center shadow-lg transition-all duration-300 hover:scale-105 active:scale-95 ${
                    isListening
                      ? "bg-danger-500 text-white shadow-danger-500/40"
                      : "bg-gradient-to-br from-primary-500 to-secondary-500 text-white shadow-primary-500/40"
                  }`}
                >
                  {isListening ? (
                    <MicOff className="w-9 h-9" />
                  ) : (
                    <Mic className="w-9 h-9" />
                  )}
                </button>
              </div>

              <div className="text-center">
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  {isListening
                    ? "Listening… speak clearly"
                    : isSpeaking
                    ? "AI is speaking…"
                    : loading
                    ? "Thinking…"
                    : "Tap mic to start speaking"}
                </p>
                <p className="text-xs text-slate-400 mt-0.5">
                  {isListening
                    ? "Tap again when finished"
                    : "or tap any suggestion below"}
                </p>
              </div>
            </div>

            {/* Live Transcript / Response preview */}
            {transcript ? (
              <div className="bg-slate-50 dark:bg-slate-700/50 p-3 rounded-xl border border-slate-200 dark:border-slate-600">
                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Your Voice Input</p>
                <p className="text-sm text-slate-700 dark:text-slate-200 break-words italic">
                  "{transcript}"
                </p>
                <div className="mt-2.5 flex items-center justify-end gap-2">
                  <button
                    onClick={() => setTranscript("")}
                    className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 px-2 py-1"
                  >
                    Clear
                  </button>
                  <button
                    onClick={() => send(transcript, true)}
                    disabled={loading}
                    className="btn-primary btn-sm text-xs px-3 py-1.5 rounded-lg flex items-center gap-1"
                  >
                    {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                    Ask AI
                  </button>
                </div>
              </div>
            ) : null}

            {/* Quick voice phrases */}
            <div>
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">
                Try asking:
              </p>
              <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                {voicePhrases.map((phrase) => (
                  <button
                    key={phrase}
                    onClick={() => send(phrase, true)}
                    disabled={loading}
                    className="w-full flex items-center gap-2 p-2 rounded-xl bg-slate-50 dark:bg-slate-700/40 hover:bg-primary-50 dark:hover:bg-primary-900/20 text-left transition-colors border border-slate-100 dark:border-slate-700"
                  >
                    <Play className="w-3.5 h-3.5 text-primary-500 flex-shrink-0" />
                    <span className="text-xs text-slate-600 dark:text-slate-300 truncate">
                      {phrase}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── Floating Voice Learning Button on Bottom Right ── */}
        <div className="fixed bottom-6 right-4 sm:right-8 z-40">
          <button
            onClick={() => setVoiceModalOpen(!voiceModalOpen)}
            className={`group relative flex items-center gap-2.5 px-4 py-3 rounded-full shadow-xl transition-all duration-300 hover:scale-105 active:scale-95 ${
              voiceModalOpen
                ? "bg-slate-800 text-white dark:bg-slate-700 ring-2 ring-primary-500"
                : "bg-gradient-to-r from-primary-500 via-secondary-500 to-primary-600 text-white"
            }`}
            aria-label="Learn from Voice"
          >
            {/* Pulsing beacon */}
            {!voiceModalOpen && (
              <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-secondary-500" />
              </span>
            )}
            <Mic className="w-5 h-5 text-white flex-shrink-0" />
            <span className="text-xs sm:text-sm font-semibold whitespace-nowrap">
              Learn from Voice
            </span>
          </button>
        </div>
      </div>
    </AppLayout>
  );
}

