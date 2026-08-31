import { useState, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { Brain, CreditCard, Trophy, Flame, Clock, Target, Upload, FileText, ArrowRight, Loader2 } from "lucide-react";
import { Link } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, RadarChart, PolarGrid, PolarAngleAxis, Radar } from "recharts";
import { useAuthStore } from "@/store/authStore";
import { analyticsService, DashboardData, QuizPerformance, SubjectBreakdown } from "@/services/analyticsService";

const quickActions = [
  { label: "Upload Syllabus", icon: Upload, path: "/upload-syllabus" },
  { label: "AI Tutor", icon: Brain, path: "/ai-tutor" },
  { label: "Flashcards", icon: CreditCard, path: "/flashcards" },
  { label: "Daily Quiz", icon: Trophy, path: "/daily-quiz" },
];

export default function Dashboard() {
  const { user } = useAuthStore();
  const firstName = user?.full_name?.split(" ")[0] || user?.username || "there";

  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [quizPerformance, setQuizPerformance] = useState<QuizPerformance[]>([]);
  const [subjects, setSubjects] = useState<SubjectBreakdown[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [dashData, quizData, subjectData] = await Promise.all([
          analyticsService.getDashboard(),
          analyticsService.getQuizPerformance(),
          analyticsService.getSubjectBreakdown(),
        ]);
        setDashboard(dashData);
        setQuizPerformance(quizData);
        setSubjects(subjectData);
      } catch (e) {
        console.error("Failed to load dashboard:", e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const cards = dashboard?.cards;
  const stats = dashboard?.stats;

  const weeklyData = quizPerformance.map((q) => ({
    day: new Date(q.date).toLocaleDateString("en-US", { weekday: "short" }),
    score: Math.round(q.avg_score),
  }));

  const radarData = subjects.map((s) => ({
    subject: s.subject_name,
    A: Math.round(s.avg_score),
  }));

  const today = new Date().toISOString().split("T")[0];
  const upcomingTasks = dashboard?.upcoming_tasks ?? [];
  const todayTasks = upcomingTasks.filter((t) => t.due_date === today);
  const otherTasks = upcomingTasks.filter((t) => t.due_date !== today);
  const displayTasks = [...todayTasks, ...otherTasks].slice(0, 4);

  if (loading) {
    return (
      <AppLayout title="Dashboard">
        <div className="max-w-7xl mx-auto flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Dashboard">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Upload Banner */}
        <div className="card p-4 bg-gradient-to-r from-slate-900 to-slate-800 text-white flex flex-wrap items-center justify-between gap-3 border-slate-700 shadow-md">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-400 flex items-center justify-center border border-primary-500/30">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <p className="font-bold text-sm">Upload New Course Syllabus</p>
              <p className="text-xs text-slate-400">PDF, DOCX, or Image - Mentora AI auto-generates your study plan & quiz</p>
            </div>
          </div>
          <Link to="/upload-syllabus" className="btn-primary btn-sm rounded-xl">
            <Upload className="w-3.5 h-3.5" /> Upload Now <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Welcome Banner */}
        <div className="card p-5 sm:p-6 bg-gradient-to-r from-primary-600 via-primary-500 to-secondary-500 text-white border-0 shadow-glow-primary">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-primary-100 text-sm font-medium">Good morning</p>
              <h2 className="text-xl sm:text-2xl font-bold mt-1">Welcome back, {firstName}!</h2>
              <p className="text-primary-100 mt-1 text-sm">
                {cards?.tasks_due_today ?? 0} tasks due today. Keep up the streak!
              </p>
            </div>
            <div className="hidden sm:flex flex-col items-end gap-1">
              <div className="flex items-center gap-2 bg-white/20 rounded-xl px-3 py-1.5">
                <Flame className="w-4 h-4 text-warning-400" />
                <span className="text-sm font-bold">{cards?.study_hours.week_change ?? 0}h this week</span>
              </div>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
            {quickActions.map((a) => (
              <Link
                key={a.path}
                to={a.path}
                className="flex flex-col items-center gap-2 bg-white/15 hover:bg-white/25 rounded-xl p-3 transition-all hover:scale-105"
              >
                <a.icon className="w-5 h-5" />
                <span className="text-xs font-semibold">{a.label}</span>
              </Link>
            ))}
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          {[
            {
              label: "Study Hours",
              value: `${cards?.study_hours.total ?? 0}h`,
              change: `+${cards?.study_hours.week_change ?? 0}h`,
              icon: Clock,
              color: "text-primary-600",
              bg: "bg-primary-50 dark:bg-primary-900/30",
            },
            {
              label: "Quiz Average",
              value: `${Math.round(cards?.quiz_average.value ?? 0)}%`,
              change: cards?.quiz_average.week_change != null ? `+${Math.round(cards.quiz_average.week_change)}%` : null,
              icon: Trophy,
              color: "text-success-600",
              bg: "bg-success-50 dark:bg-success-900/30",
            },
            {
              label: "Flashcards Done",
              value: `${cards?.flashcards_done.total ?? 0}`,
              change: `+${cards?.flashcards_done.week_change ?? 0}`,
              icon: CreditCard,
              color: "text-secondary-600",
              bg: "bg-secondary-50 dark:bg-secondary-900/30",
            },
            {
              label: "Topics Mastered",
              value: `${cards?.topics_mastered.mastered ?? 0}/${cards?.topics_mastered.total ?? 0}`,
              change: `+${cards?.topics_mastered.week_change ?? 0}`,
              icon: Target,
              color: "text-primary-600",
              bg: "bg-primary-50 dark:bg-primary-900/30",
            },
          ].map((s) => (
            <div key={s.label} className="stat-card">
              <div className={`w-10 h-10 rounded-xl ${s.bg} flex items-center justify-center`}>
                <s.icon className={`w-5 h-5 ${s.color}`} />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">{s.value}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{s.label}</p>
              </div>
              {s.change && (
                <span className="text-xs font-semibold text-success-600 bg-success-50 dark:bg-success-900/30 px-2 py-0.5 rounded-full">
                  {s.change} this week
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="card p-5 lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-slate-800 dark:text-slate-100">Weekly Quiz Performance</h3>
              {weeklyData.length > 0 && <span className="badge-blue">This week</span>}
            </div>
            {weeklyData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={weeklyData} barSize={32}>
                  <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#94a3b8" }} />
                  <YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#94a3b8" }} />
                  <Tooltip
                    contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 20px rgba(0,0,0,0.1)" }}
                    formatter={(v: any) => [`${v}%`, "Score"]}
                  />
                  <Bar dataKey="score" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-slate-400 text-center py-8">No quiz data yet. Take a quiz to see your performance!</p>
            )}
          </div>

          <div className="card p-5">
            <h3 className="font-bold text-slate-800 dark:text-slate-100 mb-4">Topic Mastery</h3>
            {radarData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10, fill: "#94a3b8" }} />
                  <Radar dataKey="A" fill="#8b5cf6" fillOpacity={0.25} stroke="#8b5cf6" strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-slate-400 text-center py-8">No subject data yet.</p>
            )}
          </div>
        </div>

        {/* Tasks */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-slate-800 dark:text-slate-100">Upcoming Tasks</h3>
            <Link to="/study-plan" className="text-sm text-primary-600 hover:text-primary-700 font-medium">
              View all
            </Link>
          </div>
          {displayTasks.length > 0 ? (
            <div className="space-y-2">
              {displayTasks.map((t) => {
                const isToday = t.due_date === today;
                return (
                  <div
                    key={t.id}
                    className="flex items-center gap-3 p-3 rounded-xl border bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-primary-200 transition-all"
                  >
                    <div className="w-5 h-5 rounded-full border-2 border-slate-300 dark:border-slate-500" />
                    <span className="flex-1 min-w-0 text-sm font-medium text-slate-700 dark:text-slate-200">{t.title}</span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        isToday
                          ? "bg-primary-50 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400"
                          : "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400"
                      }`}
                    >
                      {isToday ? "Today" : t.due_date ? new Date(t.due_date).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "No date"}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-slate-400 text-center py-4">No upcoming tasks. Create a study plan to get started!</p>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
