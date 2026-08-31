import AppLayout from "@/components/layout/AppLayout";
import { User, Mail, GraduationCap, Calendar, Edit3, Save, X } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { getInitials } from "@/lib/utils";
import { useState } from "react";
import { UserUpdate } from "@/types";

export default function Profile() {
  const { user, updateUser, isLoading } = useAuthStore();
  const name = user?.full_name || user?.username || "Student";

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    full_name: user?.full_name || "",
    username: user?.username || "",
    email: user?.email || "",
    avatar_url: user?.avatar_url || "",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleEdit = () => {
    setForm({
      full_name: user?.full_name || "",
      username: user?.username || "",
      email: user?.email || "",
      avatar_url: user?.avatar_url || "",
    });
    setEditing(true);
    setError("");
    setSuccess("");
  };

  const handleChange = (field: string, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      const payload: UserUpdate = {};
      if (form.full_name !== (user?.full_name || "")) payload.full_name = form.full_name || null;
      if (form.username !== (user?.username || "")) payload.username = form.username;
      if (form.email !== (user?.email || "")) payload.email = form.email;
      if (form.avatar_url !== (user?.avatar_url || "")) payload.avatar_url = form.avatar_url || null;
      if (Object.keys(payload).length === 0) {
        setEditing(false);
        return;
      }
      await updateUser(payload);
      setSuccess("Profile updated successfully");
      setEditing(false);
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update profile");
    }
  };

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
          {editing ? (
            <button onClick={() => { setEditing(false); setError(""); setSuccess(""); }} className="btn-outline btn-sm">
              <X className="w-4 h-4" /> Cancel
            </button>
          ) : (
            <button onClick={handleEdit} className="btn-outline btn-sm"><Edit3 className="w-4 h-4" /> Edit Profile</button>
          )}
        </div>

        {error && (
          <div className="p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-700 rounded-xl text-sm text-danger-600 dark:text-danger-400">
            {error}
          </div>
        )}
        {success && (
          <div className="p-3 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-700 rounded-xl text-sm text-success-600 dark:text-success-400">
            {success}
          </div>
        )}

        {editing && (
          <div className="card p-5 sm:p-6">
            <h3 className="font-bold text-slate-700 dark:text-slate-200 mb-4">Edit Profile</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-xs text-slate-400 mb-1 block">Full Name</label>
                <input
                  type="text"
                  value={form.full_name}
                  onChange={e => handleChange("full_name", e.target.value)}
                  className="input w-full"
                  placeholder="Your full name"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">Username</label>
                <input
                  type="text"
                  value={form.username}
                  onChange={e => handleChange("username", e.target.value)}
                  className="input w-full"
                  placeholder="Your username"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={e => handleChange("email", e.target.value)}
                  className="input w-full"
                  placeholder="Your email"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">Avatar URL</label>
                <input
                  type="url"
                  value={form.avatar_url}
                  onChange={e => handleChange("avatar_url", e.target.value)}
                  className="input w-full"
                  placeholder="https://example.com/avatar.png"
                />
              </div>
              <button type="submit" disabled={isLoading} className="btn-primary btn-md w-full">
                {isLoading ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : <><Save className="w-4 h-4 inline" /> Save Changes</>}
              </button>
            </form>
          </div>
        )}

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