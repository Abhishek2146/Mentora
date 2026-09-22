import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Mail, Lock, Eye, EyeOff, LogIn } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import logo from "@/assets/logo.png";

export default function Login() {
  const navigate = useNavigate();
const { login, resendVerification, isLoading } = useAuthStore();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [error, setError]       = useState("");
  const [resendMsg, setResendMsg] = useState("");
  const [focused, setFocused]   = useState<string | null>(null);
  const [visible, setVisible]   = useState(false);

  /* Mount animation trigger */
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 40);
    return () => clearTimeout(t);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setResendMsg("");
    try {
      await login(email, password);
      const role = useAuthStore.getState().user?.role;
      navigate(role === "admin" ? "/admin/dashboard" : "/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid email or password");
    }
  };

  const needsVerification = error.includes("verify your email");

  const handleResend = async () => {
    setResendMsg("");
    setError("");
    try {
      await resendVerification(email);
      setResendMsg("A new confirmation email has been sent.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resend verification email.");
    }
  };

  return (
    <div className="relative min-h-screen bg-gradient-to-br from-slate-50 via-primary-50 to-secondary-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 flex items-center justify-center p-4 overflow-hidden">

      {/* ── Decorative floating orbs (theme colours only) ── */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {/* Bottom-left soft blob */}
        <div
          className="absolute -bottom-32 -left-32 w-96 h-96 rounded-full bg-primary-200 dark:bg-primary-900 opacity-20 dark:opacity-10"
          style={{ filter: "blur(80px)", animation: "lp-float 9s ease-in-out infinite" }}
        />
        {/* Top-right soft blob */}
        <div
          className="absolute -top-24 -right-24 w-80 h-80 rounded-full bg-primary-300 dark:bg-primary-800 opacity-15 dark:opacity-10"
          style={{ filter: "blur(72px)", animation: "lp-float 12s ease-in-out 3s infinite reverse" }}
        />
        {/* Center accent speck */}
        <div
          className="absolute top-1/3 left-1/4 w-48 h-48 rounded-full bg-secondary-200 dark:bg-secondary-900 opacity-10"
          style={{ filter: "blur(60px)", animation: "lp-float 15s ease-in-out 6s infinite" }}
        />
      </div>

      {/* ── Main card ── */}
      <div
        className="relative z-10 w-full max-w-sm transition-all duration-700 ease-out"
        style={{ opacity: visible ? 1 : 0, transform: visible ? "translateY(0) scale(1)" : "translateY(24px) scale(0.97)" }}
      >
        {/* Logo block */}
        <div className="flex flex-col items-center gap-2 mb-8">
          {/* Pulse ring around logo */}
          <div className="relative">
            <div
              className="absolute inset-0 rounded-2xl bg-primary-400 dark:bg-primary-600 opacity-0"
              style={{ animation: "lp-ring-pulse 2.8s ease-in-out infinite" }}
            />
            <div
              className="w-16 h-16 rounded-2xl bg-white dark:bg-[#222120] flex items-center justify-center border border-[#D6CBEC]/60 dark:border-[#383533] overflow-hidden shadow-glow-primary"
              style={{ animation: "lp-logo-bob 6s ease-in-out infinite" }}
            >
              <img src={logo} alt="Mentora logo" className="w-14 h-14 object-contain" />
            </div>
          </div>

          <h1
            className="text-2xl font-black gradient-text"
            style={{ animation: "lp-slide-up 0.55s cubic-bezier(0.16,1,0.3,1) 0.15s both" }}
          >
            Mentora
          </h1>
          <p
            className="text-slate-500 dark:text-slate-400 text-sm"
            style={{ animation: "lp-slide-up 0.55s cubic-bezier(0.16,1,0.3,1) 0.25s both" }}
          >
            Your AI Learning Companion
          </p>
        </div>

        {/* Form card */}
        <div
          className="card p-7 space-y-5"
          style={{ animation: "lp-slide-up 0.6s cubic-bezier(0.16,1,0.3,1) 0.1s both" }}
        >
          {/* Heading */}
          <div>
            <h2
              className="text-xl font-bold text-slate-800 dark:text-slate-100"
              style={{ animation: "lp-slide-up 0.5s cubic-bezier(0.16,1,0.3,1) 0.2s both" }}
            >
              Welcome back
            </h2>
            <p
              className="text-xs text-slate-400 mt-0.5"
              style={{ animation: "lp-slide-up 0.5s cubic-bezier(0.16,1,0.3,1) 0.28s both" }}
            >
              Sign in to continue your learning journey
            </p>
          </div>

          {/* Error */}
          {error && (
            <div
              className="p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-700 rounded-xl text-sm text-danger-600 dark:text-danger-400"
              style={{ animation: "lp-shake 0.4s ease" }}
            >
              {error}
            </div>
          )}

          {resendMsg && (
            <div className="p-3 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-700 rounded-xl text-sm text-success-600 dark:text-success-400">
              {resendMsg}
            </div>
          )}

          {needsVerification && (
            <button id="login-resend-verification" type="button" onClick={handleResend} disabled={isLoading}
              className="w-full text-center text-sm text-primary-600 font-semibold hover:underline">
              {isLoading ? "Sending…" : "Resend confirmation email"}
            </button>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">

            {/* Email */}
            <div style={{ animation: "lp-slide-up 0.5s cubic-bezier(0.16,1,0.3,1) 0.32s both" }}>
              <label htmlFor="login-email" className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 ml-0.5">
                Email or Username
              </label>
              <div
                className="relative rounded-xl transition-all duration-200"
                style={{ boxShadow: focused === "email" ? "0 0 0 3px rgba(111,79,177,0.18)" : "none" }}
              >
                <Mail
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 transition-colors duration-200"
                  style={{ color: focused === "email" ? "#6F4FB1" : "#94a3b8" }}
                />
                <input
                  id="login-email"
                  type="text"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="input pl-10"
                  autoComplete="username"
                  onFocus={() => setFocused("email")}
                  onBlur={() => setFocused(null)}
                />
              </div>
            </div>

            {/* Password */}
            <div style={{ animation: "lp-slide-up 0.5s cubic-bezier(0.16,1,0.3,1) 0.4s both" }}>
              <label htmlFor="login-password" className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 ml-0.5">
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
                  id="login-password"
                  type={showPw ? "text" : "password"}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Your password"
                  className="input pl-10 pr-10"
                  autoComplete="current-password"
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
            </div>

            {/* Forgot */}
            <div
              className="flex justify-end"
              style={{ animation: "lp-slide-up 0.5s cubic-bezier(0.16,1,0.3,1) 0.46s both" }}
            >
              <Link
                to="/forgot-password"
                className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 font-medium transition-colors duration-150"
              >
                Forgot password?
              </Link>
            </div>

            {/* Submit */}
            <div style={{ animation: "lp-slide-up 0.5s cubic-bezier(0.16,1,0.3,1) 0.52s both" }}>
              <button
                id="login-submit"
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
                    : <><LogIn className="w-4 h-4" /> Sign In</>
                  }
                </span>
              </button>
            </div>
          </form>

          {/* Divider */}
          <div
            className="relative flex items-center gap-3"
            style={{ animation: "lp-slide-up 0.5s cubic-bezier(0.16,1,0.3,1) 0.58s both" }}
          >
            <div className="flex-1 h-px bg-[#E7E5E0] dark:bg-[#383533]" />
            <span className="text-xs text-slate-400 dark:text-slate-500">New here?</span>
            <div className="flex-1 h-px bg-[#E7E5E0] dark:bg-[#383533]" />
          </div>

          {/* Sign-up CTA */}
          <p
            className="text-center text-sm text-slate-500"
            style={{ animation: "lp-slide-up 0.5s cubic-bezier(0.16,1,0.3,1) 0.62s both" }}
          >
            No account?{" "}
            <Link to="/register" className="text-primary-600 dark:text-primary-400 font-semibold hover:underline">
              Create one free →
            </Link>
          </p>
        </div>
      </div>

      {/* ── Keyframes ── */}
      <style>{`
        @keyframes lp-slide-up {
          from { opacity: 0; transform: translateY(14px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes lp-float {
          0%, 100% { transform: translateY(0px); }
          50%       { transform: translateY(-22px); }
        }
        @keyframes lp-logo-bob {
          0%, 100% { transform: translateY(0px); }
          50%       { transform: translateY(-5px); }
        }
        @keyframes lp-ring-pulse {
          0%   { opacity: 0;    transform: scale(1);    }
          40%  { opacity: 0.25; transform: scale(1.18); }
          100% { opacity: 0;    transform: scale(1.38); }
        }
        @keyframes lp-shake {
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
