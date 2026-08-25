import apiClient from "@/lib/api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export const tutorService = {
  async sendMessage(
    message: string,
    sessionId?: number,
    syllabusId?: number,
  ): Promise<{ response: string; session_id: number }> {
    const res = await apiClient.post("/api/v1/tutor/chat", {
      message,
      session_id: sessionId,
      syllabus_id: syllabusId,
    });
    return res.data as { response: string; session_id: number };
  },
};
