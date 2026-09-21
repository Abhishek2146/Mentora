import { useState, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { Brain, CreditCard, Trophy, Flame, Clock, Target, Upload, FileText, ArrowRight, Loader2, Sparkles, TrendingUp, CalendarCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, RadarChart, PolarGrid, PolarAngleAxis, Radar } from "recharts";
import { useAuthStore } from "@/store/authStore";
import { analyticsService, DashboardData, QuizPerformance, SubjectBreakdown } from "@/services/analyticsService";
import { cn } from "@/lib/utils";

const quickActions = [
  { label: "AI Tutor", desc: "Ask anything", icon: Brain, path: "/ai-tutor" },
  { label: "Flashcards", desc: "Review cards", icon: CreditCard, path: "/flashcards" },
  { label: "Daily Quiz", desc: "Test yourself", icon: Trophy, path: "/daily-quiz" },
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

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  const kpis = [
    {
      label: "Study Hours",
      value: `${cards?.study_hours.total ?? 0}h`,
      change: `+${cards?.study_hours.week_change ?? 0}h this week`,
      icon: Clock,
      iconBg: "bg-[#EBE5F6] dark:bg-[#6F4FB1]/20 text-[#6F4FB1] dark:text-[#EBE5F6] border-[#6F4FB1]/25",
      trendColor: "text-[#6F4FB1] dark:text-[#EBE5F6]",
    },
    {
      label: "Quiz Average",
      value: `${Math.round(cards?.quiz_average.value ?? 0)}%`,
      change: cards?.quiz_average.week_change != null ? `+${Math.round(cards.quiz_average.week_change)}% this week` : null,
      icon: Trophy,
      iconBg: "bg-[#EAF2EC] dark:bg-[#8FAF9A]/20 text-[#5D826A] dark:text-[#8FAF9A] border-[#8FAF9A]/25",
      trendColor: "text-[#5D826A] dark:text-[#8FAF9A]",
    },
    {
      label: "Flashcards Done",
      value: `${cards?.flashcards_done.total ?? 0}`,
      change: `+${cards?.flashcards_done.week_change ?? 0} this week`,
      icon: CreditCard,
      iconBg: "bg-[#F7F0E2] dark:bg-[#C49A5A]/20 text-[#876432] dark:text-[#C49A5A] border-[#C49A5A]/25",
      trendColor: "text-[#876432] dark:text-[#C49A5A]",
    },
    {
      label: "Topics Mastered",
      value: `${cards?.topics_mastered.mastered ?? 0}/${cards?.topics_mastered.total ?? 0}`,
      change: `+${cards?.topics_mastered.week_change ?? 0} this week`,
      icon: Target,
      iconBg: "bg-[#F8EAEA] dark:bg-[#C47F82]/20 text-[#8C4F52] dark:text-[#C47F82] border-[#C47F82]/25",
      trendColor: "text-[#8C4F52] dark:text-[#C47F82]",
    },
  ];

  return (
    <AppLayout title="Dashboard">
      <div className="max-w-7xl mx-auto space-y-5 sm:space-y-6">
        {/* Hero Banner */}
        <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#2D283E] via-[#3E3655] to-[#252033] text-white shadow-soft border border-[#6F4FB1]/30">
          <div className="absolute -top-20 -right-16 w-72 h-72 rounded-full bg-[#6F4FB1]/30 blur-3xl pointer-events-none animate-float" />
          <div className="absolute -bottom-24 left-1/3 w-64 h-64 rounded-full bg-[#B6A3DE]/15 blur-3xl pointer-events-none animate-float" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(182,163,222,0.14),transparent_55%)] pointer-events-none" />

          <div className="relative z-10 p-6 sm:p-8">
            <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
              <div className="space-y-2 max-w-2xl">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md border border-white/15 text-xs font-semibold text-[#EBE5F6]">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#B6A3DE] opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-[#B6A3DE]" />
                  </span>
                  <span>AI Study Assistant Ready</span>
                </div>
                <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight">
                  {getGreeting()},{" "}
                  <span className="bg-gradient-to-r from-[#EBE5F6] via-white to-[#B6A3DE] bg-clip-text text-transparent">{firstName}</span>!
                </h2>
                <p className="text-sm text-[#D6CBEC] leading-relaxed">
                  You have <span className="font-semibold text-white">{cards?.tasks_due_today ?? 0} tasks</span> scheduled for today. Ready to continue your learning journey?
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 lg:w-[340px] flex-shrink-0">
                <div className="rounded-2xl bg-white/10 backdrop-blur-xl border border-white/15 p-4 hover:bg-white/15 transition-colors">
                  <div className="flex items-center gap-2 text-[#D6CBEC]">
                    <Flame className="w-4 h-4 text-[#D1B47C]" />
                    <span className="text-xs font-medium">Study Time</span>
                  </div>
                  <p className="mt-1.5 text-xl font-extrabold text-white">{cards?.study_hours.week_change ?? 0}h</p>
                  <p className="text-[11px] text-[#B6A3DE]">this week</p>
                </div>
                <div className="rounded-2xl bg-white/10 backdrop-blur-xl border border-white/15 p-4 hover:bg-white/15 transition-colors">
                  <div className="flex items-center gap-2 text-[#D6CBEC]">
                    <CalendarCheck className="w-4 h-4 text-[#B6A3DE]" />
                    <span className="text-xs font-medium">Due Today</span>
                  </div>
                  <p className="mt-1.5 text-xl font-extrabold text-white">{cards?.tasks_due_today ?? 0}</p>
                  <p className="text-[11px] text-[#B6A3DE]">tasks</p>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
              {quickActions.map((a) => (
                <Link
                  key={a.path}
                  to={a.path}
                  className="group relative flex items-center gap-3 p-3.5 rounded-2xl bg-white/5 hover:bg-white/15 backdrop-blur-md border border-white/10 hover:border-white/25 transition-all duration-200 hover:-translate-y-0.5 overflow-hidden"
                >
                  <div className="w-10 h-10 rounded-xl bg-[#6F4FB1]/30 border border-white/15 flex items-center justify-center text-white group-hover:scale-110 transition-transform">
                    <a.icon className="w-[18px] h-[18px] text-[#EBE5F6] group-hover:text-white" />
                  </div>
                  <div className="text-left min-w-0 flex-1">
                    <p className="text-sm font-bold text-white">{a.label}</p>
                    <span className="text-[11px] text-[#D6CBEC]">{a.desc}</span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-[#D6CBEC] opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* Highlighted Animated Upload CTA */}
        <Link
          to="/upload-syllabus"
          className="group relative overflow-hidden rounded-3xl p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-5 text-white shadow-soft hover:shadow-glow-primary transition-shadow duration-300 bg-gradient-to-r from-[#6F4FB1] via-[#7C5AC2] to-[#4B2E83] bg-[length:200%_200%] animate-gradient-x border border-white/10"
        >
          <span className="pointer-events-none absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-white/25 to-transparent skew-x-[-20deg] animate-shimmer" />
          <div className="absolute -top-16 -right-10 w-64 h-64 rounded-full bg-white/10 blur-3xl pointer-events-none" />

          <div className="relative z-10 flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-white/15 border border-white/20 flex items-center justify-center flex-shrink-0 shadow-sm group-hover:animate-wiggle">
              <Upload className="w-7 h-7 text-white" />
            </div>
            <div className="min-w-0">
              <h3 className="text-lg sm:text-xl font-extrabold tracking-tight flex items-center gap-2">
                Upload your syllabus
                <Sparkles className="w-4 h-4 text-[#F7F0E2] animate-pulse" />
              </h3>
              <p className="text-sm text-[#EBE5F6] mt-0.5">
                Turn any PDF into AI notes, quizzes, flashcards and a personalized study plan.
              </p>
            </div>
          </div>

          <div className="relative z-10 inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white text-[#5D3F9C] text-sm font-bold flex-shrink-0 shadow-sm group-hover:gap-3 transition-all animate-glow-pulse">
            <span>Upload now</span>
            <ArrowRight className="w-4 h-4" />
          </div>
        </Link>

        {/* Stats KPI Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
          {kpis.map((s) => (
            <div
              key={s.label}
              className="card h-full p-5 hover:shadow-card-hover hover:-translate-y-1 transition-all duration-200 flex flex-col justify-between"
            >
              <div className="flex items-start justify-between gap-3">
                <span className="text-xs font-semibold text-[#6B6B6B] dark:text-[#A8A5A0] uppercase tracking-wider">{s.label}</span>
                <div className={`w-10 h-10 rounded-xl border flex items-center justify-center flex-shrink-0 ${s.iconBg}`}>
                  <s.icon className="w-[18px] h-[18px]" />
                </div>
              </div>
              <div className="mt-4">
                <p className="text-3xl font-extrabold text-[#252525] dark:text-[#F8F7F4] tracking-tight">{s.value}</p>
                {s.change ? (
                  <p className={`text-xs font-semibold mt-1.5 flex items-center gap-1 ${s.trendColor}`}>
                    <TrendingUp className="w-3.5 h-3.5" /> {s.change}
                  </p>
                ) : (
                  <p className="text-xs text-[#6B6B6B] dark:text-[#A8A5A0] mt-1.5">Steady pace</p>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 sm:gap-6 items-stretch">
          <div className="card p-5 lg:col-span-2 flex flex-col">
            <div className="flex items-center justify-between gap-3 mb-4">
              <div>
                <h3 className="font-bold text-sm sm:text-base text-[#252525] dark:text-[#F8F7F4]">Weekly Quiz Performance</h3>
                <p className="text-xs text-[#6B6B6B] dark:text-[#A8A5A0] mt-0.5">Average scores across quizzes taken this week</p>
              </div>
              {weeklyData.length > 0 && <span className="badge-lavender flex-shrink-0">This Week</span>}
            </div>

            {weeklyData.length > 0 ? (
              <div className="flex-1 min-h-[224px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={weeklyData} barSize={28}>
                    <defs>
                      <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#6F4FB1" stopOpacity={1} />
                        <stop offset="100%" stopColor="#9376C8" stopOpacity={0.7} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#6B6B6B" }} />
                    <YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#6B6B6B" }} />
                    <Tooltip
                      contentStyle={{
                        borderRadius: 14,
                        border: "1px solid #E7E5E0",
                        boxShadow: "0 10px 25px -5px rgba(124, 111, 159, 0.12)",
                        backgroundColor: "#FFFFFF",
                        fontSize: 12,
                        fontWeight: 600,
                        color: "#252525",
                      }}
                      formatter={(v: any) => [`${v}%`, "Score"]}
                    />
                    <Bar dataKey="score" fill="url(#barGrad)" radius={[6, 6, 2, 2]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex-1 min-h-[224px] flex flex-col items-center justify-center text-center text-[#6B6B6B] dark:text-[#A8A5A0]">
                <Trophy className="w-10 h-10 mx-auto text-[#E7E5E0] dark:text-[#383533] mb-2" />
                <p className="text-sm font-medium">No quiz activity recorded yet</p>
                <p className="text-xs mt-1">Take a quiz or practice MCQ to see your performance graph!</p>
              </div>
            )}
          </div>

          <div className="card p-5 flex flex-col">
            <div className="flex items-center justify-between gap-3 mb-4">
              <h3 className="font-bold text-sm sm:text-base text-[#252525] dark:text-[#F8F7F4]">Topic Mastery</h3>
              <span className="badge-lavender flex-shrink-0">Overview</span>
            </div>
            {radarData.length > 0 ? (
              <div className="flex-1 min-h-[224px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#E7E5E0" strokeDasharray="3 3" />
                    <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10, fill: "#6B6B6B" }} />
                    <Radar dataKey="A" fill="#6F4FB1" fillOpacity={0.25} stroke="#6F4FB1" strokeWidth={2} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex-1 min-h-[224px] flex flex-col items-center justify-center text-center text-[#6B6B6B] dark:text-[#A8A5A0]">
                <Target className="w-10 h-10 mx-auto text-[#E7E5E0] dark:text-[#383533] mb-2" />
                <p className="text-sm font-medium">No subject breakdown yet</p>
                <p className="text-xs mt-1">Upload a syllabus to map out your topics</p>
              </div>
            )}
          </div>
        </div>

        {/* Upcoming Tasks Section */}
        <div className="card p-5 sm:p-6">
          <div className="flex items-center justify-between gap-3 mb-4">
            <div>
              <h3 className="font-bold text-sm sm:text-base text-[#252525] dark:text-[#F8F7F4]">Upcoming Study Tasks</h3>
              <p className="text-xs text-[#6B6B6B] dark:text-[#A8A5A0] mt-0.5">Stay on track with your syllabus milestones</p>
            </div>
            <Link
              to="/study-plan"
              className="group inline-flex items-center gap-1.5 text-xs font-semibold text-[#6F4FB1] dark:text-[#EBE5F6] hover:text-[#5D3F9C] transition-colors flex-shrink-0"
            >
              <span>View Full Plan</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </Link>
          </div>

          {displayTasks.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {displayTasks.map((t) => {
                const isToday = t.due_date === today;
                return (
                  <div
                    key={t.id}
                    className={cn(
                      "flex items-center gap-3 p-3.5 rounded-2xl border transition-all duration-150",
                      isToday
                        ? "bg-[#EBE5F6]/40 dark:bg-[#6F4FB1]/15 border-[#6F4FB1]/35 dark:border-[#6F4FB1]/40"
                        : "bg-white dark:bg-[#222120] border-[#E7E5E0] dark:border-[#383533] hover:border-[#6F4FB1]/40"
                    )}
                  >
                    <div className={cn(
                      "w-4 h-4 rounded-full border-2 flex-shrink-0 flex items-center justify-center",
                      isToday ? "border-[#6F4FB1] bg-[#6F4FB1]/20" : "border-[#E7E5E0] dark:border-[#383533]"
                    )} />
                    <span className="flex-1 min-w-0 text-xs sm:text-sm font-medium text-[#252525] dark:text-[#F8F7F4] truncate">
                      {t.title}
                    </span>
                    <span
                      className={cn(
                        "text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full font-semibold flex-shrink-0",
                        isToday
                          ? "bg-[#EBE5F6] dark:bg-[#6F4FB1]/25 text-[#6F4FB1] dark:text-[#EBE5F6] border border-[#6F4FB1]/30"
                          : "bg-[#F8F7F4] dark:bg-[#383533] text-[#6B6B6B] dark:text-[#A8A5A0]"
                      )}
                    >
                      {isToday ? "Due Today" : t.due_date ? new Date(t.due_date).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "Upcoming"}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="py-8 text-center text-[#6B6B6B] dark:text-[#A8A5A0]">
              <FileText className="w-10 h-10 mx-auto text-[#E7E5E0] dark:text-[#383533] mb-2" />
              <p className="text-sm font-medium">All caught up on tasks!</p>
              <p className="text-xs mt-1">Create a study plan or upload a new syllabus to generate daily goals.</p>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
