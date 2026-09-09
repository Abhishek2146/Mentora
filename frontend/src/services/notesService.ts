import apiClient from "@/lib/api";

export interface Note {
  id: number;
  user_id: number;
  title: string;
  content: string;
  syllabus_id: number | null;
  ai_summary: string | null;
  summary_generated_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface NoteSummaryResult {
  note_id: number;
  ai_summary: string;
  summary_generated_at: string | null;
}

export const notesService = {
  async getNotes(syllabusId?: number): Promise<Note[]> {
    const params = syllabusId ? `?syllabus_id=${syllabusId}` : "";
    const res = await apiClient.get(`/api/v1/notes/${params}`);
    return res.data;
  },

  async getNote(noteId: number): Promise<Note> {
    const res = await apiClient.get(`/api/v1/notes/${noteId}`);
    return res.data;
  },

  async createNote(data: {
    title: string;
    content: string;
    syllabus_id?: number | null;
  }): Promise<Note> {
    const res = await apiClient.post("/api/v1/notes/", data);
    return res.data;
  },

  async updateNote(
    noteId: number,
    data: { title?: string; content?: string; syllabus_id?: number | null; ai_summary?: string | null }
  ): Promise<Note> {
    const res = await apiClient.put(`/api/v1/notes/${noteId}`, data);
    return res.data;
  },

  async deleteNote(noteId: number): Promise<void> {
    await apiClient.delete(`/api/v1/notes/${noteId}`);
  },

  /** Generate comprehensive study notes and AI summary from an uploaded syllabus. */
  async generateFromSyllabus(
    syllabusId: number,
    topicFocus?: string
  ): Promise<Note> {
    const res = await apiClient.post("/api/v1/notes/generate-from-syllabus", {
      syllabus_id: syllabusId,
      topic_focus: topicFocus || null,
    });
    return res.data;
  },

  /** Generate (or regenerate) an AI summary for a note. */
  async generateSummary(noteId: number): Promise<NoteSummaryResult> {
    const res = await apiClient.post(`/api/v1/notes/${noteId}/summary`);
    return res.data;
  },

  /** Delete the AI summary from a note without deleting the note itself. */
  async deleteSummary(noteId: number): Promise<void> {
    await apiClient.delete(`/api/v1/notes/${noteId}/summary`);
  },
};
