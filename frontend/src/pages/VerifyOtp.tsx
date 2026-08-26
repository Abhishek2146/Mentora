import { useState, useRef } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { GraduationCap, ShieldCheck, ArrowLeft, AlertCircle } from "lucide-react";

export default function VerifyOtp() {
  const location = useLocation();
  const navigate = useNavigate();
  const email =
    (location.state as { email?: string } | null)?.email ||
    new URLSearchParams(location.search).get("email") ||
    "";

  const [digits, setDigits] = useState<string[]>(Array(6).fill(""));
  const [error, setError] = useState("");
  const [resendMessage, setResendMessage] = useState(false);
  const inputsRef = useRef<(HTMLInputElement | null)[]>([]);

  const handleChange = (index: number, value: string) => {
    const char = value.replace(/\D/g, "").slice(-1);
    const next = [...digits];
    next[index] = char;
    setDigits(next);
    setError("");
    if (char && index < 5) {
      inputsRef.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !digits[index] && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (!pasted) return;
    const next = Array(6).fill("");
    pasted.split("").forEach((char, i) => (next[i] = char));
    setDigits(next);
    inputsRef.current[Math.min(pasted.length, 5)]?.focus();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const otp = digits.join("");
    if (otp.length !== 6) {
      setError("Please enter all 6 digits of the OTP");
      return;
    }

    // Frontend-only flow: accept the OTP and continue to set a new password.
    navigate("/set-new-password", { state: { email, otp } });
  };

  const handleResend = () => {
    setDigits(Array(6).fill(""));
    setResendMessage(true);
    setTimeout(() => setResendMessage(false), 3000);
  };

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
          <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Verify OTP</h2>
          <p className="text-sm text-slate-500">
            Enter the 6-digit code sent to{" "}
            <strong>{email || "your email"}</strong>
          </p>

          {error && (
            <div className="p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-700 rounded-xl text-sm text-danger-600 dark:text-danger-400 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {resendMessage && (
            <div className="p-3 bg-primary-50 dark:bg-primary-900/20 border border-primary-200 rounded-xl text-sm text-primary-600">
              A new OTP has been sent
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="flex justify-between gap-2" onPaste={handlePaste}>
              {digits.map((digit, i) => (
                <input
                  key={i}
                  ref={(el) => { inputsRef.current[i] = el; }}
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={digit}
                  onChange={(e) => handleChange(i, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(i, e)}
                  className="input w-full h-12 text-center text-lg font-bold px-0"
                  aria-label={`Digit ${i + 1}`}
                />
              ))}
            </div>

            <button type="submit" className="btn-primary btn-md w-full">
              <ShieldCheck className="w-4 h-4" /> Verify OTP
            </button>
          </form>

          <p className="text-center text-sm text-slate-500">
            Didn't receive the code?{" "}
            <button
              type="button"
              onClick={handleResend}
              className="text-primary-600 font-semibold hover:underline"
            >
              Resend OTP
            </button>
          </p>

          <Link
            to="/forgot-password"
            className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 justify-center"
          >
            <ArrowLeft className="w-4 h-4" /> Back
          </Link>
        </div>
      </div>
    </div>
  );
}
