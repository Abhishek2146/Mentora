import { useState, useRef, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { Send, Bot, User, Sparkles, RotateCcw } from "lucide-react";
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

  const send = async (text?: string) => {
    const msg = text || input.trim();
    if (!msg) return;
    setInput("");
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
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout title="AI Tutor">
      <div className="max-w-4xl mx-auto h-[calc(100vh-10rem)] flex flex-col">
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
            className="btn-primary btn-sm w-10 h-10 rounded-xl disabled:opacity-40"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </AppLayout>
  );
}
