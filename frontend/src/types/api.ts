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
