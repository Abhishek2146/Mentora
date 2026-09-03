import apiClient from "@/lib/api";

export const quizService = {
  async getDailyQuiz(count = 5, syllabusId?: number) {
    const params: Record<string, any> = { count };
    if (syllabusId) params.syllabus_id = syllabusId;
    const res = await apiClient.get("/api/v1/quizzes/daily", {
      params,
      timeout: 300000,
    });
    return res.data;
  },

  async regenerateDailyQuiz(count = 5, syllabusId?: number) {
    const params: Record<string, any> = { count };
    if (syllabusId) params.syllabus_id = syllabusId;
    const res = await apiClient.post("/api/v1/quizzes/daily/regenerate", {}, {
      params,
      timeout: 300000,
    });
    return res.data;
  },

  async generateMCQ(topic: string, difficulty: string, count = 5) {
    const res = await apiClient.post(
      "/api/v1/quizzes/generate-mcq",
      { topic, difficulty, count },
      { timeout: 300000 }
    );
    return res.data;
  },

  async submitQuiz(quizId: number, answers: { question_id: number; selected: string }[], timeTaken: number) {
    const res = await apiClient.post(`/api/v1/quizzes/${quizId}/submit`, {
      answers,
      time_taken_seconds: timeTaken,
    });
    return res.data;
  },
};
