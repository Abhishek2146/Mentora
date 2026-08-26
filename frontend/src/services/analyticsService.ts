import apiClient from "@/lib/api";

export const analyticsService = {
  async getSummary() {
    const res = await apiClient.get("/api/v1/analytics/dashboard");
    return res.data;
  },

  async getWeakTopics() {
    const res = await apiClient.get("/api/v1/weak-topics/");
    return res.data;
  },

  async getRevisionPlan() {
    const res = await apiClient.get("/api/v1/revision/schedules");
    return res.data;
  },
};
