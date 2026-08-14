import apiClient from "@/lib/api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export const tutorService = {
  async sendMessage(message: string, conversationId?: string, syllabusId?: number) {
    try {
      const res = await apiClient.post("/api/v1/tutor/chat", {
        message,
        conversation_id: conversationId,
        syllabus_id: syllabusId,
      });
      return res.data as { response: string; conversation_id: string };
    } catch {
      const demos: Record<string, string> = {
        default: "I'm your AI tutor for DBMS! I can explain concepts, solve queries, and help you prepare for exams. Try asking me about normalization, SQL joins, or ACID properties!",
      };
      const key = Object.keys(demos).find((k) => message.toLowerCase().includes(k)) || "default";
      return { response: demos[key], conversation_id: conversationId || "demo-session" };
    }
  },
};
