export interface UserUpdate {
  email?: string;
  username?: string;
  full_name?: string | null;
  avatar_url?: string | null;
}

export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  role: "student" | "admin";
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

export type UserRole = "student" | "admin";

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
  language: string;
  tags: string[] | null;
  starter_code: string | null;
  input_format: string | null;
  output_format: string | null;
  examples: Array<{ input?: string; output?: string; explanation?: string }> | null;
  test_cases: Array<{ input?: string; expected?: string }> | null;
  hints: string[] | null;
  constraints: string | null;
  user_id: number | null;
  is_ai_generated?: boolean;
  created_at?: string;
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
  score: number;
  passed_test_cases: number;
  total_test_cases: number;
  execution_time: number | null;
  error_message: string | null;
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

export interface AdminDashboardStats {
  stats: {
    total_users: number;
    total_students: number;
    total_admins: number;
    active_users: number;
    total_syllabi: number;
    total_study_plans: number;
    total_quizzes: number;
    total_quiz_attempts: number;
    total_coding_problems: number;
    total_coding_submissions: number;
    total_flashcard_decks: number;
    avg_quiz_score: number;
  };
  recent_registrations: {
    id: number;
    username: string;
    full_name: string | null;
    email: string;
    role: string;
    is_active: boolean;
    created_at: string | null;
  }[];
}

export type PlanType = "FREE" | "SUBSCRIPTION";
export type BillingCycle = "NONE" | "MONTHLY" | "YEARLY";
export type SubscriptionStatus = "ACTIVE" | "EXPIRED" | "CANCELLED";

export type UsageTypeKey =
  | "AI_CHAT"
  | "NOTE_GENERATION"
  | "QUIZ_GENERATION"
  | "FLASHCARD_GENERATION"
  | "STUDY_PLAN_GENERATION"
  | "CODING_PROBLEM_GENERATION"
  | "SYLLABUS_ANALYSIS";

export const USAGE_TYPE_LABELS: Record<UsageTypeKey, string> = {
  AI_CHAT: "AI Tutor Chat",
  NOTE_GENERATION: "Note Generation",
  QUIZ_GENERATION: "Quiz Generation",
  FLASHCARD_GENERATION: "Flashcard Generation",
  STUDY_PLAN_GENERATION: "Study Plan Generation",
  CODING_PROBLEM_GENERATION: "Coding Problem Generation",
  SYLLABUS_ANALYSIS: "Syllabus Analysis",
};

export interface Subscription {
  id: number;
  user_id: number;
  plan_type: PlanType;
  billing_cycle: BillingCycle;
  status: SubscriptionStatus;
  started_at: string | null;
  expires_at: string | null;
  auto_renew: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface FeatureUsage {
  usage_type: UsageTypeKey;
  daily_limit: number;
  used: number;
  remaining: number;
  usage_date: string;
}

export interface UsageReport {
  user_id: number;
  plan_type: PlanType;
  billing_cycle: BillingCycle;
  status: SubscriptionStatus;
  expires_at: string | null;
  effective_plan: PlanType;
  rate_limit_per_minute: number;
  features: FeatureUsage[];
  usage_date: string;
}

export interface PlanInfo {
  plan_type: PlanType;
  billing_cycles: string[];
  rate_limit_per_minute: number;
  daily_limits: Record<UsageTypeKey, number>;
  price_monthly_paisa?: number | null;
  price_yearly_paisa?: number | null;
  price_monthly_npr?: number | null;
  price_yearly_npr?: number | null;
}

export interface PlansResponse {
  plans: PlanInfo[];
}

export interface KhaltiInitiateResponse {
  pidx: string;
  payment_url: string;
  expires_at: string | null;
  expires_in: number | null;
  purchase_order_id: string;
  purchase_order_name: string;
  amount: number;
  billing_cycle: BillingCycle;
}

export interface KhaltiVerifyResponse {
  pidx: string;
  status: string;
  transaction_id: string | null;
  total_amount: number | null;
  fee: number | null;
  refunded: boolean | null;
  purchase_order_id: string;
  billing_cycle: string;
  subscription: Subscription | null;
  message: string;
}

export interface KhaltiConfig {
  enabled: boolean;
  base_url: string;
  website_url: string;
  return_url: string;
  prices: {
    monthly_paisa: number;
    yearly_paisa: number;
    monthly_npr: number;
    yearly_npr: number;
    currency: string;
  };
  billing_cycles: BillingCycle[];
}

export interface PaymentOut {
  id: number;
  purchase_order_id: string;
  pidx: string;
  billing_cycle: string;
  amount: number;
  total_amount: number | null;
  status: string;
  payment_url: string | null;
  transaction_id: string | null;
  expires_at: string | null;
  created_at: string | null;
}

export * from "./api";
