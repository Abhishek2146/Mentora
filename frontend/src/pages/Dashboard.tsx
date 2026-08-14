import AppLayout from "@/components/layout/AppLayout";
import { Brain, CreditCard, Trophy, Flame, Clock, Target, Calendar, Star, Upload, FileText, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, RadarChart, PolarGrid, PolarAngleAxis, Radar } from "recharts";

const weeklyData = [
  { day: "Mon", score: 72 }, { day: "Tue", score: 85 }, { day: "Wed", score: 68 },
  { day: "Thu", score: 91 }, { day: "Fri", score: 78 }, { day: "Sat", score: 88 }, { day: "Sun", score: 82 },
];

const radarData = [
  { subject: "SQL", A: 88 }, { subject: "Normalization", A: 75 }, { subject: "ER Diagrams", A: 90 },
  { subject: "Transactions", A: 42 }, { subject: "Indexing", A: 55 }, { subject: "Rel. Algebra", A: 61 },
];

const tasks = [
  { id: 1, title: "Complete SQL Joins chapter", due: "Today", done: false, type: "study" },
  { id: 2, title: "Flashcard review – Normalization", due: "Today", done: true, type: "review" },
  { id: 3, title: "Practice 10 MCQs on ACID", due: "Tomorrow", done: false, type: "quiz" },
  { id: 4, title: "Upload DBMS Syllabus PDF", due: "Tomorrow", done: false, type: "upload" },
];

const quickActions = [
  { label: "Upload Syllabus", icon: Upload, path: "/upload-syllabus" },
  { label: "AI Tutor", icon: Brain, path: "/ai-tutor" },
  { label: "Flashcards", icon: CreditCard, path: "/flashcards" },
  { label: "Daily Quiz", icon: Trophy, path: "/daily-quiz" },
];

export default function Dashboard() {
  return (
    <AppLayout title="Dashboard">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Top Syllabus Upload Banner */}
        <div className="card p-4 bg-gradient-to-r from-slate-900 to-slate-800 text-white flex items-center justify-between border-slate-700 shadow-md">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-400 flex items-center justify-center border border-primary-500/30">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <p className="font-bold text-sm">Upload New Course Syllabus</p>
              <p className="text-xs text-slate-400">PDF, DOCX, or Image • Mentora AI auto-generates your study plan & quiz</p>
            </div>
          </div>
          <Link to="/upload-syllabus" className="btn-primary btn-sm rounded-xl">
            <Upload className="w-3.5 h-3.5" /> Upload Now <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
        {/* Welcome Banner */}
        <div className="card p-6 bg-gradient-to-r from-primary-600 via-primary-500 to-secondary-500 text-white border-0 shadow-glow-primary">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-primary-100 text-sm font-medium">Good morning 👋</p>
              <h2 className="text-2xl font-bold mt-1">Welcome back, Dipeesh!</h2>
              <p className="text-primary-100 mt-1 text-sm">You have 3 tasks due today. Keep up the streak! 🔥</p>
            </div>
            <div className="hidden sm:flex flex-col items-end gap-1">
              <div className="flex items-center gap-2 bg-white/20 rounded-xl px-3 py-1.5">
                <Flame className="w-4 h-4 text-orange-300" />
                <span className="text-sm font-bold">12 day streak</span>
              </div>
              <div className="flex items-center gap-2 bg-white/20 rounded-xl px-3 py-1.5">
                <Star className="w-4 h-4 text-yellow-300" />
                <span className="text-sm font-bold">Top 15%</span>
              </div>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-4 gap-3">
            {quickActions.map((a) => (
              <Link key={a.path} to={a.path}
                className="flex flex-col items-center gap-2 bg-white/15 hover:bg-white/25 rounded-xl p-3 transition-all hover:scale-105">
                <a.icon className="w-5 h-5" />
                <span className="text-xs font-semibold">{a.label}</span>
              </Link>
            ))}
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: "Study Hours", value: "47.5h", change: "+2.5h", icon: Clock, color: "text-primary-600", bg: "bg-primary-50 dark:bg-primary-900/30" },
            { label: "Quiz Average", value: "78%", change: "+5%", icon: Trophy, color: "text-emerald-600", bg: "bg-emerald-50 dark:bg-emerald-900/30" },
            { label: "Flashcards Done", value: "124", change: "+18", icon: CreditCard, color: "text-secondary-600", bg: "bg-secondary-50 dark:bg-secondary-900/30" },
            { label: "Topics Mastered", value: "9/18", change: "+1", icon: Target, color: "text-orange-600", bg: "bg-orange-50 dark:bg-orange-900/30" },
          ].map((s) => (
            <div key={s.label} className="stat-card">
              <div className={`w-10 h-10 rounded-xl ${s.bg} flex items-center justify-center`}>
                <s.icon className={`w-5 h-5 ${s.color}`} />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">{s.value}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{s.label}</p>
              </div>
              <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 dark:bg-emerald-900/30 px-2 py-0.5 rounded-full">{s.change} this week</span>
            </div>
          ))}
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="card p-5 lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-slate-800 dark:text-slate-100">Weekly Quiz Performance</h3>
              <span className="badge-blue">This week</span>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={weeklyData} barSize={32}>
                <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }}
                  formatter={(v: any) => [`${v}%`, 'Score']}
                />
                <Bar dataKey="score" fill="#0ea5e9" radius={[6,6,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card p-5">
            <h3 className="font-bold text-slate-800 dark:text-slate-100 mb-4">Topic Mastery</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <Radar dataKey="A" fill="#8b5cf6" fillOpacity={0.25} stroke="#8b5cf6" strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Tasks */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-slate-800 dark:text-slate-100">Today's Tasks</h3>
            <Link to="/study-plan" className="text-sm text-primary-600 hover:text-primary-700 font-medium">View all →</Link>
          </div>
          <div className="space-y-2">
            {tasks.map((t) => (
              <div key={t.id} className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
                t.done ? "bg-slate-50 dark:bg-slate-800/50 border-slate-100 dark:border-slate-700 opacity-60" : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-primary-200"
              }`}>
                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                  t.done ? "bg-emerald-500 border-emerald-500" : "border-slate-300 dark:border-slate-500"
                }`}>
                  {t.done && <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                </div>
                <span className={`flex-1 text-sm font-medium ${t.done ? "line-through text-slate-400" : "text-slate-700 dark:text-slate-200"}`}>{t.title}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  t.due === "Today" ? "bg-primary-50 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400" : "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400"
                }`}>{t.due}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
