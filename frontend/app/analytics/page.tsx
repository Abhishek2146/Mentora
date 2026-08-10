import DashboardLayout from "@/components/layout/DashboardLayout";
import apiClient from "@/lib/api";
import { useEffect, useState } from "react";

export default function AnalyticsPage() {
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [studyTimeData, setStudyTimeData] = useState<any[]>([]);
  const [quizData, setQuizData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const [dashboard, studyTime, quiz] = await Promise.all([
        apiClient.get("/api/v1/analytics/dashboard"),
        apiClient.get("/api/v1/analytics/study-time?days=30"),
        apiClient.get("/api/v1/analytics/quiz-performance"),
      ]);
      setDashboardData(dashboard.data);
      setStudyTimeData(studyTime.data);
      setQuizData(quiz.data);
    } catch (error) {
      console.error("Failed to fetch analytics:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
        <p className="text-gray-600">Detailed insights into your learning performance.</p>

        {dashboardData && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-2xl font-bold text-primary-600">{dashboardData.data?.total_quizzes_taken || 0}</div>
              <p className="text-gray-500 text-sm">Quizzes Taken</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-2xl font-bold text-green-600">{dashboardData.data?.avg_quiz_score?.toFixed(1) || 0}%</div>
              <p className="text-gray-500 text-sm">Avg Quiz Score</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-2xl font-bold text-purple-600">{dashboardData.data?.coding_problems_solved || 0}</div>
              <p className="text-gray-500 text-sm">Coding Problems</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-2xl font-bold text-orange-600">{dashboardData.data?.overall_progress?.toFixed(1) || 0}%</div>
              <p className="text-gray-500 text-sm">Overall Progress</p>
            </div>
          </div>
        )}

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Quiz Performance</h2>
          <div className="space-y-3">
            {quizData.slice(0, 10).map((item, i) => (
              <div key={i} className="flex items-center space-x-4">
                <span className="text-sm text-gray-600 w-24">{item.date}</span>
                <div className="flex-1 bg-gray-200 rounded-full h-4">
                  <div
                    className="bg-primary-600 h-4 rounded-full"
                    style={{ width: `${item.avg_score}%` }}
                  />
                </div>
                <span className="text-sm font-medium w-16">{item.avg_score.toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Study Time (Last 30 Days)</h2>
          <div className="h-48">
            {studyTimeData.length > 0 ? (
              <div className="flex items-end justify-between h-full space-x-1">
                {studyTimeData.map((item, i) => (
                  <div key={i} className="flex flex-col items-center flex-1">
                    <div className="w-full bg-primary-100 rounded-t cursor-pointer hover:bg-primary-200 transition-colors" style={{ height: `${Math.max((item.study_time || 0) / 10, 20)}px` }}>
                      <span className="text-xs text-gray-600 block text-center mt-1">
                        {(item.study_time || 0)}m
                      </span>
                    </div>
                    <span className="text-xs text-gray-500 mt-1">
                      {new Date(item.date).toLocaleDateString("en-US", { weekday: "short" })}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">No study data available yet.</p>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
