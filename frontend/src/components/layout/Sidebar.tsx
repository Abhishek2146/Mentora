import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Brain, CreditCard, CalendarDays, BarChart3,
  ClipboardList, BookOpen, Trophy, AlertTriangle, RotateCcw,
  Upload, Code2, Mic, User, Settings, ChevronLeft, ChevronRight, X,
  TrendingUp, ShieldCheck, Users, Crown, Flame, FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/store/uiStore";
import { useAuthStore } from "@/store/authStore";
import { getInitials } from "@/lib/utils";
import logo from "@/assets/logo.png";

const navGroups = [
  {
    label: "Main",
    items: [
      { label: "Dashboard",       icon: LayoutDashboard, path: "/dashboard" },
      { label: "AI Tutor",        icon: Brain,           path: "/ai-tutor" },
      { label: "AI Detection",    icon: ShieldCheck,     path: "/ai-detection" },
      { label: "Flashcards",      icon: CreditCard,      path: "/flashcards" },
      { label: "Study Plan",      icon: CalendarDays,    path: "/study-plan" },
      { label: "Notes",           icon: FileText,        path: "/notes" },
      { label: "Analytics",       icon: BarChart3,       path: "/analytics" },
      { label: "Study Groups",    icon: Users,           path: "/study-groups" },
      { label: "Study Streak",    icon: Flame,           path: "/study-streak" },
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
    ],
  },
    {
      label: "Setup",
      items: [
        { label: "Upload Syllabus", icon: Upload,          path: "/upload-syllabus" },
        { label: "Subscription",    icon: Crown,           path: "/subscription" },
        { label: "Profile",         icon: User,            path: "/profile" },
        { label: "Settings",        icon: Settings,        path: "/settings" },
      ],
    },
];

