import apiClient from "@/lib/api";
import { mockQuizQuestions } from "@/data/mockData";

export const quizService = {
  async getDailyQuiz() {
    try {
      const res = await apiClient.get("/api/quiz/daily");
      return res.data;
    } catch {
      return mockQuizQuestions;
    }
  },

  async generateMCQ(topic: string, difficulty: string, count = 5) {
    try {
      const res = await apiClient.post("/api/quiz/generate-mcq", { topic, difficulty, count });
      return res.data;
    } catch {
      return mockQuizQuestions.slice(0, count);
    }
  },

  async submitQuiz(quizId: number, answers: { question_id: number; selected: number }[], timeTaken: number) {
    try {
      const res = await apiClient.post(`/api/quiz/${quizId}/submit`, { answers, time_taken_seconds: timeTaken });
      return res.data;
    } catch {
      const correct = Math.floor(answers.length * 0.75);
      return { score: 75, correct, total: answers.length, weak_topics: [], strong_topics: [] };
    }
  },
};
