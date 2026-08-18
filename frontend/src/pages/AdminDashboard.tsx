import { useEffect, useMemo, useState } from "react";
import {
  Users, UserPlus, ShieldCheck, Activity, FileText, CalendarDays,
  ClipboardList, Code2, CreditCard, BookOpen, Trash2, RefreshCw,
  Search, ChevronUp, ChevronDown, Ban, CheckCircle2, BarChart3,
} from "lucide-react";
import { adminService } from "@/services/adminService";
import { useAuthStore } from "@/store/authStore";
import type { AdminDashboardStats, User } from "@/types";
import { cn, getInitials, formatDate } from "@/lib/utils";

type SortField = "id" | "username" | "email" | "role" | "created_at";

export default function AdminDashboard() {
  const { user } = useAuthStore();
  const [stats, setStats] = useState<AdminDashboardStats["stats"] | null>(null);
  const [recent, setRecent] = useState<AdminDashboardStats["recent_registrations"]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [userLoading, setUserLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [sortField, setSortField] = useState<SortField>("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [actionMsg, setActionMsg] = useState("");

  const loadStats = async () => {
    try {
      const data = await adminService.getDashboard();
      setStats(data.stats);
      setRecent(data.recent_registrations);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load admin dashboard");
    }
  };

  const loadUsers = async () => {
    setUserLoading(true);
    try {
      const data = await adminService.listUsers({
        search: search || undefined,
        role: roleFilter || undefined,
      });
      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setUserLoading(false);
    }
  };

  useEffect(() => {
    (async () => {
      setLoading(true);
      await Promise.all([loadStats(), loadUsers()]);
      setLoading(false);
    })();
  }, []);

  useEffect(() => {
    const t = setTimeout(loadUsers, 300);
    return () => clearTimeout(t);
  }, [search, roleFilter]);

  const toggleActive = async (u: User) => {
    setActionMsg("");
    try {
      await adminService.updateUser(u.id, { is_active: !u.is_active });
      setUsers(prev => prev.map(x => (x.id === u.id ? { ...x, is_active: !u.is_active } : x)));
      await loadStats();
      setActionMsg(`User "${u.username}" ${u.is_active ? "deactivated" : "activated"}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update user");
    }
  };

  const changeRole = async (u: User, role: string) => {
    setActionMsg("");
    try {
      await adminService.updateUser(u.id, { role });
      setUsers(prev => prev.map(x => (x.id === u.id ? { ...x, role: role as User["role"] } : x)));
      await loadStats();
      setActionMsg(`Role updated for "${u.username}"`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update role");
    }
  };

  const removeUser = async (u: User) => {
    if (!window.confirm(`Delete user "${u.username}"? This cannot be undone.`)) return;
    setActionMsg("");
    try {
      await adminService.deleteUser(u.id);
      setUsers(prev => prev.filter(x => x.id !== u.id));
      await loadStats();
      setActionMsg(`User "${u.username}" deleted`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete user");
    }
  };

  const sortedUsers = useMemo(() => {
    const arr = [...users];
    arr.sort((a, b) => {
      const av = a[sortField] ?? "";
      const bv = b[sortField] ?? "";
      if (typeof av === "number" && typeof bv === "number") {
        return sortDir === "asc" ? av - bv : bv - av;
      }
      return sortDir === "asc"
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
    return arr;
  }, [users, sortField, sortDir]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(d => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  const statCards = [
    { label: "Total Users", value: stats?.total_users ?? 0, icon: Users, color: "text-primary-600", bg: "bg-primary-50 dark:bg-primary-900/30" },
    { label: "Students", value: stats?.total_students ?? 0, icon: UserPlus, color: "text-emerald-600", bg: "bg-emerald-50 dark:bg-emerald-900/30" },
    { label: "Active Users", value: stats?.active_users ?? 0, icon: Activity, color: "text-teal-600", bg: "bg-teal-50 dark:bg-teal-900/30" },
    { label: "Admins", value: stats?.total_admins ?? 0, icon: ShieldCheck, color: "text-violet-600", bg: "bg-violet-50 dark:bg-violet-900/30" },
    { label: "Syllabi", value: stats?.total_syllabi ?? 0, icon: FileText, color: "text-sky-600", bg: "bg-sky-50 dark:bg-sky-900/30" },
    { label: "Study Plans", value: stats?.total_study_plans ?? 0, icon: CalendarDays, color: "text-indigo-600", bg: "bg-indigo-50 dark:bg-indigo-900/30" },
    { label: "Quizzes", value: stats?.total_quizzes ?? 0, icon: ClipboardList, color: "text-amber-600", bg: "bg-amber-50 dark:bg-amber-900/30" },
    { label: "Quiz Attempts", value: stats?.total_quiz_attempts ?? 0, icon: BarChart3, color: "text-rose-600", bg: "bg-rose-50 dark:bg-rose-900/30" },
    { label: "Coding Problems", value: stats?.total_coding_problems ?? 0, icon: Code2, color: "text-lime-600", bg: "bg-lime-50 dark:bg-lime-900/30" },
    { label: "Flashcard Decks", value: stats?.total_flashcard_decks ?? 0, icon: CreditCard, color: "text-fuchsia-600", bg: "bg-fuchsia-50 dark:bg-fuchsia-900/30" },
    { label: "Avg Quiz Score", value: `${stats?.avg_quiz_score ?? 0}%`, icon: BookOpen, color: "text-cyan-600", bg: "bg-cyan-50 dark:bg-cyan-900/30" },
    { label: "Coding Submissions", value: stats?.total_coding_submissions ?? 0, icon: Code2, color: "text-orange-600", bg: "bg-orange-50 dark:bg-orange-900/30" },
  ];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <span className="w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-800 dark:text-slate-100">Admin Dashboard</h1>
            <p className="text-sm text-slate-500">Platform overview & user management</p>
          </div>
          <div className="flex items-center gap-3">
            {actionMsg && <span className="text-sm text-emerald-600 bg-emerald-50 dark:bg-emerald-900/30 px-3 py-1.5 rounded-xl font-medium">{actionMsg}</span>}
            <button onClick={() => { loadStats(); loadUsers(); }} className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-sm hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
          </div>
        </div>

        {error && <div className="p-3 bg-danger-50 border border-danger-200 rounded-xl text-sm text-danger-600">{error}</div>}

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
          {statCards.map(s => (
            <div key={s.label} className="stat-card">
              <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center", s.bg)}>
                <s.icon className={cn("w-4.5 h-4.5", s.color)} style={{ width: 18, height: 18 }} />
              </div>
              <div>
                <p className="text-xl font-bold text-slate-800 dark:text-slate-100">{s.value}</p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">{s.label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Recent registrations */}
        <div className="card p-5">
          <h3 className="font-bold text-slate-800 dark:text-slate-100 mb-3">Recent Registrations</h3>
          {recent.length === 0 ? (
            <p className="text-sm text-slate-500">No users registered yet.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {recent.map(u => (
                <div key={u.id} className="flex items-center gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-700">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
                    {u.full_name ? getInitials(u.full_name) : u.username?.[0]?.toUpperCase() ?? "U"}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">{u.full_name || u.username}</p>
                    <p className="text-xs text-slate-400 truncate">{u.email}</p>
                    <p className="text-[10px] text-slate-400 capitalize">{u.role} • {u.created_at ? formatDate(u.created_at) : ""}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* User management */}
        <div className="card p-5">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h3 className="font-bold text-slate-800 dark:text-slate-100">User Management</h3>
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Search users…"
                  className="input pl-9 py-2 text-sm"
                />
              </div>
              <select
                value={roleFilter}
                onChange={e => setRoleFilter(e.target.value)}
                className="input py-2 text-sm"
              >
                <option value="">All roles</option>
                <option value="student">Student</option>
                <option value="instructor">Instructor</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>

          {userLoading && <p className="text-sm text-slate-400 mb-3">Loading…</p>}

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-[11px] uppercase tracking-wider text-slate-400">
                  {(["id", "username", "email", "role", "created_at"] as SortField[]).map(f => (
                    <th key={f} className="pb-2 px-2">
                      <button onClick={() => toggleSort(f)} className="flex items-center gap-1 hover:text-slate-600 dark:hover:text-slate-200">
                        {f}
                        {sortField === f && (sortDir === "asc" ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                      </button>
                    </th>
                  ))}
                  <th className="pb-2 px-2">Status</th>
                  <th className="pb-2 px-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedUsers.map(u => (
                  <tr key={u.id} className="border-b border-slate-100 dark:border-slate-700/50">
                    <td className="py-2.5 px-2 text-slate-500">{u.id}</td>
                    <td className="py-2.5 px-2">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                          {u.full_name ? getInitials(u.full_name) : u.username?.[0]?.toUpperCase() ?? "U"}
                        </div>
                        <div className="min-w-0">
                          <p className="font-semibold text-slate-800 dark:text-slate-100 truncate">{u.full_name || u.username}</p>
                          <p className="text-[11px] text-slate-400">@{u.username}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-2.5 px-2 text-slate-500">{u.email}</td>
                    <td className="py-2.5 px-2">
                      <select
                        value={u.role}
                        disabled={u.id === user?.id}
                        onChange={e => changeRole(u, e.target.value)}
                        className={cn(
                          "text-xs font-medium rounded-lg px-2 py-1 border",
                          u.role === "admin"
                            ? "bg-violet-50 text-violet-600 border-violet-200 dark:bg-violet-900/30 dark:text-violet-300 dark:border-violet-700"
                            : u.role === "instructor"
                              ? "bg-sky-50 text-sky-600 border-sky-200 dark:bg-sky-900/30 dark:text-sky-300 dark:border-sky-700"
                              : "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-700"
                        )}
                      >
                        <option value="student">student</option>
                        <option value="instructor">instructor</option>
                        <option value="admin">admin</option>
                      </select>
                    </td>
                    <td className="py-2.5 px-2 text-slate-500">{u.created_at ? formatDate(u.created_at) : "—"}</td>
                    <td className="py-2.5 px-2">
                      <span className={cn(
                        "inline-flex items-center gap-1 text-xs font-medium rounded-full px-2 py-0.5",
                        u.is_active
                          ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-300"
                          : "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400"
                      )}>
                        {u.is_active ? <CheckCircle2 className="w-3 h-3" /> : <Ban className="w-3 h-3" />}
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="py-2.5 px-2">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => toggleActive(u)}
                          disabled={u.id === user?.id}
                          title={u.is_active ? "Deactivate" : "Activate"}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                          {u.is_active ? <Ban className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
                        </button>
                        <button
                          onClick={() => removeUser(u)}
                          disabled={u.id === user?.id}
                          title="Delete user"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-danger-600 hover:bg-danger-50 dark:hover:bg-red-900/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {users.length === 0 && !userLoading && (
              <p className="text-sm text-slate-500 text-center py-6">No users found.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}