import apiClient from "@/lib/api";
import type { SyllabusSearchParams, SyllabusSearchResponse } from "@/types/api";

export const syllabusService = {
  async uploadSyllabus(file: File, title: string, description?: string) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title);
    if (description) formData.append("description", description);
    const res = await apiClient.post("/api/v1/syllabus/upload", formData);
    return res.data;
  },

  async analyzeSyllabus(syllabusId: number) {
    const res = await apiClient.post(`/api/v1/syllabus/${syllabusId}/analyze`);
    return res.data;
  },

  async getAllSyllabi() {
    const res = await apiClient.get("/api/v1/syllabus");
    return res.data;
  },

  async searchSyllabi(params: SyllabusSearchParams): Promise<SyllabusSearchResponse> {
    const searchParams = new URLSearchParams();
    searchParams.append("q", params.q);
    if (params.search_in) {
      params.search_in.forEach(field => searchParams.append("search_in", field));
    }
    if (params.status) searchParams.append("status", params.status);
    if (params.page) searchParams.append("page", params.page.toString());
    if (params.per_page) searchParams.append("per_page", params.per_page.toString());

    const res = await apiClient.get(`/api/v1/syllabus/search?${searchParams.toString()}`);
    return res.data;
  },
};
