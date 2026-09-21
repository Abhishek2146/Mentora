import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { GraduationCap, MailCheck, MailX } from "lucide-react";
import { useAuthStore } from "@/store/authStore";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const { verifyEmail, isLoading } = useAuthStore();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setStatus("error");
      setError("Missing verification token in the URL.");
      return;
    }
    (async () => {
      try {
        await verifyEmail(token);
        setStatus("success");
      } catch (err) {
        setStatus("error");
        setError(err instanceof Error ? err.message : "Failed to verify your email.");
      }
    })();
  }, [searchParams, verifyEmail]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-primary-50 to-secondary-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className={`w-14 h-14 rounded-2xl flex items-center justify-center shadow-glow-primary ${
            status === "success" ? "bg-gradient-to-br from-emerald-500 to-teal-500" : "bg-gradient-to-br from-primary-500 to-secondary-500"
          }`}>
            {status === "loading" && <span className="w-7 h-7 border-2 border-white/40 border-t-white rounded-full animate-spin" />}
            {status === "success" && <MailCheck className="w-8 h-8 text-white" />}
            {status === "error" && <MailX className="w-8 h-8 text-white" />}
          </div>
          <h1 className="text-2xl font-black gradient-text">Mentora</h1>
        </div>

        <div className="card p-7 space-y-5">
          {status === "loading" && (
            <p className="text-sm text-slate-600 dark:text-slate-300 text-center">Confirming your email address…</p>
          )}

          {status === "success" && (
            <>
              <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 text-center">Email verified</h2>
              <p className="text-sm text-slate-600 dark:text-slate-300 text-center">
                Your account is now active. You can sign in and start learning.
              </p>
              <Link to="/login" id="verify-email-login" className="btn-primary btn-md w-full inline-flex items-center justify-center">
                Sign in
              </Link>
            </>
          )}

          {status === "error" && (
            <>
              <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 text-center">Couldn't verify email</h2>
              <p className="text-sm text-danger-600 text-center">{error}</p>
              <p className="text-sm text-slate-500 text-center">
                The link may have expired. Try asking for a new confirmation email.
              </p>
              <Link to="/forgot-password" className="btn-primary btn-md w-full inline-flex items-center justify-center">
                Go to login
              </Link>
            </>
          )}

          {!isLoading && status !== "loading" && (
            <p className="text-center text-sm text-slate-500">
              <Link to="/login" className="text-primary-600 font-semibold hover:underline">Back to login</Link>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}