export default function Sidebar() {
  const { sidebarOpen, setSidebarOpen, mobileNavOpen, setMobileNavOpen } = useUIStore();
  const { user } = useAuthStore();
  const { pathname } = useLocation();
  const userName = user?.full_name || user?.username || "Student";
  const isAdmin = user?.role === "admin" || user?.role === "super_admin";

  const groups = [
    ...(isAdmin
      ? [{
          label: "Admin",
          items: [
            { label: "Admin Dashboard", icon: ShieldCheck, path: "/admin/dashboard" },
            { label: "User Management", icon: Users, path: "/admin/dashboard" },
          ],
        }]
      : []),
    ...navGroups,
  ];

  const handleNavClick = () => setMobileNavOpen(false);

  return (
    <>
      {/* Mobile backdrop */}
      <div
        onClick={() => setMobileNavOpen(false)}
        className={cn(
          "fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-sm transition-opacity duration-300 lg:hidden",
          mobileNavOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        aria-hidden="true"
      />

      <aside
        className={cn(
          "fixed top-0 left-0 h-full z-50 flex flex-col transition-all duration-300 ease-in-out w-64 overflow-hidden",
          "bg-white dark:bg-[#222120] border-r border-[#E7E5E0] dark:border-[#383533]",
          // Mobile: off-canvas drawer that slides in.
          mobileNavOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full",
          // Desktop: persistent rail based on collapse state.
          "lg:translate-x-0 lg:shadow-none",
          sidebarOpen ? "lg:w-64" : "lg:w-16"
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-[#E7E5E0] dark:border-[#383533]">
          <Link to="/dashboard" onClick={handleNavClick} className="flex items-center gap-3 min-w-0 group">
            <div className="w-9 h-9 rounded-xl bg-white dark:bg-[#222120] flex items-center justify-center shadow-sm flex-shrink-0 overflow-hidden group-hover:scale-105 transition-transform duration-200">
              <img src={logo} alt="Mentora logo" className="w-8 h-8 object-contain" />
            </div>
            <div className={cn("min-w-0 transition-opacity duration-200", !sidebarOpen && "lg:hidden")}>
              <span className="font-bold text-lg tracking-tight text-[#252525] dark:text-[#F8F7F4] block">
                Mentora
              </span>
              <span className="text-[10px] font-medium tracking-wider text-[#6B6B6B] block -mt-1 uppercase">
                AI Learning
              </span>
            </div>
          </Link>
          <button
            onClick={() => setMobileNavOpen(false)}
            className="p-1.5 rounded-lg text-[#6B6B6B] hover:text-[#252525] hover:bg-[#EBE5F6]/40 dark:hover:bg-[#383533] transition-all lg:hidden"
            aria-label="Close menu"
          >
            <X className="w-4 h-4" />
          </button>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className={cn(
              "hidden lg:flex items-center justify-center w-7 h-7 rounded-lg text-[#6B6B6B] hover:text-[#252525] dark:hover:text-[#F8F7F4] hover:bg-[#EBE5F6]/40 dark:hover:bg-[#383533] transition-all",
              !sidebarOpen && "absolute -right-3 top-5 bg-white dark:bg-[#222120] border border-[#E7E5E0] dark:border-[#383533] shadow-sm rounded-full z-10"
            )}
            aria-label="Toggle sidebar"
          >
            {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-2.5 space-y-4 no-scrollbar">
          {groups.map((group) => (
            <div key={group.label}>
              <p className={cn(
                "text-[10px] font-bold uppercase tracking-wider text-[#6B6B6B]/80 dark:text-[#A8A5A0] px-3 mb-1 truncate whitespace-nowrap select-none",
                !sidebarOpen && "lg:opacity-0 lg:pointer-events-none"
              )}>
                {group.label}
              </p>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const isActive = pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      onClick={handleNavClick}
                      title={!sidebarOpen ? item.label : undefined}
                      className={cn(
                        "sidebar-item relative group",
                        isActive && "active",
                        !sidebarOpen && "lg:justify-center lg:px-2"
                      )}
                    >
                      {isActive && (
                        <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-[#6F4FB1]" />
                      )}
                      <item.icon
                        className={cn(
                          "w-4 h-4 flex-shrink-0 transition-colors duration-150",
                          isActive
                            ? "text-[#6F4FB1]"
                            : "text-[#6B6B6B] dark:text-[#A8A5A0] group-hover:text-[#252525] dark:group-hover:text-[#F8F7F4]"
                        )}
                      />
                      <span className={cn("truncate font-medium text-xs sm:text-sm", !sidebarOpen && "lg:hidden")}>
                        {item.label}
                      </span>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* User Card */}
        <div className="border-t border-[#E7E5E0] dark:border-[#383533] p-2.5 bg-[#F8F7F4]/60 dark:bg-[#1A1918]/60">
          <Link
            to="/profile"
            onClick={handleNavClick}
            className={cn(
              "flex items-center gap-3 rounded-xl p-2 hover:bg-white dark:hover:bg-[#222120] border border-transparent hover:border-[#E7E5E0] dark:hover:border-[#383533] transition-all duration-150",
              !sidebarOpen && "lg:justify-center lg:p-1.5"
            )}
          >
            <div className="w-8 h-8 rounded-lg bg-[#6F4FB1] flex items-center justify-center text-white text-xs font-bold shadow-sm flex-shrink-0">
              {user?.full_name ? getInitials(user.full_name) : user?.username?.[0]?.toUpperCase() ?? "U"}
            </div>
            <div className={cn("leading-tight min-w-0 flex-1", !sidebarOpen && "lg:hidden")}>
              <div className="flex items-center justify-between gap-1">
                <p className="text-xs font-semibold text-[#252525] dark:text-[#F8F7F4] truncate">{userName}</p>
                <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-[#EBE5F6] text-[#6F4FB1] border border-[#6F4FB1]/20 uppercase tracking-wider">
                  {user?.role === "admin" ? "ADMIN" : "PRO"}
                </span>
              </div>
              <p className="text-[11px] text-[#6B6B6B] truncate mt-0.5">{user?.email || "student"}</p>
            </div>
          </Link>
        </div>

        {/* Footer */}
        <div className={cn("hidden lg:block p-3 border-t border-[#E7E5E0] dark:border-[#383533]", !sidebarOpen && "lg:hidden")}>
          <div className="text-[10px] text-[#6B6B6B] text-center">Mentora v1.0</div>
        </div>
      </aside>
    </>
  );
}
