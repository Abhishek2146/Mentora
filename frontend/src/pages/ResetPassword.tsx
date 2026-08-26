import { useState, useEffect } from "react";
import { useSearchParams, Link, useNavigate } from "react-router-dom";
import { GraduationCap, Lock, Eye, EyeOff, CheckCircle2, AlertCircle } from "lucide-react";
import { useAuthStore } from "@/store/authStore";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const { resetPassword, isLoading } = useAuthStore();

  useEffect(() => {
    if (!token) {
      setError("Invalid or missing reset token");
    }
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!token) {
      setError("Invalid reset token");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    try {
      await resetPassword(token, password);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset password. Please try again.");
    }
  };

  if (!token && !error) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-primary-50 to-secondary-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center">
            <GraduationCap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-black gradient-text">Mentora</h1>
        </div>

        <div className="card p-7 space-y-5">
          {success ? (
            <div className="flex flex-col items-center gap-4 text-center py-4">
              <CheckCircle2 className="w-12 h-12 text-success-500" />
              <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Password Reset</h2>
              <p className="text-sm text-slate-500">Your password has been reset successfully</p>
              <Link to="/login" className="btn-primary btn-md w-full">Sign In</Link>
            </div>
          ) : (
            <>
              {error && (
                <div className="p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-700 rounded-xl text-sm text-danger-600 dark:text-danger-400 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}
              {!error && (
                <>
                  <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Set New Password</h2>
                  <p className="text-sm text-slate-500">Enter your new password below</p>
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <input
                        id="reset-password"
                        type={showPw ? "text" : "password"}
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        placeholder="New password"
                        className="input pl-10 pr-10"
                        required
                        autoComplete="new-password"
                      />
                      <button type="button" onClick={() => setShowPw(!showPw)}
                        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors">
                        {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <input
                        id="reset-confirm-password"
                        type={showPw ? "text" : "password"}
                        value={confirmPassword}
                        onChange={e => setConfirmPassword(e.target.value)}
                        placeholder="Confirm new password"
                        className="input pl-10 pr-10"
                        required
                        autoComplete="new-password"
                      />
                    </div>
                    <button type="submit" disabled={isLoading} className="btn-primary btn-md w-full">
                      {isLoading ? (
                        <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                      ) : (
                        'Reset Password'
                      )}
                    </button>
                  </form>
                  <Link to="/login" className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 justify-center">
                    Back to login
                  </Link>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}