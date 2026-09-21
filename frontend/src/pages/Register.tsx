import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { User, AtSign, Mail, Lock, Eye, EyeOff, UserPlus } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import logo from "@/assets/logo.png";

/* Password strength helpers */
function calcStrength(pw: string): number {
  let s = 0;
  if (pw.length >= 8)            s++;
  if (/[A-Z]/.test(pw))         s++;
  if (/[0-9]/.test(pw))         s++;
  if (/[^A-Za-z0-9]/.test(pw))  s++;
  return s;
}
const STRENGTH_LABEL = ["", "Weak", "Fair", "Good", "Strong"];
const STRENGTH_COLOR = [
  "",
  "bg-danger-400",
  "bg-warning-400",
  "bg-success-400 opacity-80",
  "bg-primary-500",
];

const FIELDS = [
  { key: "full_name", icon: User,    placeholder: "Your full name",      label: "Full Name",      type: "text"  },
  { key: "username",  icon: AtSign,  placeholder: "Choose a username",   label: "Username",       type: "text"  },
  { key: "email",     icon: Mail,    placeholder: "you@example.com",     label: "Email Address",  type: "email" },
] as const;

export default function Register() {
  const navigate = useNavigate();
  const { register, isLoading } = useAuthStore();
  const [form, setForm]       = useState({ full_name: "", email: "", username: "", password: "" });
  const [showPw, setShowPw]   = useState(false);
  const [error, setError]     = useState("");
  const [focused, setFocused] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);

  const strength = calcStrength(form.password);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 40);
    return () => clearTimeout(t);
  }, []);

  const f = (k: string) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm(p => ({ ...p, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await register(form);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed. Please try again.");
    }
  };

  return (
    <div className="relative min-h-screen bg-gradient-to-br from-slate-50 via-primary-50 to-secondary-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 flex items-center justify-center p-4 overflow-hidden">

      {/* ── Decorative floating orbs ── */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div
          className="absolute -bottom-40 -right-40 w-[28rem] h-[28rem] rounded-full bg-primary-200 dark:bg-primary-900 opacity-20 dark:opacity-10"
          style={{ filter: "blur(88px)", animation: "rp-float 10s ease-in-out infinite" }}
        />
        <div
          className="absolute -top-28 -left-28 w-80 h-80 rounded-full bg-primary-300 dark:bg-primary-800 opacity-15 dark:opacity-10"
          style={{ filter: "blur(72px)", animation: "rp-float 13s ease-in-out 4s infinite reverse" }}
        />
        <div
          className="absolute top-1/2 right-1/4 w-56 h-56 rounded-full bg-secondary-200 dark:bg-secondary-900 opacity-10"
          style={{ filter: "blur(60px)", animation: "rp-float 16s ease-in-out 8s infinite" }}
        />
      </div>

      {/* ── Main card ── */}
      <div
        className="relative z-10 w-full max-w-sm transition-all duration-700 ease-out"
        style={{ opacity: visible ? 1 : 0, transform: visible ? "translateY(0) scale(1)" : "translateY(24px) scale(0.97)" }}
      >
        {/* Logo block */}
        <div className="flex flex-col items-center gap-2 mb-8">
          <div className="relative">
            {/* Pulse ring */}
            <div
              className="absolute inset-0 rounded-2xl bg-primary-400 dark:bg-primary-600 opacity-0"
              style={{ animation: "rp-ring-pulse 2.8s ease-in-out infinite" }}
            />
            <div
              className="w-16 h-16 rounded-2xl bg-white dark:bg-[#222120] flex items-center justify-center border border-[#D6CBEC]/60 dark:border-[#383533] overflow-hidden shadow-glow-primary"
              style={{ animation: "rp-logo-bob 6s ease-in-out infinite" }}
            >
              <img src={logo} alt="Mentora logo" className="w-14 h-14 object-contain" />
            </div>
          </div>

          <h1
            className="text-2xl font-black gradient-text"
            style={{ animation: "rp-slide-up 0.55s cubic-bezier(0.16,1,0.3,1) 0.15s both" }}
          >
            Mentora
          </h1>
          <p
            className="text-slate-500 dark:text-slate-400 text-sm"
            style={{ animation: "rp-slide-up 0.55s cubic-bezier(0.16,1,0.3,1) 0.25s both" }}
          >
            Create your account
          </p>
        </div>

        {/* Form card */}
        <div
          className="card p-7 space-y-4"
          style={{ animation: "rp-slide-up 0.6s cubic-bezier(0.16,1,0.3,1) 0.1s both" }}
        >
          {/* Heading */}
          <div style={{ animation: "rp-slide-up 0.5s cubic-bezier(0.16,1,0.3,1) 0.18s both" }}>
            <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Get started</h2>
            <p className="text-xs text-slate-400 mt-0.5">Free forever · No credit card needed</p>
          </div>

          {/* Error */}
          {error && (
            <div
              className="p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-700 rounded-xl text-sm text-danger-600 dark:text-danger-400"
              style={{ animation: "rp-shake 0.4s ease" }}
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3.5">

            {/* Dynamic text fields */}
            {FIELDS.map((field, i) => (
              <div
                key={field.key}
                style={{ animation: `rp-slide-up 0.5s cubic-bezier(0.16,1,0.3,1) ${0.26 + i * 0.08}s both` }}
              >
                <label
                  htmlFor={`register-${field.key}`}
                  className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 ml-0.5"
                >
                  {field.label}
                </label>
                <div
                  className="relative rounded-xl transition-all duration-200"
                  style={{ boxShadow: focused === field.key ? "0 0 0 3px rgba(111,79,177,0.18)" : "none" }}
                >
                  <field.icon
                    className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 transition-colors duration-200"
                    style={{ color: focused === field.key ? "#6F4FB1" : "#94a3b8" }}
                  />
                  <input
                    id={`register-${field.key}`}
                    type={field.type}
                    value={form[field.key as keyof typeof form]}
                    onChange={f(field.key)}
                    placeholder={field.placeholder}
                    className="input pl-10"
                    required
                    onFocus={() => setFocused(field.key)}
                    onBlur={() => setFocused(null)}
                  />
                </div>
              </div>
            ))}

            {/* Password */}
            <div style={{ animation: "rp-slide-up 0.5s cubic-bezier(0.16,1,0.3,1) 0.5s both" }}>
              <label htmlFor="register-password" className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 ml-0.5">
                Password
              </label>
              <div
                className="relative rounded-xl transition-all duration-200"
                style={{ boxShadow: focused === "password" ? "0 0 0 3px rgba(111,79,177,0.18)" : "none" }}
              >
                <Lock
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 transition-colors duration-200"
                  style={{ color: focused === "password" ? "#6F4FB1" : "#94a3b8" }}
                />
                <input
                  id="register-password"
                  type={showPw ? "text" : "password"}
                  value={form.password}
                  onChange={f("password")}
                  placeholder="Create a strong password"
                  className="input pl-10 pr-10"
                  required
                  onFocus={() => setFocused("password")}
                  onBlur={() => setFocused(null)}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-primary-500 transition-colors duration-200"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>

              {/* Strength meter */}
              {form.password.length > 0 && (
                <div className="mt-2 space-y-1">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4].map(lvl => (
                      <div
                        key={lvl}
                        className={`flex-1 h-1 rounded-full transition-all duration-300 ${
                          strength >= lvl ? STRENGTH_COLOR[strength] : "bg-[#E7E5E0] dark:bg-[#383533]"
                        }`}
                      />
                    ))}
                  </div>
                  <p className={`text-xs ml-0.5 transition-colors duration-300 ${
                    strength === 1 ? "text-danger-500"
                    : strength === 2 ? "text-warning-600 dark:text-warning-400"
                    : strength === 3 ? "text-success-600 dark:text-success-400"
                    : strength === 4 ? "text-primary-600 dark:text-primary-400"
                    : ""
                  }`}>
                    {STRENGTH_LABEL[strength]}
                  </p>
                </div>
              )}
            </div>

            {/* Submit */}
            <div style={{ animation: "rp-slide-up 0.5s cubic-bezier(0.16,1,0.3,1) 0.58s both" }} className="pt-1">
              <button
                id="register-submit"
                type="submit"
                disabled={isLoading}
                className="btn-primary btn-md w-full relative overflow-hidden group"
              >
                {/* Shimmer sweep */}
                <span
                  className="absolute inset-0 translate-x-[-110%] group-hover:translate-x-[110%] transition-transform duration-700 ease-in-out"
                  style={{ background: "linear-gradient(105deg, transparent 40%, rgba(255,255,255,0.18) 50%, transparent 60%)" }}
                />
                <span className="relative flex items-center justify-center gap-2">
                  {isLoading
                    ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    : <><UserPlus className="w-4 h-4" /> Create Account</>
                  }
                </span>
              </button>
            </div>
          </form>

          {/* Divider */}
          <div
            className="relative flex items-center gap-3"
            style={{ animation: "rp-slide-up 0.5s cubic-bezier(0.16,1,0.3,1) 0.65s both" }}
          >
            <div className="flex-1 h-px bg-[#E7E5E0] dark:bg-[#383533]" />
            <span className="text-xs text-slate-400 dark:text-slate-500">Already have one?</span>
            <div className="flex-1 h-px bg-[#E7E5E0] dark:bg-[#383533]" />
          </div>

          {/* Sign-in CTA */}
          <p
            className="text-center text-sm text-slate-500"
            style={{ animation: "rp-slide-up 0.5s cubic-bezier(0.16,1,0.3,1) 0.7s both" }}
          >
            Have an account?{" "}
            <Link to="/login" className="text-primary-600 dark:text-primary-400 font-semibold hover:underline">
              Sign in →
            </Link>
          </p>
        </div>
      </div>

      {/* ── Keyframes ── */}
      <style>{`
        @keyframes rp-slide-up {
          from { opacity: 0; transform: translateY(14px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes rp-float {
          0%, 100% { transform: translateY(0px); }
          50%       { transform: translateY(-22px); }
        }
        @keyframes rp-logo-bob {
          0%, 100% { transform: translateY(0px); }
          50%       { transform: translateY(-5px); }
        }
        @keyframes rp-ring-pulse {
          0%   { opacity: 0;    transform: scale(1);    }
          40%  { opacity: 0.25; transform: scale(1.18); }
          100% { opacity: 0;    transform: scale(1.38); }
        }
        @keyframes rp-shake {
          0%,100% { transform: translateX(0); }
          20%     { transform: translateX(-5px); }
          40%     { transform: translateX(5px); }
          60%     { transform: translateX(-3px); }
          80%     { transform: translateX(3px); }
        }
      `}</style>
    </div>
  );
}
