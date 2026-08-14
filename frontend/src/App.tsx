import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import DashboardPage from "@/pages/Dashboard";
import AiTutorPage from "@/pages/AiTutor";
import FlashcardsPage from "@/pages/Flashcards";
import StudyPlanPage from "@/pages/StudyPlan";
import AnalyticsPage from "@/pages/Analytics";
import DailyQuizPage from "@/pages/DailyQuiz";
import MCQPage from "@/pages/MCQ";
import ExamSimulatorPage from "@/pages/ExamSimulator";
import WeakTopicsPage from "@/pages/WeakTopics";
import RevisionPlanPage from "@/pages/RevisionPlan";
import UploadSyllabusPage from "@/pages/UploadSyllabus";
import CodingPracticePage from "@/pages/CodingPractice";
import VoiceLearningPage from "@/pages/VoiceLearning";
import ProfilePage from "@/pages/Profile";
import SettingsPage from "@/pages/Settings";
import ProgressPage from "@/pages/Progress";
import RegisterPage from "@/pages/Register";
import LoginPage from "@/pages/Login";
import ForgotPasswordPage from "@/pages/ForgotPassword";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/ai-tutor" element={<AiTutorPage />} />
        <Route path="/flashcards" element={<FlashcardsPage />} />
        <Route path="/study-plan" element={<StudyPlanPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/daily-quiz" element={<DailyQuizPage />} />
        <Route path="/mcq" element={<MCQPage />} />
        <Route path="/exam-simulator" element={<ExamSimulatorPage />} />
        <Route path="/weak-topics" element={<WeakTopicsPage />} />
        <Route path="/revision-plan" element={<RevisionPlanPage />} />
        <Route path="/upload-syllabus" element={<UploadSyllabusPage />} />
        <Route path="/coding-practice" element={<CodingPracticePage />} />
        <Route path="/voice-learning" element={<VoiceLearningPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/progress" element={<ProgressPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
