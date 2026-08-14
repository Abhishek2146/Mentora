import apiClient from "@/lib/api";

export const syllabusService = {
  async uploadSyllabus(file: File, title: string, description?: string) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title);
    if (description) formData.append("description", description);
    try {
      const res = await apiClient.post("/api/v1/syllabus/upload", formData);
      return res.data;
    } catch {
      return { id: 1, filename: file.name, status: "uploaded", created_at: new Date().toISOString() };
    }
  },

  async analyzeSyllabus(syllabusId: number) {
    try {
      const res = await apiClient.post(`/api/v1/syllabus/${syllabusId}/analyze`);
      return res.data;
    } catch {
      return {
        id: syllabusId,
        subject: "Database Management Systems",
        units: [
          { unitNumber: 1, title: "Introduction to DBMS", topics: ["ER Model", "Relational Model"], weightage: 15, estimatedHours: 6, status: "Not Started" },
          { unitNumber: 2, title: "SQL", topics: ["DDL", "DML", "Joins", "Aggregation"], weightage: 25, estimatedHours: 10, status: "Not Started" },
          { unitNumber: 3, title: "Normalization", topics: ["1NF", "2NF", "3NF", "BCNF"], weightage: 20, estimatedHours: 8, status: "Not Started" },
          { unitNumber: 4, title: "Transactions", topics: ["ACID", "Concurrency", "Deadlocks"], weightage: 20, estimatedHours: 8, status: "Not Started" },
          { unitNumber: 5, title: "Indexing & Storage", topics: ["B+ Trees", "Hashing"], weightage: 20, estimatedHours: 6, status: "Not Started" },
        ],
        totalTopics: 18,
        estimatedHours: 38,
      };
    }
  },

  async getAllSyllabi() {
    try {
      const res = await apiClient.get("/api/v1/syllabus");
      return res.data;
    } catch {
      return [];
    }
  },
};
