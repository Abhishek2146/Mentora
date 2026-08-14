import apiClient from "@/lib/api";
import { mockStudyPlan } from "@/data/mockData";

export const studyPlanService = {
  async getStudyPlan() {
    try {
      const res = await apiClient.get("/api/v1/study-plan");
      return res.data;
    } catch {
      return mockStudyPlan;
    }
  },

  async generatePlan(syllabusId: number, examDate: string, dailyHours: number) {
    try {
      const res = await apiClient.post("/api/v1/study-plan/generate", {
        syllabus_id: syllabusId,
        exam_date: examDate,
        daily_hours: dailyHours,
        focus_weak_topics: true,
      });
      return res.data;
    } catch {
      return mockStudyPlan;
    }
  },
};
