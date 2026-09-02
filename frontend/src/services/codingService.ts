import apiClient from "@/lib/api";
import type { CodingProblem, CodingSubmission } from "@/types";

export const codingService = {
  async getProblems(params?: {
    difficulty?: string;
    category?: string;
    language?: string;
  }): Promise<CodingProblem[]> {
    const search = new URLSearchParams();
    if (params?.difficulty) search.append("difficulty", params.difficulty);
    if (params?.category) search.append("category", params.category);
    if (params?.language) search.append("language", params.language);
    const query = search.toString();
    const res = await apiClient.get(`/api/v1/coding/problems${query ? `?${query}` : ""}`);
    return res.data;
  },

  async getProblem(problemId: number): Promise<CodingProblem> {
    const res = await apiClient.get(`/api/v1/coding/problems/${problemId}`);
    return res.data;
  },

  async generateProblem(payload: {
    topic?: string;
    syllabus_id?: number;
    difficulty?: "easy" | "medium" | "hard";
    language?: string;
  }): Promise<CodingProblem> {
    const res = await apiClient.post("/api/v1/coding/generate", payload);
    return res.data;
  },

  async submitCode(
    problemId: number,
    code: string,
    language: string
  ): Promise<CodingSubmission> {
    const res = await apiClient.post(`/api/v1/coding/submissions/${problemId}`, {
      code,
      language,
    });
    return res.data;
  },

  async getMySubmissions(problemId?: number): Promise<CodingSubmission[]> {
    const query = problemId ? `?problem_id=${problemId}` : "";
    const res = await apiClient.get(`/api/v1/coding/submissions/my${query}`);
    return res.data;
  },

  async getSupportedLanguages(): Promise<string[]> {
    const res = await apiClient.get("/api/v1/coding/languages");
    return res.data.languages;
  },
};
