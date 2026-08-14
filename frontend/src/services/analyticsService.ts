import apiClient from "@/lib/api";
import { mockAnalytics, mockWeakTopics, mockRevisionPlan } from "@/data/mockData";

export const analyticsService = {
  async getSummary() {
    try {
      const res = await apiClient.get("/api/analytics/summary");
      return res.data;
    } catch {
      return mockAnalytics;
    }
  },

  async getWeakTopics() {
    try {
      const res = await apiClient.get("/api/weak-topics");
      return res.data;
    } catch {
      return mockWeakTopics;
    }
  },

  async getRevisionPlan() {
    try {
      const res = await apiClient.get("/api/revision-plan");
      return res.data;
    } catch {
      return mockRevisionPlan;
    }
  },
};
