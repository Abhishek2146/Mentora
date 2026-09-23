import apiClient from "@/lib/api";
import type { Review, ReviewSummary } from "@/types";

export const reviewService = {
  /** Public list of all reviews (newest first). */
  async list(): Promise<Review[]> {
    const res = await apiClient.get("/api/v1/reviews");
    return res.data;
  },

  /** Public average rating and review count. */
  async getSummary(): Promise<ReviewSummary> {
    const res = await apiClient.get("/api/v1/reviews/summary");
    return res.data;
  },

  /** The authenticated user's own review. */
  async getMine(): Promise<Review> {
    const res = await apiClient.get("/api/v1/reviews/me");
    return res.data;
  },

  /** Create or update (upsert) the authenticated user's review. */
  async save(rating: number, comment: string | null): Promise<Review> {
    const res = await apiClient.post("/api/v1/reviews", { rating, comment });
    return res.data;
  },

  /** Delete the authenticated user's review. */
  async deleteMine(): Promise<void> {
    await apiClient.delete("/api/v1/reviews/me");
  },
};