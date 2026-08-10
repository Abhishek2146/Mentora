import DashboardLayout from "@/components/layout/DashboardLayout";
import apiClient from "@/lib/api";
import { useState, useEffect, useRef } from "react";
import { ChatSession, ChatMessage } from "@/types";

interface ChatRequest {
  message: string;
  syllabus_id?: number;
  session_id?: number;
}

export default function AiTutorPage() {
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchSessions = async () => {
    try {
      const response = await apiClient.get("/api/v1/tutor/sessions");
      setSessions(response.data);
    } catch (error) {
      console.error("Failed to fetch sessions:", error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: "user" as const, content: input };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const request: ChatRequest = {
        message: input,
        ...(currentSessionId && { session_id: currentSessionId }),
      };

      const response = await apiClient.post("/api/v1/tutor/chat", request);
      const aiMessage = { role: "assistant" as const, content: response.data.response };
      setMessages((prev) => [...prev, aiMessage]);

      if (response.data.session_id && !currentSessionId) {
        setCurrentSessionId(response.data.session_id);
      }
      setInput("");
    } catch (error) {
      console.error("Failed to send message:", error);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I encountered an error. Please try again." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const startNewSession = () => {
    setMessages([]);
    setCurrentSessionId(null);
  };

  return (
    <DashboardLayout>
      <div className="max-w-4xl mx-auto h-[calc(100vh-200px)]">
        <div className="mb-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">AI Tutor</h1>
          <button
            onClick={startNewSession}
            className="px-3 py-1 text-sm text-primary-600 hover:bg-primary-50 rounded-md"
          >
            + New Chat
          </button>
        </div>

        <div className="bg-white rounded-lg shadow h-[calc(100vh-260px)] flex flex-col">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`p-3 rounded-lg ${
                  msg.role === "user"
                    ? "bg-primary-50 ml-auto max-w-[80%]"
                    : "bg-gray-100 mr-auto max-w-[80%]"
                }`}
              >
                <p className="text-sm">{msg.content}</p>
              </div>
            ))}
            {isLoading && (
              <div className="p-3 rounded-lg bg-gray-100">
                <p className="text-sm text-gray-500">AI is thinking...</p>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="border-t p-3">
            <div className="flex space-x-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && !isLoading && sendMessage()}
                placeholder="Ask your AI tutor anything..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500"
                disabled={isLoading}
              />
              <button
                onClick={sendMessage}
                disabled={isLoading || !input.trim()}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
