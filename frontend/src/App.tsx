import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
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
import { ProtectedRoute, PublicRoute } from "@/components/ProtectedRoute";
import { useAuthStore } from "@/store/authStore";

export default function App() {
  useEffect(() => {
    useAuthStore.getState().checkAuth();
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/ai-tutor" element={<ProtectedRoute><AiTutorPage /></ProtectedRoute>} />
        <Route path="/flashcards" element={<ProtectedRoute><FlashcardsPage /></ProtectedRoute>} />
        <Route path="/study-plan" element={<ProtectedRoute><StudyPlanPage /></ProtectedRoute>} />
        <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
        <Route path="/daily-quiz" element={<ProtectedRoute><DailyQuizPage /></ProtectedRoute>} />
        <Route path="/mcq" element={<ProtectedRoute><MCQPage /></ProtectedRoute>} />
        <Route path="/exam-simulator" element={<ProtectedRoute><ExamSimulatorPage /></ProtectedRoute>} />
        <Route path="/weak-topics" element={<ProtectedRoute><WeakTopicsPage /></ProtectedRoute>} />
        <Route path="/revision-plan" element={<ProtectedRoute><RevisionPlanPage /></ProtectedRoute>} />
        <Route path="/upload-syllabus" element={<ProtectedRoute><UploadSyllabusPage /></ProtectedRoute>} />
        <Route path="/coding-practice" element={<ProtectedRoute><CodingPracticePage /></ProtectedRoute>} />
        <Route path="/voice-learning" element={<ProtectedRoute><VoiceLearningPage /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
        <Route path="/progress" element={<ProtectedRoute><ProgressPage /></ProtectedRoute>} />
        <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
        <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
        <Route path="/forgot-password" element={<PublicRoute><ForgotPasswordPage /></PublicRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
