import { useState, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  LineChart,
  Line,
  CartesianGrid,
} from "recharts";
import { TrendingUp, Clock, Trophy, Flame, Loader2 } from "lucide-react";
import { analyticsService, DashboardStats, QuizPerformance, SubjectBreakdown, StudyTimeTrend } from "@/services/analyticsService";

export default function Analytics() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [quizPerformance, setQuizPerformance] = useState<QuizPerformance[]>([]);
  const [subjects, setSubjects] = useState<SubjectBreakdown[]>([]);
  const [studyTrend, setStudyTrend] = useState<StudyTimeTrend[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [dashData, quizData, subjectData, trendData] = await Promise.all([
          analyticsService.getDashboard(),
          analyticsService.getQuizPerformance(),
          analyticsService.getSubjectBreakdown(),
          analyticsService.getStudyTimeTrend(30),
        ]);
        setStats(dashData.cards);
        setQuizPerformance(quizData);
        setSubjects(subjectData);
        setStudyTrend(trendData);
      } catch (e) {
        console.error("Failed to load analytics:", e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const weeklyChart = quizPerformance.map((q) => ({
    day: new Date(q.date).toLocaleDateString("en-US", { weekday: "short" }),
    score: Math.round(q.avg_score),
  }));

  const masteryChart = subjects.map((s) => ({
    topic: s.subject_name,
    mastery: Math.round(s.avg_score),
  }));

  const trendChart = studyTrend.map((t) => ({
    date: new Date(t.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    hours: t.study_time ? Math.round((t.study_time / 3600) * 10) / 10 : 0,
  }));

  if (loading) {
    return (
      <AppLayout title="Analytics">
        <div className="max-w-6xl mx-auto flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Analytics">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          {[
            {
              label: "Total Study Hours",
              value: `${stats?.study_hours.total ?? 0}h`,
              icon: Clock,
              color: "text-primary-600",
              bg: "bg-primary-50 dark:bg-primary-900/30",
            },
            {
              label: "Quiz Average",
              value: `${Math.round(stats?.quiz_average.value ?? 0)}%`,
              icon: Trophy,
              color: "text-success-600",
              bg: "bg-success-50 dark:bg-success-900/30",
            },
            {
              label: "Current Streak",
              value: `${stats?.study_hours.week_change ?? 0}h`,
              icon: Flame,
              color: "text-warning-600",
              bg: "bg-warning-50 dark:bg-warning-900/30",
            },
            {
              label: "Topics Mastered",
              value: `${stats?.topics_mastered.mastered ?? 0}/${stats?.topics_mastered.total ?? 0}`,
              icon: TrendingUp,
              color: "text-secondary-600",
              bg: "bg-secondary-50 dark:bg-secondary-900/30",
            },
          ].map((s) => (
            <div key={s.label} className="stat-card">
              <div className={`w-10 h-10 rounded-xl ${s.bg} flex items-center justify-center`}>
                <s.icon className={`w-5 h-5 ${s.color}`} />
              </div>
              <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">{s.value}</p>
              <p className="text-xs text-slate-500">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          <div className="card p-5">
            <h3 className="font-bold text-slate-800 dark:text-slate-100 mb-4">Quiz Scores</h3>
            {weeklyChart.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={weeklyChart} barSize={28}>
                  <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#94a3b8" }} />
                  <YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#94a3b8" }} />
                  <Tooltip contentStyle={{ borderRadius: 12, border: "none" }} formatter={(v: any) => [`${v}%`, "Score"]} />
                  <Bar dataKey="score" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-slate-400 text-center py-8">No quiz data yet. Take a quiz to see your performance!</p>
            )}
          </div>

          <div className="card p-5">
            <h3 className="font-bold text-slate-800 dark:text-slate-100 mb-4">Subject Mastery</h3>
            {masteryChart.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <RadarChart data={masteryChart}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis dataKey="topic" tick={{ fontSize: 10, fill: "#94a3b8" }} />
                  <Radar dataKey="mastery" fill="#8b5cf6" fillOpacity={0.25} stroke="#8b5cf6" strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-slate-400 text-center py-8">No subject data yet. Complete quizzes to see mastery!</p>
            )}
          </div>

          <div className="card p-5 lg:col-span-2">
            <h3 className="font-bold text-slate-800 dark:text-slate-100 mb-4">Study Hours Trend</h3>
            {trendChart.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={trendChart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#94a3b8" }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#94a3b8" }} />
                  <Tooltip contentStyle={{ borderRadius: 12, border: "none" }} formatter={(v: any) => [`${v}h`, "Hours"]} />
                  <Line dataKey="hours" stroke="#0ea5e9" strokeWidth={3} dot={{ r: 5, fill: "#0ea5e9" }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-slate-400 text-center py-8">No study time data yet. Take quizzes to track your hours!</p>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
