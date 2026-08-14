import { Link } from "react-router-dom";
import { Bell, Search, Sun, Moon, Menu, Upload } from "lucide-react";
import { useUIStore } from "@/store/uiStore";
import { useAuthStore } from "@/store/authStore";
import { getInitials } from "@/lib/utils";
import { useState } from "react";

export default function Header({ title }: { title?: string }) {
  const { setSidebarOpen, sidebarOpen } = useUIStore();
  const { user } = useAuthStore();
  const [dark, setDark] = useState(document.documentElement.classList.contains("dark"));

  const toggleDark = () => {
    document.documentElement.classList.toggle("dark");
    setDark(!dark);
  };

  return (
    <header className="sticky top-0 z-20 h-16 flex items-center gap-4 px-6 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border-b border-slate-200/80 dark:border-slate-700/50">
      {/* Mobile menu toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="lg:hidden p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
      >
        <Menu className="w-5 h-5 text-slate-600 dark:text-slate-400" />
      </button>

      {/* Page title */}
      {title && (
        <h1 className="text-lg font-bold text-slate-800 dark:text-slate-100 hidden sm:block">
          {title}
        </h1>
      )}

      <div className="flex-1" />

      <div className="flex items-center gap-2">
        {/* Upload Syllabus top button */}
        <Link
          to="/upload-syllabus"
          id="header-upload-syllabus-btn"
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-gradient-to-r from-primary-500 to-secondary-500 text-white text-xs font-semibold shadow-md hover:shadow-lg hover:scale-105 transition-all"
        >
          <Upload className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Upload Syllabus</span>
        </Link>

        {/* Search */}
        <button
          id="header-search-btn"
          className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all text-sm"
        >
          <Search className="w-4 h-4" />
          <span className="hidden md:inline">Search…</span>
          <kbd className="hidden md:inline text-xs bg-white dark:bg-slate-600 px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-500">⌘K</kbd>
        </button>

        {/* Dark mode toggle */}
        <button
          onClick={toggleDark}
          id="dark-mode-toggle"
          className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          aria-label="Toggle dark mode"
        >
          {dark ? (
            <Sun className="w-5 h-5 text-amber-400" />
          ) : (
            <Moon className="w-5 h-5 text-slate-500" />
          )}
        </button>

        {/* Notifications */}
        <button
          id="notifications-btn"
          className="relative p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          aria-label="Notifications"
        >
          <Bell className="w-5 h-5 text-slate-500 dark:text-slate-400" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-danger-500 rounded-full ring-2 ring-white dark:ring-slate-900" />
        </button>

        {/* Avatar */}
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white text-sm font-bold shadow-md cursor-pointer hover:scale-105 transition-transform">
          {user?.full_name ? getInitials(user.full_name) : user?.username?.[0]?.toUpperCase() ?? "U"}
        </div>
      </div>
    </header>
  );
}
