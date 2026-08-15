import apiClient from "@/lib/api";

export interface Comment {
  id: string;
  target_id: string;
  target_type: string;
  user_id: string;
  user_name: string;
  content: string;
  rating?: number;
  created_at: string;
}

export interface CommentCreatePayload {
  target_id: string;
  target_type?: string;
  content: string;
  rating?: number;
}

export const commentService = {
  async getComments(targetId?: string, targetType?: string): Promise<Comment[]> {
    try {
      const params = new URLSearchParams();
      if (targetId) params.append("target_id", targetId);
      if (targetType) params.append("target_type", targetType);
      const res = await apiClient.get(`/api/v1/comments?${params.toString()}`);
      return res.data;
    } catch {
      return [
        {
          id: "c1",
          target_id: targetId || "topic-sql-joins",
          target_type: targetType || "topic",
          user_id: "u1",
          user_name: "Dipeesh Kumar",
          content: "Great explanation on LEFT JOIN vs INNER JOIN! Really helped with my DBMS quiz.",
          rating: 5,
          created_at: new Date().toISOString(),
        },
      ];
    }
  },

  async createComment(payload: CommentCreatePayload): Promise<Comment> {
    try {
      const res = await apiClient.post("/api/v1/comments", {
        target_id: payload.target_id,
        target_type: payload.target_type || "topic",
        content: payload.content,
        rating: payload.rating,
      });
      return res.data;
    } catch {
      return {
        id: `c_${Date.now()}`,
        target_id: payload.target_id,
        target_type: payload.target_type || "topic",
        user_id: "u1",
        user_name: "Dipeesh Kumar",
        content: payload.content,
        rating: payload.rating,
        created_at: new Date().toISOString(),
      };
    }
  },

  async deleteComment(commentId: string): Promise<void> {
    try {
      await apiClient.delete(`/api/v1/comments/${commentId}`);
    } catch {
      // Demo fallback
    }
  },
};
