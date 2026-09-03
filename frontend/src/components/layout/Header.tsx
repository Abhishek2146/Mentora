import { Link, useNavigate } from "react-router-dom";
import { Bell, Search, Sun, Moon, Menu, Upload, LogOut, User, ChevronDown, Loader2, FileText, ArrowRight, Check, Archive, X, AlertTriangle, Trophy, Info, Cpu } from "lucide-react";
import { useUIStore } from "@/store/uiStore";
import { useAuthStore } from "@/store/authStore";
import { cn, getInitials, formatDate } from "@/lib/utils";
import { useState, useEffect, useRef, useCallback } from "react";
import { syllabusService } from "@/services/syllabusService";
import { notificationService } from "@/services/notificationService";
import type { SyllabusSearchResult, Notification } from "@/types/api";

export default function Header({ title }: { title?: string }) {
  const { setMobileNavOpen } = useUIStore();
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [dark, setDark] = useState(document.documentElement.classList.contains("dark"));
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SyllabusSearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [notificationLoading, setNotificationLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);
  const notificationContainerRef = useRef<HTMLDivElement>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout>();

  const fetchNotifications = useCallback(async () => {
    if (!user) return;
    setNotificationLoading(true);
    try {
      const response = await notificationService.getNotifications({ page: 1, per_page: 10 });
      setNotifications(response.items);
      setUnreadCount(response.unread_count);
    } catch (e) {
      console.error("Failed to fetch notifications:", e);
    } finally {
      setNotificationLoading(false);
    }
  }, [user]);

  const fetchUnreadCount = useCallback(async () => {
    if (!user) return;
    try {
      const response = await notificationService.getUnreadCount();
      setUnreadCount(response.unread_count);
    } catch (e) {
      console.error("Failed to fetch unread count:", e);
    }
  }, [user]);

  useEffect(() => {
    fetchNotifications();
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications, fetchUnreadCount]);

  const toggleDark = () => {
    document.documentElement.classList.toggle("dark");
    setDark(!dark);
  };

  const performSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }

    setSearchLoading(true);
    setSearchError(null);

    try {
      const response = await syllabusService.searchSyllabi({
        q: query,
        search_in: ["title", "description", "subjects", "chapters", "topics"],
        page: 1,
        per_page: 5,
      });
      setSearchResults(response.items);
    } catch (e: any) {
      setSearchError(e?.response?.data?.detail || "Search failed");
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  }, []);

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => {
      performSearch(value);
    }, 250);
  };

  const handleSearchSelect = (syllabus: SyllabusSearchResult) => {
    setSearchOpen(false);
    setSearchQuery("");
    setSearchResults([]);
    navigate(`/syllabus/${syllabus.id}`);
  };

  const handleGoToFullSearch = () => {
    setSearchOpen(false);
    navigate(`/search?q=${encodeURIComponent(searchQuery)}`);
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Escape") {
      setSearchOpen(false);
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      setSearchOpen(true);
      setTimeout(() => searchInputRef.current?.focus(), 0);
    }
  };

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (searchOpen) {
      setTimeout(() => searchInputRef.current?.focus(), 0);
    }
  }, [searchOpen]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target as Node)) {
        setSearchOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [searchOpen]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (notificationContainerRef.current && !notificationContainerRef.current.contains(event.target as Node)) {
        setNotificationOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [notificationOpen]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "parsed": return "bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400";
      case "processing": return "bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400";
      case "failed": return "bg-danger-100 text-danger-700 dark:bg-danger-900/30 dark:text-danger-400";
      default: return "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300";
    }
  };

  return (
    <>
      <header className="sticky top-0 z-20 h-16 flex items-center gap-2 sm:gap-4 px-4 sm:px-6 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border-b border-slate-200/80 dark:border-slate-700/50">
        {/* Mobile menu toggle */}
        <button
          onClick={() => setMobileNavOpen(true)}
          className="lg:hidden p-2 -ml-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          aria-label="Open menu"
        >
          <Menu className="w-5 h-5 text-slate-600 dark:text-slate-400" />
        </button>

        {/* Page title */}
        {title && (
          <h1 className="text-base sm:text-lg font-bold text-slate-800 dark:text-slate-100 truncate hidden sm:block">
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

          {/* Search Dropdown */}
          <div className="relative" ref={searchContainerRef}>
            <button
              onClick={() => setSearchOpen(!searchOpen)}
              id="header-search-btn"
              className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all text-sm"
              aria-label="Search syllabi"
              aria-expanded={searchOpen}
            >
              <Search className="w-4 h-4" />
              <span className="hidden md:inline">Search…</span>
              <kbd className="hidden md:inline text-xs bg-white dark:bg-slate-600 px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-500">⌘K</kbd>
            </button>

            {searchOpen && (
              <div className="absolute left-2 right-2 sm:left-auto sm:right-0 top-full mt-2 sm:w-96 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl overflow-hidden animate-in slide-in-from-top-2 duration-150">
                {/* Search Input */}
                <div className="p-3 border-b border-slate-200 dark:border-slate-700">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input
                      ref={searchInputRef}
                      type="text"
                      value={searchQuery}
                      onChange={(e) => handleSearchChange(e.target.value)}
                      placeholder="Search syllabi..."
                      className="w-full pl-10 pr-10 py-2.5 text-sm bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      autoFocus
                    />
                    {searchQuery && (
                      <button
                        onClick={() => {
                          setSearchQuery("");
                          setSearchResults([]);
                          searchInputRef.current?.focus();
                        }}
                        className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                        aria-label="Clear search"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                      </button>
                    )}
                  </div>
                </div>

                {/* Results */}
                <div className="max-h-96 overflow-y-auto">
                  {searchLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
                      <span className="ml-2 text-sm text-slate-500 dark:text-slate-400">Searching…</span>
                    </div>
                  ) : searchError ? (
                    <div className="p-4 text-center text-danger-500 text-sm">{searchError}</div>
                  ) : searchResults.length === 0 && searchQuery ? (
                    <div className="p-8 text-center">
                      <FileText className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
                      <p className="text-sm text-slate-500 dark:text-slate-400">No results for "{searchQuery}"</p>
                    </div>
                  ) : searchResults.length === 0 && !searchQuery ? (
                    <div className="p-8 text-center">
                      <FileText className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
                      <p className="text-sm text-slate-500 dark:text-slate-400">Start typing to search your syllabi</p>
                      <p className="text-xs text-slate-400 mt-1">Searches titles, subjects, chapters, topics, and full text</p>
                    </div>
                  ) : (
                    <div className="divide-y divide-slate-200 dark:divide-slate-700">
                      {searchResults.map((result) => (
                        <button
                          key={result.id}
                          onClick={() => handleSearchSelect(result)}
                          className="w-full p-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors text-left"
                        >
                          <div className="flex items-start gap-3">
                            <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
                              <FileText className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <h4 className="font-medium text-slate-800 dark:text-slate-100 truncate text-sm">
                                  {result.title}
                                </h4>
                                <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded-full ${getStatusColor(result.status)}`}>
                                  {result.status}
                                </span>
                              </div>
                              {result.matched_fields && result.matched_fields.length > 0 && (
                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 truncate">
                                  Matched: {result.matched_fields.map(f => f.charAt(0).toUpperCase() + f.slice(1)).join(", ")}
                                </p>
                              )}
                            </div>
                            <ArrowRight className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
                          </div>
                        </button>
                      ))}

                      {/* View All Results */}
                      <button
                        onClick={handleGoToFullSearch}
                        className="w-full p-3 text-center text-sm font-medium text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors border-t border-slate-200 dark:border-slate-700"
                      >
                        View all results <ArrowRight className="w-4 h-4 inline ml-1" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Dark mode toggle */}
          <button
            onClick={toggleDark}
            id="dark-mode-toggle"
            className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            aria-label="Toggle dark mode"
          >
            {dark ? (
              <Sun className="w-5 h-5 text-warning-500" />
            ) : (
              <Moon className="w-5 h-5 text-slate-500" />
            )}
          </button>

          {/* Notifications */}
          <div className="relative" ref={notificationContainerRef}>
            <button
              onClick={() => setNotificationOpen(!notificationOpen)}
              id="notifications-btn"
              className="relative p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              aria-label="Notifications"
              aria-expanded={notificationOpen}
            >
              <Bell className="w-5 h-5 text-slate-500 dark:text-slate-400" />
              {unreadCount > 0 && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-danger-500 rounded-full ring-2 ring-white dark:ring-slate-900" />
              )}
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-danger-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </button>

            {notificationOpen && (
              <div className="absolute right-0 top-full mt-2 w-96 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl overflow-hidden animate-in slide-in-from-top-2 duration-150">
                {/* Header */}
                <div className="p-3 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
                  <h3 className="font-semibold text-slate-800 dark:text-slate-100">Notifications</h3>
                  <div className="flex items-center gap-2">
                    {unreadCount > 0 && (
                      <button
                        onClick={async () => {
                          await notificationService.markAllAsRead();
                          fetchNotifications();
                          fetchUnreadCount();
                        }}
                        className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
                      >
                        Mark all read
                      </button>
                    )}
                    <Link
                      to="/notifications"
                      onClick={() => setNotificationOpen(false)}
                      className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
                    >
                      View all
                    </Link>
                  </div>
                </div>

                {/* List */}
                <div className="max-h-96 overflow-y-auto">
                  {notificationLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
                      <span className="ml-2 text-sm text-slate-500 dark:text-slate-400">Loading…</span>
                    </div>
                  ) : notifications.length === 0 ? (
                    <div className="p-8 text-center">
                      <Bell className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
                      <p className="text-sm text-slate-500 dark:text-slate-400">No notifications yet</p>
                    </div>
                  ) : (
                    <div className="divide-y divide-slate-200 dark:divide-slate-700">
                      {notifications.map((notification) => (
                        <button
                          key={notification.id}
                          onClick={async () => {
                            if (!notification.is_read) {
                              await notificationService.markAsRead(notification.id);
                              fetchNotifications();
                              fetchUnreadCount();
                            }
                            // Navigate based on related entity
                            if (notification.related_entity_type && notification.related_entity_id) {
                              if (notification.related_entity_type === "syllabus") {
                                navigate(`/syllabus/${notification.related_entity_id}`);
                              }
                            }
                            setNotificationOpen(false);
                          }}
                          className={`w-full p-3 text-left transition-colors ${
                            notification.is_read
                              ? "hover:bg-slate-50 dark:hover:bg-slate-700/50"
                              : "bg-primary-50/50 dark:bg-primary-900/20 hover:bg-primary-50 dark:hover:bg-primary-900/30"
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                              notification.type === "success" ? "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400" :
                              notification.type === "warning" ? "bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400" :
                              notification.type === "error" ? "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400" :
                              notification.type === "achievement" ? "bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400" :
                              notification.type === "reminder" ? "bg-sky-100 dark:bg-sky-900/30 text-sky-600 dark:text-sky-400" :
                              "bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400"
                            }`}>
                              {notification.type === "success" && <Check className="w-4 h-4" />}
                              {notification.type === "warning" && <AlertTriangle className="w-4 h-4" />}
                              {notification.type === "error" && <X className="w-4 h-4" />}
                              {notification.type === "achievement" && <Trophy className="w-4 h-4" />}
                              {notification.type === "reminder" && <Bell className="w-4 h-4" />}
                              {notification.type === "info" && <Info className="w-4 h-4" />}
                              {notification.type === "system" && <Cpu className="w-4 h-4" />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <h4 className="font-medium text-slate-800 dark:text-slate-100 truncate text-sm">
                                  {notification.title}
                                </h4>
                                {!notification.is_read && (
                                  <span className="w-1.5 h-1.5 bg-primary-500 rounded-full flex-shrink-0" />
                                )}
                              </div>
                              <p className="text-sm text-slate-600 dark:text-slate-300 mt-0.5 line-clamp-2">
                                {notification.message}
                              </p>
                              <p className="text-xs text-slate-400 mt-1">
                                {formatDate(notification.created_at)}
                              </p>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* User dropdown */}
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-2 px-2 py-1.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              aria-haspopup="menu"
              aria-expanded={userMenuOpen}
            >
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white text-sm font-bold shadow-md flex-shrink-0">
                {user?.full_name ? getInitials(user.full_name) : user?.username?.[0]?.toUpperCase() ?? "U"}
              </div>
              <div className="hidden md:block text-left leading-tight">
                <p className="text-sm font-bold text-slate-800 dark:text-slate-100 truncate max-w-[120px]">
                  {user?.full_name || user?.username || "Student"}
                </p>
                <p className="text-[11px] text-slate-400 capitalize">{user?.role || "student"}</p>
              </div>
              <ChevronDown
                className={cn(
                  "w-4 h-4 text-slate-400 transition-transform",
                  userMenuOpen && "rotate-180"
                )}
              />
            </button>

            {userMenuOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setUserMenuOpen(false)} />
                <div className="absolute right-0 mt-2 w-48 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg py-1.5">
                  <div className="px-4 py-2 border-b border-slate-100 dark:border-slate-700">
                    <p className="text-sm font-bold text-slate-800 dark:text-slate-100 truncate">
                      {user?.full_name || user?.username || "Student"}
                    </p>
                    <p className="text-[11px] text-slate-400 truncate">{user?.email}</p>
                  </div>
                  <Link
                    to="/profile"
                    onClick={() => setUserMenuOpen(false)}
                    className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
                  >
                    <User className="w-4 h-4 text-slate-400" /> Profile
                  </Link>
                  <div className="my-1 border-t border-slate-100 dark:border-slate-700" />
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      logout();
                    }}
                    className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-danger-600 dark:text-danger-400 hover:bg-danger-50 dark:hover:bg-danger-900/20 transition-colors"
                  >
                    <LogOut className="w-4 h-4" /> Logout
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </header>
    </>
  );
}