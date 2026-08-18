import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShieldCheck, Mail, Lock, User, Eye, EyeOff, KeyRound } from "lucide-react";
import { useAuthStore } from "@/store/authStore";

export default function AdminRegister() {
  const navigate = useNavigate();
  const { registerAdmin, isLoading } = useAuthStore();
  const [form, setForm] = useState({ full_name: "", username: "", email: "", password: "", admin_secret: "" });
  const [showPw, setShowPw] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await registerAdmin(form);
      navigate("/admin/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Admin registration failed. Please try again.");
    }
  };

  const f = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => setForm(p => ({ ...p, [k]: e.target.value }));

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-primary-50 to-secondary-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center shadow-lg">
            <ShieldCheck className="w-8 h-8 text-primary-400" />
          </div>
          <h1 className="text-2xl font-black gradient-text">Mentora Admin</h1>
          <p className="text-slate-500 text-sm">Register an administrator account</p>
        </div>

        <div className="card p-7 space-y-5">
          <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Admin sign up</h2>

          {error && <div className="p-3 bg-danger-50 border border-danger-200 rounded-xl text-sm text-danger-600">{error}</div>}

          <form onSubmit={handleSubmit} className="space-y-4">
            {[
              { key: "full_name", icon: User, placeholder: "Full name", type: "text" },
              { key: "username", icon: User, placeholder: "Username", type: "text" },
              { key: "email", icon: Mail, placeholder: "Email address", type: "email" },
            ].map(field => (
              <div key={field.key} className="relative">
                <field.icon className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input type={field.type} value={form[field.key as keyof typeof form]}
                  onChange={f(field.key)} placeholder={field.placeholder}
                  id={`admin-register-${field.key}`}
                  className="input pl-10" required />
              </div>
            ))}
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input id="admin-register-password" type={showPw ? "text" : "password"} value={form.password} onChange={f("password")}
                placeholder="Password" className="input pl-10 pr-10" required />
              <button type="button" onClick={() => setShowPw(!showPw)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400">
                {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <div className="relative">
              <KeyRound className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input id="admin-register-secret" type={showSecret ? "text" : "password"} value={form.admin_secret} onChange={f("admin_secret")}
                placeholder="Admin registration key" className="input pl-10 pr-10" required />
              <button type="button" onClick={() => setShowSecret(!showSecret)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400">
                {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <button id="admin-register-submit" type="submit" disabled={isLoading} className="btn-primary btn-md w-full">
              {isLoading ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : <><ShieldCheck className="w-4 h-4" /> Create Admin Account</>}
            </button>
          </form>
          <p className="text-center text-sm text-slate-500">
            Already an admin? <Link to="/login" className="text-primary-600 font-semibold hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}