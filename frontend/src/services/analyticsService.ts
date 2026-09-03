import apiClient from "@/lib/api";

export interface DashboardStats {
  study_hours: { total: number; week_change: number };
  quiz_average: { value: number; week_change: number | null };
  flashcards_done: { total: number; week_change: number };
  topics_mastered: { mastered: number; total: number; week_change: number };
  tasks_due_today: number;
}

export interface DashboardData {
  user: { username: string; full_name: string | null; role: string };
  stats: {
    syllabi_count: number;
    active_plans: number;
    pending_tasks: number;
    total_attempts: number;
    avg_score: number;
    coding_solved: number;
  };
  cards: DashboardStats;
  overall_progress: number;
  upcoming_tasks: {
    id: number;
    title: string;
    due_date: string | null;
    task_type: string | null;
  }[];
}

export interface QuizPerformance {
  date: string;
  avg_score: number;
  attempts: number;
}

export interface SubjectBreakdown {
  subject_id: number;
  subject_name: string;
  avg_score: number;
  attempts: number;
}

export interface StudyTimeTrend {
  date: string;
  study_time: number;
}

export interface ActivityLog {
  type: string;
  description: string;
  timestamp: string | null;
}

export interface WeakTopic {
  topic_name: string;
  accuracy: number;
}

export const analyticsService = {
  async getDashboard(): Promise<DashboardData> {
    const res = await apiClient.get("/api/v1/dashboard/");
    return res.data;
  },

  async getAnalyticsSummary() {
    const res = await apiClient.get("/api/v1/analytics/dashboard");
    return res.data;
  },

  async getStudyTimeTrend(days: number = 30): Promise<StudyTimeTrend[]> {
    const res = await apiClient.get("/api/v1/analytics/study-time", { params: { days } });
    return res.data;
  },

  async getQuizPerformance(): Promise<QuizPerformance[]> {
    const res = await apiClient.get("/api/v1/analytics/quiz-performance");
    return res.data;
  },

  async getSubjectBreakdown(): Promise<SubjectBreakdown[]> {
    const res = await apiClient.get("/api/v1/analytics/subject-breakdown");
    return res.data;
  },

  async getActivityLog(limit: number = 20): Promise<ActivityLog[]> {
    const res = await apiClient.get("/api/v1/analytics/activity", { params: { limit } });
    return res.data;
  },

  async getWeakTopics(): Promise<WeakTopic[]> {
    const res = await apiClient.get("/api/v1/weak-topics/");
    return res.data;
  },
};
