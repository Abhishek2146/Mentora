import apiClient from "@/lib/api";
import { mockAnalytics, mockWeakTopics, mockRevisionPlan } from "@/data/mockData";

export const analyticsService = {
  async getSummary() {
    try {
      const res = await apiClient.get("/api/v1/analytics/dashboard");
      return res.data;
    } catch {
      return mockAnalytics;
    }
  },

  async getWeakTopics() {
    try {
      const res = await apiClient.get("/api/v1/weak-topics");
      return res.data;
    } catch {
      return mockWeakTopics;
    }
  },

  async getRevisionPlan() {
    try {
      const res = await apiClient.get("/api/v1/revision/schedules");
      return res.data;
    } catch {
      return mockRevisionPlan;
    }
  },
};
