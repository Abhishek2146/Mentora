export const APP_NAME = "Mentora";
export const APP_VERSION = "1.0.0";

export const ROUTES = {
  DASHBOARD: "/dashboard",
  AI_TUTOR: "/ai-tutor",
  FLASHCARDS: "/flashcards",
  STUDY_PLAN: "/study-plan",
  ANALYTICS: "/analytics",
  DAILY_QUIZ: "/daily-quiz",
  MCQ: "/mcq",
  EXAM_SIMULATOR: "/exam-simulator",
  WEAK_TOPICS: "/weak-topics",
  REVISION_PLAN: "/revision-plan",
  UPLOAD_SYLLABUS: "/upload-syllabus",
  CODING_PRACTICE: "/coding-practice",
  VOICE_LEARNING: "/voice-learning",
  PROFILE: "/profile",
  SETTINGS: "/settings",
  PROGRESS: "/progress",
  LOGIN: "/login",
  REGISTER: "/register",
  FORGOT_PASSWORD: "/forgot-password",
} as const;

export const DIFFICULTY_COLORS = {
  Easy:   { bg: "bg-success-50",  text: "text-success-600",  dark: "dark:bg-green-900/40 dark:text-green-400"  },
  Medium: { bg: "bg-warning-50",  text: "text-warning-600",  dark: "dark:bg-yellow-900/40 dark:text-yellow-400" },
  Hard:   { bg: "bg-danger-50",   text: "text-danger-600",   dark: "dark:bg-red-900/40 dark:text-red-400"       },
} as const;

export const SUBJECT_COLORS = [
  "from-primary-500 to-primary-600",
  "from-secondary-500 to-secondary-600",
  "from-emerald-500 to-emerald-600",
  "from-orange-500 to-orange-600",
  "from-pink-500 to-pink-600",
  "from-cyan-500 to-cyan-600",
];
