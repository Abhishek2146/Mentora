import { useEffect, useMemo, useState } from "react";
import { Users, BookOpen, ClipboardList, Code2, CreditCard, Plus, Search, Filter, MoreVertical, Edit, Trash2, Eye, GraduationCap } from "lucide-react";
import { adminService } from "@/services/adminService";
import { useAuthStore } from "@/store/authStore";
import type { User } from "@/types";
import { cn, getInitials, formatDate } from "@/lib/utils";

type SortField = "id" | "username" | "email" | "created_at";

export default function InstructorDashboard() {
  const { user } = useAuthStore();
  const [students, setStudents] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [sortField, setSortField] = useState<SortField>("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const loadStudents = async () => {
    try {
      const data = await adminService.listUsers({ role: "student", search: search || undefined });
      setStudents(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load students");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStudents();
  }, []);

  useEffect(() => {
    const t = setTimeout(loadStudents, 300);
    return () => clearTimeout(t);
  }, [search]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(d => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  const sortedStudents = useMemo(() => {
    const arr = [...students];
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
  }, [students, sortField, sortDir]);

  const statCards = [
    { label: "Total Students", value: students.length, icon: Users, color: "text-emerald-600", bg: "bg-emerald-50 dark:bg-emerald-900/30" },
    { label: "Active Students", value: students.filter(s => s.is_active).length, icon: Users, color: "text-teal-600", bg: "bg-teal-50 dark:bg-teal-900/30" },
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
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-800 dark:text-slate-100">Instructor Dashboard</h1>
            <p className="text-sm text-slate-500">Manage your students & courses</p>
          </div>
          <button onClick={loadStudents} className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-sm hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
            Refresh
          </button>
        </div>

        {error && <div className="p-3 bg-danger-50 border border-danger-200 rounded-xl text-sm text-danger-600">{error}</div>}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

        <div className="card p-5">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h3 className="font-bold text-slate-800 dark:text-slate-100">Student Management</h3>
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Search students…"
                  className="input pl-9 py-2 text-sm"
                />
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-[11px] uppercase tracking-wider text-slate-400">
                  {(["id", "username", "email", "created_at"] as SortField[]).map(f => (
                    <th key={f} className="pb-2 px-2">
                      <button onClick={() => toggleSort(f)} className="flex items-center gap-1 hover:text-slate-600 dark:hover:text-slate-200">
                        {f}
                        {sortField === f && (sortDir === "asc" ? " ▲" : " ▼")}
                      </button>
                    </th>
                  ))}
                  <th className="pb-2 px-2">Status</th>
                  <th className="pb-2 px-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedStudents.map(s => (
                  <tr key={s.id} className="border-b border-slate-100 dark:border-slate-700/50">
                    <td className="py-2.5 px-2 text-slate-500">{s.id}</td>
                    <td className="py-2.5 px-2">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                          {s.full_name ? getInitials(s.full_name) : s.username?.[0]?.toUpperCase() ?? "U"}
                        </div>
                        <div className="min-w-0">
                          <p className="font-semibold text-slate-800 dark:text-slate-100 truncate">{s.full_name || s.username}</p>
                          <p className="text-[11px] text-slate-400">@{s.username}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-2.5 px-2 text-slate-500">{s.email}</td>
                    <td className="py-2.5 px-2 text-slate-500">{s.created_at ? formatDate(s.created_at) : "—"}</td>
                    <td className="py-2.5 px-2">
                      <span className={cn(
                        "inline-flex items-center gap-1 text-xs font-medium rounded-full px-2 py-0.5",
                        s.is_active
                          ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-300"
                          : "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400"
                      )}>
                        {s.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="py-2.5 px-2">
                      <div className="flex items-center gap-1">
                        <button title="View details" className="p-1.5 rounded-lg text-slate-400 hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors">
                          <Eye className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {students.length === 0 && !loading && (
              <p className="text-sm text-slate-500 text-center py-6">No students found.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}