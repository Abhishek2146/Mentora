import DashboardLayout from "@/components/layout/DashboardLayout";
import apiClient from "@/lib/api";
import { useEffect, useState } from "react";
import { WeakTopic } from "@/types";

export default function WeakTopicsPage() {
  const [weakTopics, setWeakTopics] = useState<WeakTopic[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchWeakTopics();
  }, []);

  const fetchWeakTopics = async () => {
    try {
      const response = await apiClient.get("/api/v1/weak-topics/");
      setWeakTopics(response.data);
    } catch (error) {
      console.error("Failed to fetch weak topics:", error);
    }
  };

  const detectWeakTopics = async () => {
    setLoading(true);
    try {
      await apiClient.post("/api/v1/weak-topics/detect");
      fetchWeakTopics();
    } catch (error) {
      console.error("Failed to detect weak topics:", error);
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 70) return "bg-green-100 text-green-800";
    if (confidence >= 40) return "bg-yellow-100 text-yellow-800";
    return "bg-red-100 text-red-800";
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-900">Weak Topics</h1>
          <button
            onClick={detectWeakTopics}
            disabled={loading}
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? "Analyzing..." : "Detect Weak Topics"}
          </button>
        </div>

        <div className="bg-white rounded-lg shadow">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Topic</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Accuracy</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Confidence</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Attempts</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {weakTopics.map((topic) => (
                  <tr key={topic.id} className="border-t">
                    <td className="py-3 px-4 font-medium">{topic.topic_name}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2">
                        <span>{Math.round(topic.accuracy)}%</span>
                        <div className="w-16 h-2 bg-gray-200 rounded-full">
                          <div
                            className="h-2 rounded-full bg-red-500"
                            style={{ width: `${topic.accuracy}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 rounded-full text-xs ${getConfidenceColor(topic.confidence_level)}`}>
                        {Math.round(topic.confidence_level)}%
                      </span>
                    </td>
                    <td className="py-3 px-4">{topic.total_attempts}</td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {topic.recommended_action || "Review this topic"}
                    </td>
                  </tr>
                ))}
              </tbody>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
