import apiClient from "@/lib/api";
import { mockFlashcards } from "@/data/mockData";

export const flashcardService = {
  async getFlashcards(topic?: string) {
    try {
      const res = await apiClient.get(`/api/flashcards${topic ? `?topic=${topic}` : ""}`);
      return res.data;
    } catch {
      return mockFlashcards;
    }
  },

  async generateFlashcards(topic: string, count = 10) {
    try {
      const res = await apiClient.post("/api/flashcards/generate", { topic, count });
      return res.data;
    } catch {
      return mockFlashcards.slice(0, count);
    }
  },

  async submitRating(cardId: number, rating: "Again" | "Hard" | "Good" | "Easy") {
    try {
      const res = await apiClient.post(`/api/flashcards/${cardId}/rating`, { rating });
      return res.data;
    } catch {
      return { next_review: new Date().toISOString(), interval: 1 };
    }
  },
};
