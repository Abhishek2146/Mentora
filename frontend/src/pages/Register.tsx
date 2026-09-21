import { useState } from "react";
import { Link } from "react-router-dom";
import { GraduationCap, Mail, Lock, User, Eye, EyeOff, UserPlus, MailCheck } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { isGmailAddress } from "@/lib/emailValidation";

export default function Register() {
  const { register, resendVerification, isLoading } = useAuthStore();
  const [form, setForm] = useState({ full_name: "", email: "", username: "", password: "" });
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);
  const [resendMsg, setResendMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!isGmailAddress(form.email)) {
      setError("Please enter a valid Gmail address ending in @gmail.com.");
      return;
    }
    try {
      await register(form);
      setRegisteredEmail(form.email);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed. Please try again.");
    }
  };

  const handleResend = async () => {
    if (!registeredEmail) return;
    setError("");
    setResendMsg("");
    try {
      await resendVerification(registeredEmail);
      setResendMsg("A new confirmation email has been sent. Please check your inbox.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resend verification email.");
    }
  };

  const f = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm(p => ({ ...p, [k]: e.target.value }));

  const emailInvalid = form.email.length > 0 && !isGmailAddress(form.email);

  if (registeredEmail) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-primary-50 to-secondary-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 flex items-center justify-center p-4">
        <div className="w-full max-w-sm">
          <div className="flex flex-col items-center gap-3 mb-8">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center shadow-glow-primary">
              <MailCheck className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-black gradient-text">Check your email</h1>
            <p className="text-slate-500 text-sm text-center">
              We sent a confirmation link to<br /><strong>{registeredEmail}</strong>
            </p>
          </div>

          <div className="card p-7 space-y-5 text-center">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Click the <strong>Confirm Email</strong> button in the email we just sent.
              Your account is only activated after you confirm it.
            </p>

            {error && <div className="p-3 bg-danger-50 border border-danger-200 rounded-xl text-sm text-danger-600">{error}</div>}
            {resendMsg && <div className="p-3 bg-success-50 border border-success-200 rounded-xl text-sm text-success-600">{resendMsg}</div>}

            <button id="register-resend" onClick={handleResend} disabled={isLoading} className="btn-primary btn-md w-full">
              {isLoading ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : "Resend confirmation email"}
            </button>

            <p className="text-center text-sm text-slate-500">
              Already confirmed? <Link to="/login" className="text-primary-600 font-semibold hover:underline">Sign in</Link>
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-primary-50 to-secondary-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center shadow-glow-primary">
            <GraduationCap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-black gradient-text">Mentora</h1>
          <p className="text-slate-500 text-sm">Create your account</p>
        </div>

        <div className="card p-7 space-y-5">
          <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Get started</h2>

          {error && <div className="p-3 bg-danger-50 border border-danger-200 rounded-xl text-sm text-danger-600">{error}</div>}

          <form onSubmit={handleSubmit} className="space-y-4">
            {[
              { key: "full_name", icon: User, placeholder: "Full name", type: "text" },
              { key: "username", icon: User, placeholder: "Username", type: "text" },
            ].map(field => (
              <div key={field.key} className="relative">
                <field.icon className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input type={field.type} value={form[field.key as keyof typeof form]}
                  onChange={f(field.key)} placeholder={field.placeholder}
                  id={`register-${field.key}`}
                  className="input pl-10" required />
              </div>
            ))}
            <div className="space-y-1">
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="email"
                  value={form.email}
                  onChange={f("email")}
                  placeholder="name@gmail.com"
                  id="register-email"
                  className={`input pl-10${emailInvalid ? " !border-danger-500 focus:!ring-danger-500/20" : ""}`}
                  required />
              </div>
              {emailInvalid && (
                <p className="text-xs text-danger-600">Use a valid Gmail address ending in @gmail.com.</p>
              )}
            </div>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input id="register-password" type={showPw ? "text" : "password"} value={form.password} onChange={f("password")}
                placeholder="Password" className="input pl-10 pr-10" required />
              <button type="button" onClick={() => setShowPw(!showPw)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400">
                {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <button id="register-submit" type="submit" disabled={isLoading} className="btn-primary btn-md w-full">
              {isLoading ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : <><UserPlus className="w-4 h-4" /> Create Account</>}
            </button>
            <p className="text-center text-xs text-slate-400">
              A confirmation email will be sent to your address. Your account activates after you confirm it.
            </p>
          </form>
          <p className="text-center text-sm text-slate-500">
            Have an account? <Link to="/login" className="text-primary-600 font-semibold hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}