import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Brain, CreditCard, CalendarDays, BarChart3,
  ClipboardList, BookOpen, Trophy, AlertTriangle, RotateCcw,
  Upload, Code2, Mic, User, Settings, ChevronLeft, ChevronRight,
  GraduationCap, TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/store/uiStore";

const navGroups = [
  {
    label: "Main",
    items: [
      { label: "Dashboard",       icon: LayoutDashboard, path: "/dashboard" },
      { label: "AI Tutor",        icon: Brain,           path: "/ai-tutor" },
      { label: "Flashcards",      icon: CreditCard,      path: "/flashcards" },
      { label: "Study Plan",      icon: CalendarDays,    path: "/study-plan" },
      { label: "Analytics",       icon: BarChart3,       path: "/analytics" },
    ],
  },
  {
    label: "Practice",
    items: [
      { label: "Daily Quiz",      icon: ClipboardList,   path: "/daily-quiz" },
      { label: "MCQ Practice",    icon: BookOpen,        path: "/mcq" },
      { label: "Exam Simulator",  icon: Trophy,          path: "/exam-simulator" },
      { label: "Coding Practice", icon: Code2,           path: "/coding-practice" },
    ],
  },
  {
    label: "Improve",
    items: [
      { label: "Weak Topics",     icon: AlertTriangle,   path: "/weak-topics" },
      { label: "Revision Plan",   icon: RotateCcw,       path: "/revision-plan" },
      { label: "Progress",        icon: TrendingUp,      path: "/progress" },
      { label: "Voice Learning",  icon: Mic,             path: "/voice-learning" },
    ],
  },
  {
    label: "Setup",
    items: [
      { label: "Upload Syllabus", icon: Upload,          path: "/upload-syllabus" },
      { label: "Profile",         icon: User,            path: "/profile" },
      { label: "Settings",        icon: Settings,        path: "/settings" },
    ],
  },
];

export default function Sidebar() {
  const { sidebarOpen, setSidebarOpen } = useUIStore();
  const { pathname } = useLocation();

  return (
    <aside
      className={cn(
        "fixed top-0 left-0 h-full z-30 flex flex-col transition-all duration-300 ease-in-out",
        "bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-700/50",
        sidebarOpen ? "w-64" : "w-16"
      )}
    >
      {/* Logo */}
      <div className="flex items-center justify-between px-4 py-5 border-b border-slate-100 dark:border-slate-700/50">
        {sidebarOpen && (
          <Link to="/dashboard" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center shadow-glow-primary">
              <GraduationCap className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
              Mentora
            </span>
          </Link>
        )}
        {!sidebarOpen && (
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center mx-auto">
            <GraduationCap className="w-5 h-5 text-white" />
          </div>
        )}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className={cn(
            "p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition-all",
            !sidebarOpen && "absolute -right-3 top-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 shadow-sm rounded-full"
          )}
          aria-label="Toggle sidebar"
        >
          {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 no-scrollbar">
        {navGroups.map((group) => (
          <div key={group.label} className="mb-4">
            {sidebarOpen && (
              <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500 px-3 mb-1.5">
                {group.label}
              </p>
            )}
            {group.items.map((item) => {
              const isActive = pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  title={!sidebarOpen ? item.label : undefined}
                  className={cn(
                    "sidebar-item mb-0.5",
                    isActive && "active",
                    !sidebarOpen && "justify-center px-2"
                  )}
                >
                  <item.icon className={cn("w-4.5 h-4.5 flex-shrink-0", isActive ? "text-primary-600 dark:text-primary-400" : "")} style={{ width: 18, height: 18 }} />
                  {sidebarOpen && <span className="truncate">{item.label}</span>}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      {sidebarOpen && (
        <div className="p-4 border-t border-slate-100 dark:border-slate-700/50">
          <div className="text-[10px] text-slate-400 text-center">Mentora v1.0</div>
        </div>
      )}
    </aside>
  );
}
