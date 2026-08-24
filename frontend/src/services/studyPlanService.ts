import apiClient from "@/lib/api";

export interface StudyTask {
  id: number;
  title: string;
  description: string | null;
  due_date: string | null;
  completed: boolean;
  task_type: string | null;
}

export interface StudyPlan {
  id: number;
  title: string;
  description: string | null;
  start_date: string;
  end_date: string | null;
  syllabus_id: number | null;
  is_active: boolean;
  plan_data: any;
  tasks: StudyTask[];
}

export const studyPlanService = {
  async getAllPlans(): Promise<StudyPlan[]> {
    const res = await apiClient.get("/api/v1/study-plan/");
    return res.data;
  },

  async generatePlan(
    syllabusId: number,
    startDate: string,
    endDate?: string
  ): Promise<StudyPlan> {
    const res = await apiClient.post("/api/v1/study-plan/", {
      title: "AI Study Plan",
      syllabus_id: syllabusId,
      start_date: startDate,
      end_date: endDate || null,
      is_ai_generated: true,
    });
    return res.data;
  },

  async getPlan(planId: number): Promise<StudyPlan> {
    const res = await apiClient.get(`/api/v1/study-plan/${planId}`);
    return res.data;
  },

  async toggleTask(taskId: number, completed: boolean): Promise<any> {
    const res = await apiClient.put(`/api/v1/study-plan/tasks/${taskId}`, {
      completed,
    });
    return res.data;
  },

  async deletePlan(planId: number): Promise<void> {
    await apiClient.delete(`/api/v1/study-plan/${planId}`);
  },
};
