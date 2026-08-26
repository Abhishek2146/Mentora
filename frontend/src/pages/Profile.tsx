import AppLayout from "@/components/layout/AppLayout";
import { User, Mail, GraduationCap, Calendar, Edit3 } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { getInitials } from "@/lib/utils";

export default function Profile() {
  const { user } = useAuthStore();
  const name = user?.full_name || user?.username || "Student";
  return (
    <AppLayout title="Profile">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="card p-5 sm:p-8 flex flex-col items-center gap-4 text-center">
          <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white text-3xl font-black shadow-glow-primary">
            {user ? getInitials(name) : "U"}
          </div>
          <div>
            <h2 className="text-xl sm:text-2xl font-bold text-slate-800 dark:text-slate-100 break-words">{name}</h2>
            <p className="text-slate-500">{user?.email || "student@mentora.ai"}</p>
            <span className="badge-blue mt-2 inline-flex capitalize">{user?.role || "student"}</span>
          </div>
          <button className="btn-outline btn-sm"><Edit3 className="w-4 h-4" /> Edit Profile</button>
        </div>
        <div className="card p-5 sm:p-6 space-y-4">
          <h3 className="font-bold text-slate-700 dark:text-slate-200">Account Details</h3>
          {[
            { icon: User, label: "Username", value: user?.username || "dipeesh" },
            { icon: Mail, label: "Email", value: user?.email || "student@mentora.ai" },
            { icon: GraduationCap, label: "Role", value: user?.role || "student" },
            { icon: Calendar, label: "Joined", value: user?.created_at ? new Date(user.created_at).toLocaleDateString() : "2024-01-01" },
          ].map(f => (
            <div key={f.label} className="flex items-center gap-4 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-xl">
              <div className="w-9 h-9 rounded-lg bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center">
                <f.icon className="w-4 h-4 text-primary-600 dark:text-primary-400" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs text-slate-400">{f.label}</p>
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-200 capitalize break-words">{f.value}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
