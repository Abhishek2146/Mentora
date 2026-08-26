import { useState, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppLayout from "@/components/layout/AppLayout";
import { notificationService } from "@/services/notificationService";
import { Bell, Check, Archive, X, Loader2, Filter, ChevronRight, AlertTriangle, Trophy, Info, Cpu } from "lucide-react";
import type { Notification, NotificationType, NotificationPriority } from "@/types/api";

const TYPE_OPTIONS = [
  { value: "", label: "All Types" },
  { value: "info", label: "Info" },
  { value: "success", label: "Success" },
  { value: "warning", label: "Warning" },
  { value: "error", label: "Error" },
  { value: "reminder", label: "Reminder" },
  { value: "achievement", label: "Achievement" },
  { value: "system", label: "System" },
];

const PRIORITY_OPTIONS = [
  { value: "", label: "All Priorities" },
  { value: "low", label: "Low" },
  { value: "normal", label: "Normal" },
  { value: "high", label: "High" },
  { value: "urgent", label: "Urgent" },
];

export default function NotificationsPage() {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState({ total: 0, page: 1, per_page: 20, pages: 0, unread_count: 0 });
  const [filters, setFilters] = useState({
    unread_only: false,
    archived_only: false,
    notification_type: "",
    priority: "",
  });

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await notificationService.getNotifications({
        page: pagination.page,
        per_page: pagination.per_page,
        unread_only: filters.unread_only,
        archived_only: filters.archived_only,
        notification_type: filters.notification_type || undefined,
      });
      setNotifications(response.items);
      setPagination(prev => ({
        ...prev,
        total: response.total,
        page: response.page,
        per_page: response.per_page,
        pages: response.pages,
        unread_count: response.unread_count,
      }));
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load notifications");
    } finally {
      setLoading(false);
    }
  }, [pagination.page, filters.unread_only, filters.archived_only, filters.notification_type]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const handleMarkAsRead = async (notification: Notification) => {
    if (notification.is_read) return;
    try {
      await notificationService.markAsRead(notification.id);
      setNotifications(prev => prev.map(n => n.id === notification.id ? { ...n, is_read: true } : n));
      setPagination(prev => ({ ...prev, unread_count: Math.max(0, prev.unread_count - 1) }));
    } catch (e) {
      console.error("Failed to mark as read:", e);
    }
  };

  const handleMarkAsUnread = async (notification: Notification) => {
    if (!notification.is_read) return;
    try {
      await notificationService.markAsUnread(notification.id);
      setNotifications(prev => prev.map(n => n.id === notification.id ? { ...n, is_read: false } : n));
      setPagination(prev => ({ ...prev, unread_count: prev.unread_count + 1 }));
    } catch (e) {
      console.error("Failed to mark as unread:", e);
    }
  };

  const handleArchive = async (notification: Notification) => {
    try {
      await notificationService.archive(notification.id);
      setNotifications(prev => prev.filter(n => n.id !== notification.id));
      setPagination(prev => ({ ...prev, total: prev.total - 1 }));
    } catch (e) {
      console.error("Failed to archive:", e);
    }
  };

  const handleUnarchive = async (notification: Notification) => {
    try {
      await notificationService.unarchive(notification.id);
      // Would need to refetch to get the unarchived notification
      fetchNotifications();
    } catch (e) {
      console.error("Failed to unarchive:", e);
    }
  };

  const handleDelete = async (notification: Notification) => {
    if (!window.confirm("Delete this notification?")) return;
    try {
      await notificationService.delete(notification.id);
      setNotifications(prev => prev.filter(n => n.id !== notification.id));
      setPagination(prev => ({ ...prev, total: prev.total - 1 }));
    } catch (e) {
      console.error("Failed to delete:", e);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationService.markAllAsRead();
      fetchNotifications();
    } catch (e) {
      console.error("Failed to mark all as read:", e);
    }
  };

  const getTypeColor = (type: NotificationType) => {
    switch (type) {
      case "success": return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400";
      case "warning": return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
      case "error": return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
      case "achievement": return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
      case "reminder": return "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400";
      case "system": return "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400";
      default: return "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400";
    }
  };

  const getPriorityColor = (priority: NotificationPriority) => {
    switch (priority) {
      case "urgent": return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
      case "high": return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
      case "normal": return "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400";
      default: return "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300";
    }
  };

  const getTypeIcon = (type: NotificationType) => {
    switch (type) {
      case "success": return <Check className="w-3 h-3" />;
      case "warning": return <AlertTriangle className="w-3 h-3" />;
      case "error": return <X className="w-3 h-3" />;
      case "achievement": return <Trophy className="w-3 h-3" />;
      case "reminder": return <Bell className="w-3 h-3" />;
      case "system": return <Cpu className="w-3 h-3" />;
      default: return <Info className="w-3 h-3" />;
    }
  };

  // Need to import these icons
  return (
    <AppLayout title="Notifications">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header with stats and actions */}
        <div className="card p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Notifications</h1>
              <p className="text-slate-500 dark:text-slate-400 mt-1">Manage your notifications and alerts</p>
            </div>
            <div className="flex items-center gap-3">
              {pagination.unread_count > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="btn-primary btn-sm"
                >
                  <Check className="w-4 h-4 mr-2" />
                  Mark all as read ({pagination.unread_count})
                </button>
              )}
            </div>
          </div>

          {/* Filters */}
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filters.unread_only}
                onChange={(e) => setFilters(prev => ({ ...prev, unread_only: e.target.checked, archived_only: false }))}
                className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-slate-700 dark:text-slate-300">Unread only</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filters.archived_only}
                onChange={(e) => setFilters(prev => ({ ...prev, archived_only: e.target.checked, unread_only: false }))}
                className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-slate-700 dark:text-slate-300">Archived</span>
            </label>
            <select
              value={filters.notification_type}
              onChange={(e) => setFilters(prev => ({ ...prev, notification_type: e.target.value }))}
              className="input py-2 text-sm"
            >
              {TYPE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Notifications List */}
        <div className="card">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
              <span className="ml-3 text-slate-600 dark:text-slate-400">Loading…</span>
            </div>
          ) : error ? (
            <div className="p-6 text-center text-red-500">{error}</div>
          ) : notifications.length === 0 ? (
            <div className="p-12 text-center">
              <Bell className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <h3 className="font-bold text-slate-700 dark:text-slate-200">No notifications</h3>
              <p className="text-slate-500 dark:text-slate-400 mt-1">
                {filters.unread_only ? "You're all caught up!" : "No notifications match your filters."}
              </p>
            </div>
          ) : (
            <>
              <div className="divide-y divide-slate-200 dark:divide-slate-700">
                {notifications.map((notification) => (
                  <div
                    key={notification.id}
                    className={`p-4 transition-colors ${
                      notification.is_read
                        ? "hover:bg-slate-50 dark:hover:bg-slate-700/50"
                        : "bg-primary-50/50 dark:bg-primary-900/20 hover:bg-primary-50 dark:hover:bg-primary-900/30"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${getTypeColor(notification.type)}`}>
                        {getTypeIcon(notification.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <h3 className="font-semibold text-slate-800 dark:text-slate-100">
                                {notification.title}
                              </h3>
                              <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getTypeColor(notification.type)}`}>
                                {notification.type}
                              </span>
                              <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getPriorityColor(notification.priority)}`}>
                                {notification.priority}
                              </span>
                              {!notification.is_read && (
                                <span className="w-2 h-2 bg-primary-500 rounded-full flex-shrink-0 mt-1.5" />
                              )}
                            </div>
                            <p className="text-slate-600 dark:text-slate-300 mt-1 line-clamp-2">
                              {notification.message}
                            </p>
                            {notification.related_entity_type && notification.related_entity_id && (
                              <Link
                                to={notification.related_entity_type === "syllabus" ? `/syllabus/${notification.related_entity_id}` : "#"}
                                className="text-sm text-primary-600 dark:text-primary-400 hover:underline mt-2 inline-block"
                              >
                                View {notification.related_entity_type}
                              </Link>
                            )}
                          </div>
                          <div className="flex items-center gap-1 ml-4">
                            <p className="text-xs text-slate-400 whitespace-nowrap">
                              {new Date(notification.created_at).toLocaleDateString()}
                            </p>
                            <div className="relative">
                              <button
                                className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                              >
                                <ChevronRight className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
                          {!notification.is_read && (
                            <button
                              onClick={() => handleMarkAsRead(notification)}
                              className="btn-ghost btn-sm text-xs"
                            >
                              <Check className="w-3 h-3 mr-1" /> Mark read
                            </button>
                          )}
                          {notification.is_read && (
                            <button
                              onClick={() => handleMarkAsUnread(notification)}
                              className="btn-ghost btn-sm text-xs"
                            >
                              Mark unread
                            </button>
                          )}
                          {!notification.is_archived && (
                            <button
                              onClick={() => handleArchive(notification)}
                              className="btn-ghost btn-sm text-xs"
                            >
                              <Archive className="w-3 h-3 mr-1" /> Archive
                            </button>
                          )}
                          {notification.is_archived && (
                            <button
                              onClick={() => handleUnarchive(notification)}
                              className="btn-ghost btn-sm text-xs"
                            >
                              Unarchive
                            </button>
                          )}
                          <button
                            onClick={() => handleDelete(notification)}
                            className="btn-ghost btn-sm text-xs text-danger-600 hover:bg-danger-50 dark:hover:bg-red-900/20 ml-auto"
                          >
                            <X className="w-3 h-3 mr-1" /> Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {pagination.pages > 1 && (
                <div className="p-4 border-t border-slate-200 dark:border-slate-700">
                  <nav className="flex items-center justify-center gap-1" aria-label="Pagination">
                    <button
                      onClick={() => setPagination(prev => ({ ...prev, page: prev.page - 1 }))}
                      disabled={pagination.page <= 1}
                      className="p-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      aria-label="Previous page"
                    >
                      <ChevronRight className="w-5 h-5 rotate-180" />
                    </button>
                    {Array.from({ length: Math.min(pagination.pages, 5) }, (_, i) => {
                      let pageNum;
                      if (pagination.pages <= 5) {
                        pageNum = i + 1;
                      } else if (pagination.page <= 3) {
                        pageNum = i + 1;
                      } else if (pagination.page >= pagination.pages - 2) {
                        pageNum = pagination.pages - 4 + i;
                      } else {
                        pageNum = pagination.page - 2 + i;
                      }
                      return (
                        <button
                          key={pageNum}
                          onClick={() => setPagination(prev => ({ ...prev, page: pageNum }))}
                          className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                            pageNum === pagination.page
                              ? "bg-primary-500 text-white"
                              : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                    <button
                      onClick={() => setPagination(prev => ({ ...prev, page: prev.page + 1 }))}
                      disabled={pagination.page >= pagination.pages}
                      className="p-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      aria-label="Next page"
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </nav>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </AppLayout>
  );
}