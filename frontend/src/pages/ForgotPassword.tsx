import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { GraduationCap, Mail, ArrowLeft, AlertCircle, CheckCircle2, ShieldCheck } from "lucide-react";
import { useAuthStore } from "@/store/authStore";

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const { forgotPassword, isLoading } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await forgotPassword(email);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send reset email");
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-primary-50 to-secondary-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 flex items-center justify-center p-4">
        <div className="w-full max-w-sm">
          <div className="flex flex-col items-center gap-3 mb-8">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center">
              <GraduationCap className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-black gradient-text">Mentora</h1>
          </div>

          <div className="card p-7 space-y-5 text-center">
            <CheckCircle2 className="w-12 h-12 text-success-500 mx-auto" />
            <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Check your email</h2>
            <p className="text-sm text-slate-500">
              If an account exists for <strong>{email}</strong>, we’ve sent a reset link and a 6-digit OTP.
            </p>
            <div className="bg-slate-50 dark:bg-slate-800 rounded-xl p-4 text-left text-xs space-y-2 border">
              <p className="font-semibold flex items-center gap-1.5"><Mail className="w-3.5 h-3.5" /> Option 1 — Reset link (1 hour):</p>
              <p className="text-slate-500">Click the link in the email to set a new password directly.</p>
              <p className="font-semibold flex items-center gap-1.5"><ShieldCheck className="w-3.5 h-3.5" /> Option 2 — OTP (10 min):</p>
              <p className="text-slate-500">Enter the 6-digit OTP from the same email on the next page.</p>
            </div>
            <p className="text-xs text-slate-400">Didn’t receive it? Check spam or resend. In development, the link/OTP is also logged in the backend console.</p>
            <div className="flex flex-col gap-2">
              <button onClick={() => navigate(`/verify-otp?email=${encodeURIComponent(email)}`)} className="btn-primary btn-md w-full">
                Enter OTP
              </button>
              <button onClick={() => setSuccess(false)} className="btn-ghost btn-md w-full text-sm">
                Resend email
              </button>
              <Link to="/login" className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 justify-center">
                <ArrowLeft className="w-4 h-4" /> Back to login
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

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
          <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Reset Password</h2>
          <p className="text-sm text-slate-500">Enter your email to receive a reset link and OTP</p>
          {error && (
            <div className="p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-700 rounded-xl text-sm text-danger-600 dark:text-danger-400 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                placeholder="Your email address" className="input pl-10" required />
            </div>
            <button type="submit" disabled={isLoading} className="btn-primary btn-md w-full">
              {isLoading ? (
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              ) : (
                'Send Reset Link'
              )}
            </button>
          </form>
          <Link to="/login" className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 justify-center">
            <ArrowLeft className="w-4 h-4" /> Back to login
          </Link>
        </div>
      </div>
    </div>
  );
}
