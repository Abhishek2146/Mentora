import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import Link from "next/link";

export default function HomePage() {
  const router = useRouter();
  const { isAuthenticated, checkAuth, user } = useAuthStore();

  useEffect(() => {
    checkAuth();
    if (isAuthenticated) {
      router.push("/dashboard");
    }
  }, [isAuthenticated, checkAuth, router]);

  if (isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-600 via-secondary-600 to-primary-800 flex items-center justify-center">
      <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
        <h1 className="text-4xl sm:text-5xl font-extrabold text-white mb-6">
          Mentora
        </h1>
        <p className="text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
          Your AI-powered learning companion. Upload your syllabus, get personalized
          study plans, generate quizzes and flashcards, and master any subject with
          adaptive AI tutoring.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 text-center">
            <div className="text-3xl font-bold text-white">AI</div>
            <p className="text-primary-200 mt-1">Syllabus Parsing &amp; Content Extraction</p>
          </div>
          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 text-center">
            <div className="text-3xl font-bold text-white">Adaptive</div>
            <p className="text-primary-200 mt-1">Study Plans &amp; Revision Schedules</p>
          </div>
          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 text-center">
            <div className="text-3xl font-bold text-white">Practice</div>
            <p className="text-primary-200 mt-1">Quizzes, Flashcards &amp; Coding</p>
          </div>
        </div>

        <div className="space-x-4 space-y-4 sm:space-y-0">
          <Link
            href="/login"
            className="inline-block px-8 py-3 bg-white text-primary-600 font-semibold rounded-lg shadow-lg hover:bg-gray-100 transition-colors"
          >
            Sign In
          </Link>
          <Link
            href="/register"
            className="inline-block px-8 py-3 border-2 border-white text-white font-semibold rounded-lg hover:bg-white/10 transition-colors"
          >
            Get Started
          </Link>
        </div>

        <p className="mt-8 text-sm text-primary-200">
          No credit card required. Start learning smarter today.
        </p>
      </div>
    </div>
  );
}
