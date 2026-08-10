import DashboardLayout from "@/components/layout/DashboardLayout";
import apiClient from "@/lib/api";
import { useEffect, useState } from "react";

export default function ProgressPage() {
  const [progressData, setProgressData] = useState<any[]>([]);
  const [overallProgress, setOverallProgress] = useState(0);

  useEffect(() => {
    fetchProgress();
  }, []);

  const fetchProgress = async () => {
    try {
      const response = await apiClient.get("/api/v1/progress/");
      setProgressData(response.data);
      const overall = response.data.find((p: any) => p.progress_type === "overall");
      setOverallProgress(overall?.value || 0);
    } catch (error) {
      console.error("Failed to fetch progress:", error);
    }
  };

  const progressPercentage = Math.round(overallProgress);

  const getProgressColor = (value: number) => {
    if (value >= 80) return "bg-green-500";
    if (value >= 60) return "bg-yellow-500";
    return "bg-red-500";
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900">Progress</h1>
        <p className="text-gray-600">Track your learning journey and progress over time.</p>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Overall Progress</h2>
          <div className="flex items-center space-x-4">
            <div className="w-32 h-32 relative">
              <svg viewBox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke="#e5e7eb"
                  strokeWidth="8"
                />
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="8"
                  strokeDasharray="251.2"
                  strokeDashoffset={251.2 - (progressPercentage / 100) * 251.2}
                  className={getProgressColor(progressPercentage)}
                  style={{ transition: "stroke-dashoffset 0.5s" }}
                  transform="rotate(-90 50 50)"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-2xl font-bold">{progressPercentage}%</span>
              </div>
            </div>
            <div>
              <p className="text-gray-600">Keep going! You're making great progress.</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Subject Breakdown</h2>
          <div className="space-y-4">
            {progressData
              .filter((p) => p.progress_type !== "overall")
              .map((p) => (
                <div key={p.id}>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">{p.progress_type}</span>
                    <span className="text-sm text-gray-500">{Math.round(p.value)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${getProgressColor(p.value)}`}
                      style={{ width: `${p.value}%` }}
                    />
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
