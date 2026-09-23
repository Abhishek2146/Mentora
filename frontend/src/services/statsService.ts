import apiClient from "@/lib/api";
import type { PublicStats } from "@/types";

export const statsService = {
  /** Real public platform stats for the landing page. */
  async getPublicStats(): Promise<PublicStats> {
    const res = await apiClient.get("/api/v1/stats/public");
    return res.data;
  },
};