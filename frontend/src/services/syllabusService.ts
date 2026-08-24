import apiClient from "@/lib/api";

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
};
