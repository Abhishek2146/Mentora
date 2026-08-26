import apiClient from "@/lib/api";
import type { SyllabusSearchParams, SyllabusSearchResponse } from "@/types/api";

const PROCESSING_TIMEOUT = 300000;

export const syllabusService = {
  async uploadSyllabus(file: File, title: string, description?: string) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title);
    if (description) formData.append("description", description);
    const res = await apiClient.post(
      "/api/v1/syllabus/upload",
      formData,
      { timeout: PROCESSING_TIMEOUT }
    );
    return res.data;
  },

  async analyzeSyllabus(syllabusId: number) {
    const res = await apiClient.post(`/api/v1/syllabus/${syllabusId}/analyze`, null, {
      timeout: PROCESSING_TIMEOUT,
    });
    return res.data;
  },

  async getAllSyllabi() {
    const res = await apiClient.get("/api/v1/syllabus");
    return res.data;
  },

  async deleteSyllabus(syllabusId: number) {
    await apiClient.delete(`/api/v1/syllabus/${syllabusId}`);
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
