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
import RegisterPage from "@/pages/Register";
import LoginPage from "@/pages/Login";
import ForgotPasswordPage from "@/pages/ForgotPassword";
import ResetPasswordPage from "@/pages/ResetPassword";
import VerifyOtpPage from "@/pages/VerifyOtp";
import SetNewPasswordPage from "@/pages/SetNewPassword";
import SearchPage from "@/pages/Search";
import SyllabusDetailPage from "@/pages/SyllabusDetail";
import { ProtectedRoute, PublicRoute, AdminRoute } from "@/components/ProtectedRoute";
import { useAuthStore } from "@/store/authStore";
import HomePage from "@/pages/HomePage";
import AdminRegisterPage from "@/pages/AdminRegister";
import AdminDashboardPage from "@/pages/AdminDashboard";
import UploadSyllabus from "./pages/UploadSyllabus";
import CodingPractice from "./pages/CodingPractice";
import VoiceLearning from "./pages/VoiceLearning";
import Profile from "./pages/Profile";
import Settings from "./pages/Settings";
import Progress from "./pages/Progress";

export default function App() {
  useEffect(() => {
    useAuthStore.getState().checkAuth();
  }, []);

  return (
    <BrowserRouter>
<Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/search" element={<ProtectedRoute><SearchPage /></ProtectedRoute>} />
        <Route path="/syllabus/:id" element={<ProtectedRoute><SyllabusDetailPage /></ProtectedRoute>} />
        <Route path="/ai-tutor" element={<ProtectedRoute><AiTutorPage /></ProtectedRoute>} />
        <Route path="/flashcards" element={<ProtectedRoute><FlashcardsPage /></ProtectedRoute>} />
        <Route path="/study-plan" element={<ProtectedRoute><StudyPlanPage /></ProtectedRoute>} />
        <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
        <Route path="/daily-quiz" element={<ProtectedRoute><DailyQuizPage /></ProtectedRoute>} />
        <Route path="/mcq" element={<ProtectedRoute><MCQPage /></ProtectedRoute>} />
        <Route path="/exam-simulator" element={<ProtectedRoute><ExamSimulatorPage /></ProtectedRoute>} />
        <Route path="/weak-topics" element={<ProtectedRoute><WeakTopicsPage /></ProtectedRoute>} />
        <Route path="/revision-plan" element={<ProtectedRoute><RevisionPlanPage /></ProtectedRoute>} />
        <Route path="/upload-syllabus" element={<ProtectedRoute><UploadSyllabus /></ProtectedRoute>} />
        <Route path="/coding-practice" element={<ProtectedRoute><CodingPractice /></ProtectedRoute>} />
        <Route path="/voice-learning" element={<ProtectedRoute><VoiceLearning /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><Profile/></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
        <Route path="/progress" element={<ProtectedRoute><Progress/></ProtectedRoute>} />
        <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
        <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
        <Route path="/forgot-password" element={<PublicRoute><ForgotPasswordPage /></PublicRoute>} />
        <Route path="/reset-password" element={<PublicRoute><ResetPasswordPage /></PublicRoute>} />
        <Route path="/verify-otp" element={<PublicRoute><VerifyOtpPage /></PublicRoute>} />
        <Route path="/set-new-password" element={<PublicRoute><SetNewPasswordPage /></PublicRoute>} />
        <Route path="/admin/register" element={<AdminRegisterPage />} />
        <Route path="/admin/dashboard" element={<AdminRoute><AdminDashboardPage /></AdminRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}