import apiClient from "@/lib/api";
import { mockFlashcards } from "@/data/mockData";

export const flashcardService = {
  async getFlashcards(topic?: string, syllabusId?: number) {
    try {
      const params = new URLSearchParams();
      if (topic) params.append("topic", topic);
      if (syllabusId) params.append("syllabus_id", syllabusId.toString());
      const query = params.toString();
      const res = await apiClient.get(`/api/v1/flashcards/review/all${query ? `?${query}` : ""}`);
      return res.data;
    } catch {
      return mockFlashcards;
    }
  },

  async generateFlashcards(topic: string, count = 10, syllabusId?: number) {
    const res = await apiClient.post("/api/v1/flashcards/generate", {
      topic: topic || null,
      count,
      syllabus_id: syllabusId || null,
    });
    return res.data;
  },

  async submitRating(cardId: number, rating: "Again" | "Hard" | "Good" | "Easy") {
    const res = await apiClient.post(`/api/v1/flashcards/${cardId}/rating`, { rating });
    return res.data;
  },
};
