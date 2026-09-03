export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name?: string;
  role?: "student";
}

export interface UploadFileData {
  title: string;
  description?: string;
  file: File;
}

export interface QuizAttemptData {
  quiz_id: number;
  score: number;
  total_questions: number;
  correct_answers: number;
  time_taken?: number;
  answers?: Record<number, string>;
  is_passed: boolean;
}

export interface CodingSubmissionData {
  problem_id: number;
  code: string;
  language: string;
}

export interface ChatMessageData {
  message: string;
  syllabus_id?: number;
  session_id?: number;
}

export interface FileUploadResponse {
  file_path: string;
  file_type: string;
  extracted_text: string;
}

export interface SyllabusSearchParams {
  q: string;
  search_in?: string[];
  status?: string;
  page?: number;
  per_page?: number;
}

export interface SyllabusSearchResult {
  id: number;
  title: string;
  description?: string;
  file_type?: string;
  status: string;
  is_processed: boolean;
  is_ai_processed: boolean;
  created_at: string;
  updated_at: string;
  matched_fields: string[];
}

export interface SyllabusSearchResponse {
  items: SyllabusSearchResult[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  query: string;
}

export type NotificationType = "info" | "success" | "warning" | "error" | "reminder" | "achievement" | "system";
export type NotificationPriority = "low" | "normal" | "high" | "urgent";

export interface Notification {
  id: number;
  user_id: number;
  type: NotificationType;
  priority: NotificationPriority;
  title: string;
  message: string;
  related_entity_type?: string;
  related_entity_id?: number;
  is_read: boolean;
  is_archived: boolean;
  read_at?: string;
  created_at: string;
  updated_at: string;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  unread_count: number;
}

export interface NotificationStats {
  total: number;
  unread: number;
  archived: number;
  by_type: Record<string, number>;
  by_priority: Record<string, number>;
}

export interface BulkNotificationAction {
  notification_ids: number[];
  action: "read" | "unread" | "archive" | "delete";
}

export interface VoiceResponse {
  transcript: string;
  response: string;
  audio_url: string | null;
  session_id: number;
}

export interface VoiceSession {
  id: number;
  user_id: number;
  session_id: number | null;
  audio_path: string | null;
  transcript: string | null;
  response_text: string | null;
  voice_used: string;
  duration: number | null;
  created_at: string;
  updated_at: string | null;
}
