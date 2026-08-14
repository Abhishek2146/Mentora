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
  role?: string;
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
