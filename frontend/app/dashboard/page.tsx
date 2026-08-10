import DashboardLayout from "@/app/dashboard/layout";
import { DashboardStats } from "@/types";
import { useEffect, useState } from "react";
import apiClient from "@/lib/api";
import Link from "next/link";
import {
  BookOpenIcon,
  QuestionMarkCircleIcon,
  RectangleStackIcon,
  CodeBracketIcon,
  ChartBarIcon,
  ClockIcon,
  PlayIcon,
} from "@heroicons/react/24/outline";

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await apiClient.get("/api/v1/dashboard/");
      setStats(response.data);
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
    } finally {
      setLoading(false);
    }
  };

  const quickActions = [
    { name: "Upload New Syllabus", href: "/upload-syllabus", icon: BookOpenIcon, color: "bg-blue-500" },
    { name: "Start Daily Quiz", href: "/daily-quiz", icon: QuestionMarkCircleIcon, color: "bg-green-500" },
    { name: "Review Flashcards", href: "/flashcards", icon: RectangleStackIcon, color: "bg-purple-500" },
    { name: "Coding Practice", href: "/coding-practice", icon: CodeBracketIcon, color: "bg-orange-500" },
    { name: "AI Tutor Chat", href: "/ai-tutor", icon: ChartBarIcon, color: "bg-pink-500" },
    { name: "View Study Plan", href: "/study-plan", icon: ClockIcon, color: "bg-indigo-500" },
  ];

  if (loading) {
    return (
      <DashboardLayout>
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">Welcome back! Here's your learning overview.</p>
        </div>

        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-3xl font-bold text-primary-600">{stats.stats?.syllabi_count || 0}</div>
              <p className="text-gray-500 text-sm mt-1">Syllabi Uploaded</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-3xl font-bold text-secondary-600">{stats.stats?.active_plans || 0}</div>
              <p className="text-gray-500 text-sm mt-1">Active Study Plans</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-3xl font-bold text-green-600">{stats.stats?.avg_score?.toFixed(0) || 0}%</div>
              <p className="text-gray-500 text-sm mt-1">Average Quiz Score</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-3xl font-bold text-orange-600">{stats.stats?.coding_solved || 0}</div>
              <p className="text-gray-500 text-sm mt-1">Coding Problems Solved</p>
            </div>
          </div>
        )}

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {quickActions.map((action) => (
              <Link
                key={action.name}
                href={action.href}
                className="flex items-center space-x-3 p-4 rounded-lg border border-gray-200 hover:bg-gray-50 hover:border-primary-300 transition-colors group"
              >
                <div className={`${action.color} p-2 rounded-lg text-white`}>
                  <action.icon className="w-5 h-5" />
                </div>
                <span className="font-medium text-gray-700 group-hover:text-primary-600">
                  {action.name}
                </span>
              </Link>
            ))}
          </div>
        </div>

        {stats?.upcoming_tasks && stats.upcoming_tasks.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Upcoming Tasks</h2>
            <div className="space-y-3">
              {stats.upcoming_tasks.map((task: any) => (
                <div
                  key={task.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div>
                    <span className="font-medium">{task.title}</span>
                    {task.due_date && (
                      <span className="text-sm text-gray-500 ml-2">
                        Due: {new Date(task.due_date).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                  <span className="text-xs px-2 py-1 bg-gray-200 rounded-full">
                    {task.task_type || "study"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
