export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  role: "student" | "instructor" | "admin";
  is_active: boolean;
  is_verified: boolean;
  avatar_url: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type UserRole = "student" | "instructor" | "admin";

export interface Syllabus {
  id: number;
  title: string;
  description: string | null;
  file_path: string | null;
  file_type: string | null;
  status: "uploaded" | "processing" | "parsed" | "failed";
  parsed_data: any | null;
  subjects: SubjectWithChapters[];
  created_at: string;
  updated_at: string | null;
}

export interface Subject {
  id: number;
  name: string;
  description: string | null;
  order: number;
}

export interface Chapter {
  id: number;
  name: string;
  description: string | null;
  order: number;
  subject_id: number;
}

export interface SubjectWithChapters extends Subject {
  chapters: Chapter[];
}

export interface StudyPlan {
  id: number;
  title: string;
  description: string | null;
  start_date: string;
  end_date: string | null;
  syllabus_id: number | null;
  is_active: boolean;
  plan_data: any | null;
  tasks: StudyTask[];
  created_at: string;
  updated_at: string | null;
}

export interface StudyTask {
  id: number;
  title: string;
  description: string | null;
  due_date: string | null;
  completed: boolean;
  task_type: string | null;
}

export interface FlashcardDeck {
  id: number;
  title: string;
  description: string | null;
  syllabus_id: number | null;
  is_ai_generated: boolean;
  flashcards: Flashcard[];
  created_at: string;
  updated_at: string | null;
}

export interface Flashcard {
  id: number;
  deck_id: number;
  front: string;
  back: string;
  difficulty: string;
  ease_factor: number;
  interval: number;
  repetitions: number;
  next_review: string | null;
  last_reviewed: string | null;
}

export interface Question {
  id: number;
  question_type: string;
  question_text: string;
  options: string[] | null;
  correct_answer: string;
  explanation: string | null;
  difficulty: string;
  order: number;
}

export interface Quiz {
  id: number;
  title: string;
  description: string | null;
  syllabus_id: number | null;
  subject_id: number | null;
  chapter_id: number | null;
  num_questions: number;
  time_limit: number | null;
  is_active: boolean;
  is_ai_generated: boolean;
  questions: Question[];
  created_at: string;
  updated_at: string | null;
}

export interface QuizAttempt {
  id: number;
  user_id: number;
  quiz_id: number;
  score: number;
  total_questions: number;
  correct_answers: number;
  time_taken: number | null;
  answers: any | null;
  is_passed: boolean;
  created_at: string | null;
}

export interface CodingProblem {
  id: number;
  title: string;
  description: string;
  difficulty: "easy" | "medium" | "hard";
  category: string | null;
  tags: string[] | null;
  starter_code: string | null;
  test_cases: any[] | null;
  constraints: string | null;
  user_id: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface CodingSubmission {
  id: number;
  user_id: number;
  problem_id: number;
  code: string;
  language: string;
  status: string;
  output: string | null;
  passed: boolean;
  execution_time: number | null;
  memory_used: number | null;
}

export interface Progress {
  id: number;
  user_id: number;
  progress_type: string;
  value: number;
  target_value: number;
  syllabus_id: number | null;
  created_at: string;
}

export interface WeakTopic {
  id: number;
  user_id: number;
  topic_name: string;
  syllabus_id: number | null;
  subject_id: number | null;
  chapter_id: number | null;
  accuracy: number;
  confidence_level: number;
  total_attempts: number;
  last_attempted: string | null;
  recommended_action: string | null;
}

export interface StudySession {
  id: number;
  title: string;
  description: string | null;
  start_time: string;
  end_time: string | null;
  completed: boolean;
}

export interface WeeklyReport {
  id: number;
  user_id: number;
  week_start: string;
  week_end: string;
  study_time_minutes: number;
  topics_studied: string | null;
  quizzes_taken: number;
  quizzes_passed: number;
  flashcards_reviewed: number;
  coding_problems_solved: number;
  report_data: string | null;
}

export interface ChatSession {
  id: number;
  user_id: number;
  title: string | null;
  model_used: string;
  syllabus_id: number | null;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string | null;
}

export interface ChatMessage {
  id: number;
  session_id: number;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  sequence: number;
}

export interface AnalyticsData {
  total_quizzes_taken: number;
  avg_quiz_score: number;
  coding_problems_solved: number;
  overall_progress: number;
  weak_topics_count: number;
}

export interface ActivityLogEntry {
  type: string;
  description: string;
  timestamp: string | null;
}

export interface DashboardStats {
  syllabi_count: number;
  active_plans: number;
  pending_tasks: number;
  total_attempts: number;
  avg_score: number;
  coding_solved: number;
}

export interface DashboardResponse {
  user: {
    username: string;
    full_name: string | null;
    role: string;
  };
  stats: DashboardStats;
  overall_progress: number;
  upcoming_tasks: {
    id: number;
    title: string;
    due_date: string | null;
    task_type: string | null;
  }[];
}

export * from "./api";
