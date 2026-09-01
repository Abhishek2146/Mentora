import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import AppLayout from "@/components/layout/AppLayout";
import {
  Crown,
  Zap,
  CheckCircle2,
  XCircle,
  CalendarClock,
  RefreshCw,
  Loader2,
  AlertCircle,
  CreditCard,
  ExternalLink,
  ShieldCheck,
  Receipt,
  Sparkles,
  Check,
  HelpCircle,
  Star,
  ChevronDown,
  GraduationCap,
} from "lucide-react";
import { subscriptionService } from "@/services/subscriptionService";
import type {
  PlanInfo,
  Subscription as SubscriptionData,
  UsageReport,
  KhaltiConfig,
  PaymentOut,
  BillingCycle,
} from "@/types";

const fmtDate = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "—";

const fmtNPR = (paisa: number) =>
  `Rs. ${(paisa / 100).toLocaleString("en-NP", { maximumFractionDigits: 0 })}`;

const statusBadgeStyle = (s: string) => {
  if (s === "Completed") return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30";
  if (s === "Pending" || s === "Initiated" || s === "INITIATED") return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30";
  if (s === "User canceled" || s === "Expired") return "bg-slate-500/10 text-slate-500 border-slate-500/20";
  return "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20";
};

const faqs = [
  {
    q: "How does Khalti payment work?",
    a: "Mentora integrates with Khalti ePayment gateway. Select your billing cycle (Monthly or Yearly), log in with your Khalti mobile number & MPIN, and authorize the payment. Your Mentora Pro plan activates instantly upon confirmation.",
  },
  {
    q: "Can I upgrade or renew anytime?",
    a: "Yes! You can renew or extend your subscription anytime. Selecting the Yearly plan offers ~16% savings compared to paying monthly.",
  },
  {
    q: "What happens when my plan expires?",
    a: "If your subscription expires, your account automatically reverts to the Mentora Free tier. All your saved flashcards, quizzes, and course data remain completely safe.",
  },
  {
    q: "Are NPR payments secure?",
    a: "Absolutely. All payments are verified server-to-server directly through Khalti's official API in Nepalese Rupees (NPR).",
  },
];

export default function Subscription() {
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [usage, setUsage] = useState<UsageReport | null>(null);
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [khaltiConfig, setKhaltiConfig] = useState<KhaltiConfig | null>(null);
  const [payments, setPayments] = useState<PaymentOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [payingCycle, setPayingCycle] = useState<BillingCycle | null>(null);
  const [payError, setPayError] = useState("");
  const [verifyBanner, setVerifyBanner] = useState<{ type: "success" | "error" | "info"; msg: string } | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [selectedCycle, setSelectedCycle] = useState<BillingCycle>("YEARLY");

  const [searchParams, setSearchParams] = useSearchParams();

  const reload = async () => {
    try {
      const [subRes, usageRes, plansRes, cfgRes, payRes] = await Promise.allSettled([
        subscriptionService.getMySubscription(),
        subscriptionService.getMyUsage(),
        subscriptionService.getPlans(),
        subscriptionService.getKhaltiConfig(),
        subscriptionService.listMyPayments(10),
      ]);
      if (subRes.status === "fulfilled") setSubscription(subRes.value);
      if (usageRes.status === "fulfilled") setUsage(usageRes.value);
      if (plansRes.status === "fulfilled") setPlans(plansRes.value.plans);
      if (cfgRes.status === "fulfilled") setKhaltiConfig(cfgRes.value);
      else setKhaltiConfig({ enabled: false } as any);
      if (payRes.status === "fulfilled") setPayments(payRes.value as PaymentOut[]);
      if (subRes.status === "rejected" && usageRes.status === "rejected") {
        setError("Could not load your subscription details.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    reload();
  }, []);

  useEffect(() => {
    const pidx = searchParams.get("pidx");
    if (!pidx) return;
    let cancelled = false;
    (async () => {
      setVerifying(true);
      setVerifyBanner({ type: "info", msg: "Verifying your Khalti payment…" });
      try {
        const res = await subscriptionService.verifyKhalti(pidx);
        if (cancelled) return;
        if (res.status === "Completed") {
          setVerifyBanner({ type: "success", msg: res.message || "Payment verified — Mentora Pro activated!" });
          await reload();
        } else if (res.status === "Pending" || res.status === "Initiated") {
          setVerifyBanner({ type: "info", msg: res.message });
        } else {
          setVerifyBanner({ type: "error", msg: res.message });
        }
      } catch (e: any) {
        const msg = e?.response?.data?.detail ? JSON.stringify(e.response.data.detail) : e?.message || "Verification failed";
        setVerifyBanner({ type: "error", msg });
      } finally {
        setVerifying(false);
        const clean = new URLSearchParams(searchParams);
        ["pidx", "status", "transaction_id", "tidx", "amount", "total_amount", "mobile", "purchase_order_id", "purchase_order_name"].forEach(k => clean.delete(k));
        setSearchParams(clean, { replace: true });
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const isPro =
    usage?.effective_plan === "SUBSCRIPTION" ||
    (subscription?.plan_type === "SUBSCRIPTION" && subscription?.status === "ACTIVE");
  const isActive = subscription?.status === "ACTIVE";

  const scrollToPlans = () => {
    document.getElementById("pro-plans")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const proPlan = plans.find(p => p.plan_type === "SUBSCRIPTION");
  const monthlyPaisa = proPlan?.price_monthly_paisa ?? khaltiConfig?.prices.monthly_paisa ?? 99900;
  const yearlyPaisa = proPlan?.price_yearly_paisa ?? khaltiConfig?.prices.yearly_paisa ?? 999900;
  const khaltiEnabled = khaltiConfig?.enabled ?? false;

  const handlePay = async (cycle: BillingCycle) => {
    setPayError("");
    setPayingCycle(cycle);
    try {
      const res = await subscriptionService.initiateKhalti(cycle);
      if (!res.payment_url) throw new Error("No payment_url returned");
      sessionStorage.setItem("mentora_last_pidx", res.pidx);
      window.location.href = res.payment_url;
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : e?.message || "Failed to start payment";
      setPayError(msg);
      setPayingCycle(null);
    }
  };

  const handleManualVerify = async () => {
    const last = sessionStorage.getItem("mentora_last_pidx") || payments[0]?.pidx;
    if (!last) {
      setPayError("No recent payment to verify. Try paying again.");
      return;
    }
    setVerifying(true);
    try {
      const res = await subscriptionService.verifyKhalti(last);
      setVerifyBanner({ type: res.status === "Completed" ? "success" : "info", msg: res.message });
      await reload();
    } catch (e: any) {
      setPayError(e?.response?.data?.detail || e?.message || "Verify failed");
    } finally {
      setVerifying(false);
    }
  };

  // Filter out note generation from usage display safely
  const activeUsageFeatures = usage?.features.filter(
    f => (f.usage_type as string) !== "NOTE_GENERATION"
  ) ?? [];

  return (
    <AppLayout title="Subscription">
      <div className="max-w-6xl mx-auto space-y-8 pb-12">
        {/* Error Notification */}
        {error && (
          <div className="rounded-2xl p-4 flex items-center gap-3 bg-danger-50 text-danger-600 dark:bg-danger-900/20 dark:text-danger-400 border border-danger-200 dark:border-danger-800">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm font-medium">{error}</span>
          </div>
        )}

        {/* Verification Banner */}
        {verifyBanner && (
          <div className={`rounded-2xl p-4 flex items-start gap-3.5 text-sm border shadow-sm ${
            verifyBanner.type === "success"
              ? "border-emerald-300 bg-emerald-50 text-emerald-800 dark:bg-emerald-900/30 dark:border-emerald-700 dark:text-emerald-200"
              : verifyBanner.type === "error"
              ? "border-danger-300 bg-danger-50 text-danger-800 dark:bg-danger-900/30 dark:border-danger-700 dark:text-danger-200"
              : "border-amber-300 bg-amber-50 text-amber-800 dark:bg-amber-900/30 dark:border-amber-700 dark:text-amber-200"
          }`}>
            {verifying ? (
              <Loader2 className="w-5 h-5 animate-spin mt-0.5 text-primary-500" />
            ) : verifyBanner.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <AlertCircle className="w-5 h-5 flex-shrink-0 text-amber-600 dark:text-amber-400" />
            )}
            <span className="flex-1 font-medium">{verifyBanner.msg}</span>
            <button onClick={() => setVerifyBanner(null)} className="text-xs font-semibold underline opacity-70 hover:opacity-100">
              Dismiss
            </button>
          </div>
        )}

        {payError && (
          <div className="rounded-2xl p-4 flex items-center gap-3 text-sm text-danger-600 bg-danger-50 border border-danger-200 dark:bg-danger-900/30 dark:border-danger-800 dark:text-danger-300">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="font-medium">{payError}</span>
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 space-y-4">
            <div className="relative">
              <div className="w-12 h-12 rounded-full border-4 border-primary-200 dark:border-primary-900 animate-pulse" />
              <Loader2 className="w-8 h-8 animate-spin text-primary-600 dark:text-primary-400 absolute inset-0 m-auto" />
            </div>
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400 animate-pulse">Loading subscription details…</p>
          </div>
        ) : (
          <>
            {/* HERO BANNER - COMPACT MENTORA BRAND THEME */}
            <div className="relative rounded-2xl overflow-hidden p-5 sm:p-7 bg-gradient-to-r from-primary-600 via-primary-500 to-secondary-500 text-white shadow-glow-primary border border-primary-400/40">
              {/* Background Decorative Elements */}
              <div className="absolute -top-24 -right-24 w-80 h-80 bg-white/10 rounded-full blur-3xl pointer-events-none" />
              <div className="absolute -bottom-24 -left-24 w-80 h-80 bg-secondary-400/30 rounded-full blur-3xl pointer-events-none" />

              <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-5">
                <div className="space-y-2.5 max-w-lg">
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/20 backdrop-blur-md border border-white/30 text-white text-[11px] font-bold tracking-wide uppercase shadow-sm">
                    <GraduationCap className="w-3.5 h-3.5 text-white" /> Mentora Pro Membership
                  </div>
                  <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white leading-tight">
                    Supercharge Your AI Study Workflow
                  </h1>
                  <p className="text-xs sm:text-sm text-primary-50 leading-relaxed">
                    Unlock 10× higher AI response speed, unlimited flashcard sets, priority syllabus processing, and instant AI tutor responses.
                  </p>
                </div>

                {/* CURRENT PLAN DIGITAL PASS (COMPACT) */}
                <div className="w-full md:w-72 rounded-xl p-4 bg-white/15 backdrop-blur-xl border border-white/25 shadow-xl flex flex-col justify-between space-y-3 text-white">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-primary-100">Your Pass</span>
                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${
                      isActive ? "bg-emerald-400/20 text-emerald-200 border-emerald-300/40" : "bg-white/15 text-white border-white/20"
                    }`}>
                      {isActive ? "ACTIVE" : "INACTIVE"}
                    </span>
                  </div>

                  <div className="flex items-center gap-2.5">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center shadow-inner ${
                      isPro ? "bg-gradient-to-br from-amber-300 to-yellow-500 text-slate-950" : "bg-white/20 text-white"
                    }`}>
                      {isPro ? <Crown className="w-5 h-5 fill-current" /> : <Zap className="w-5 h-5" />}
                    </div>
                    <div>
                      <h3 className="text-lg font-black text-white">{isPro ? "Mentora Pro" : "Mentora Free"}</h3>
                      <p className="text-[11px] text-primary-100">
                        {isPro ? `${usage?.rate_limit_per_minute ?? 30} req/min rate limit` : "Standard AI Speed"}
                      </p>
                    </div>
                  </div>

                  {subscription && (
                    <div className="pt-2.5 border-t border-white/20 text-[11px] text-primary-100 space-y-0.5">
                      <div className="flex justify-between">
                        <span>Started:</span>
                        <span className="font-semibold text-white">{fmtDate(subscription.started_at)}</span>
                      </div>
                      {subscription.expires_at && (
                        <div className="flex justify-between">
                          <span>Expires:</span>
                          <span className="font-semibold text-yellow-300">{fmtDate(subscription.expires_at)}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {!isPro && khaltiEnabled && (
                    <button
                      onClick={scrollToPlans}
                      className="w-full py-2 px-3 rounded-lg bg-white text-primary-700 hover:bg-yellow-100 font-extrabold text-xs shadow-md flex items-center justify-center gap-1.5 transition-all hover:scale-[1.02] active:scale-[0.98]"
                    >
                      <Crown className="w-3.5 h-3.5 text-amber-500 fill-current" /> Upgrade to Pro Now
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* DAILY USAGE SUMMARY (EXCLUDING NOTE GENERATION) */}
            {usage && activeUsageFeatures.length > 0 && (
              <div className="rounded-3xl p-6 sm:p-8 bg-surface dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-soft space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-4">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-xl bg-primary-500/10 text-primary-600 dark:text-primary-400">
                      <Zap className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-bold text-lg text-slate-900 dark:text-white">Today&apos;s Daily AI Quota</h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400">Resets automatically at midnight UTC ({usage.usage_date})</p>
                    </div>
                  </div>
                  <span className="text-xs font-semibold px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                    Plan: {isPro ? "Mentora Pro" : "Free Tier"}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {activeUsageFeatures.map(f => {
                    const pct = f.daily_limit > 0 ? Math.min(100, Math.round((f.used / f.daily_limit) * 100)) : 0;
                    const label = subscriptionService.featureLabel(f.usage_type);
                    return (
                      <div key={f.usage_type} className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 space-y-3">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-slate-700 dark:text-slate-300 truncate">{label}</span>
                          <span className={`font-bold ${pct >= 100 ? "text-danger-500" : "text-primary-600 dark:text-primary-400"}`}>
                            {f.used}/{f.daily_limit}
                          </span>
                        </div>
                        <div className="w-full bg-slate-200 dark:bg-slate-700 h-2.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${
                              pct >= 100
                                ? "bg-danger-500"
                                : pct >= 80
                                ? "bg-amber-500"
                                : "bg-gradient-to-r from-primary-500 to-secondary-500"
                            }`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-[11px] text-slate-400">
                          <span>{pct}% Used</span>
                          <span>{f.daily_limit - f.used} remaining</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* BILLING CYCLE SELECTOR */}
            <div id="pro-plans" className="text-center space-y-4 pt-4">
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-primary-50 dark:bg-primary-950/50 border border-primary-200 dark:border-primary-800 text-primary-600 dark:text-primary-300 text-xs font-bold">
                <Crown className="w-3.5 h-3.5" /> Choose Your Plan
              </div>
              <h2 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">
                Simple, Transparent Pricing
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                No hidden fees. Instant access to all Mentora Pro AI features powered by secure Khalti wallet.
              </p>

              {/* Cycle Toggle Pill */}
              <div className="inline-flex items-center p-1.5 rounded-2xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-inner mt-2">
                <button
                  type="button"
                  onClick={() => setSelectedCycle("MONTHLY")}
                  className={`px-5 py-2 rounded-xl text-xs font-bold transition-all ${
                    selectedCycle === "MONTHLY"
                      ? "bg-surface dark:bg-slate-900 text-slate-900 dark:text-white shadow-md"
                      : "text-slate-500 hover:text-slate-900 dark:hover:text-white"
                  }`}
                >
                  Monthly Billing
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedCycle("YEARLY")}
                  className={`px-5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                    selectedCycle === "YEARLY"
                      ? "bg-gradient-to-r from-primary-600 to-secondary-600 text-white shadow-md"
                      : "text-slate-500 hover:text-slate-900 dark:hover:text-white"
                  }`}
                >
                  <span>Yearly Billing</span>
                  <span className="px-1.5 py-0.5 text-[10px] uppercase tracking-wider rounded-md bg-amber-400 text-slate-950 font-black">
                    Save 16%
                  </span>
                </button>
              </div>
            </div>

            {/* PRICING CARDS GRID */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8 max-w-4xl mx-auto">
              {/* FREE CARD */}
              <div className="rounded-3xl p-6 sm:p-8 bg-surface dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-soft flex flex-col justify-between space-y-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                      Standard Tier
                    </span>
                  </div>
                  <div>
                    <h3 className="text-2xl font-black text-slate-900 dark:text-white">Mentora Free</h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Essential tools for casual studying</p>
                  </div>

                  <div className="py-2">
                    <span className="text-3xl font-black text-slate-900 dark:text-white">Rs. 0</span>
                    <span className="text-xs text-slate-400 font-medium"> / forever</span>
                  </div>

                  <hr className="border-slate-100 dark:border-slate-800" />

                  <ul className="space-y-3 text-xs sm:text-sm text-slate-600 dark:text-slate-300">
                    <li className="flex items-center gap-2.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                      <span><strong>3 requests</strong> per minute</span>
                    </li>
                    <li className="flex items-center gap-2.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                      <span><strong>5 AI Tutor</strong> messages / day</span>
                    </li>
                    <li className="flex items-center gap-2.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                      <span><strong>3 Flashcards & Quizzes</strong> / day</span>
                    </li>
                    <li className="flex items-center gap-2.5 text-slate-400">
                      <XCircle className="w-4 h-4 text-slate-300 dark:text-slate-600 flex-shrink-0" />
                      <span>Priority AI processing</span>
                    </li>
                  </ul>
                </div>

                <div className="pt-4">
                  <div className="w-full py-3 px-4 rounded-2xl bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-center font-bold text-xs">
                    {isPro ? "Included in your account" : "Current Basic Plan"}
                  </div>
                </div>
              </div>

              {/* PRO CARD */}
              <div className="relative rounded-3xl p-6 sm:p-8 bg-surface dark:bg-slate-900 border-2 border-primary-500 dark:border-primary-400 shadow-glow-primary flex flex-col justify-between space-y-6">
                {/* Popular Badge */}
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-gradient-to-r from-primary-600 to-secondary-600 text-white text-xs font-black tracking-wider uppercase shadow-md flex items-center gap-1">
                  <Star className="w-3 h-3 fill-current text-yellow-300" /> Recommended for Students
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between pt-1">
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-primary-100 dark:bg-primary-950 text-primary-600 dark:text-primary-300 border border-primary-200 dark:border-primary-800 flex items-center gap-1">
                      <Crown className="w-3 h-3 text-amber-500 fill-current" /> Mentora Pro
                    </span>
                    {selectedCycle === "YEARLY" && (
                      <span className="text-[11px] font-extrabold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950 px-2.5 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-800">
                        Best Value
                      </span>
                    )}
                  </div>

                  <div>
                    <h3 className="text-2xl font-black text-slate-900 dark:text-white flex items-center gap-2">
                      Mentora Pro
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Unlimited study workflow & top AI speed</p>
                  </div>

                  <div className="py-2">
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl font-black text-slate-900 dark:text-white">
                        {selectedCycle === "YEARLY" ? fmtNPR(yearlyPaisa) : fmtNPR(monthlyPaisa)}
                      </span>
                      <span className="text-xs text-slate-500 font-semibold">
                        {selectedCycle === "YEARLY" ? " / year" : " / month"}
                      </span>
                    </div>
                    {selectedCycle === "YEARLY" && (
                      <p className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium mt-0.5">
                        Equivalent to ~{fmtNPR(Math.round(yearlyPaisa / 12))} / month (~16% discount)
                      </p>
                    )}
                  </div>

                  <hr className="border-slate-100 dark:border-slate-800" />

                  <ul className="space-y-3 text-xs sm:text-sm text-slate-700 dark:text-slate-200">
                    <li className="flex items-center gap-2.5">
                      <div className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center flex-shrink-0">
                        <Check className="w-3 h-3 stroke-[3]" />
                      </div>
                      <span><strong>30 requests</strong> per minute (10× Speed)</span>
                    </li>
                    <li className="flex items-center gap-2.5">
                      <div className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center flex-shrink-0">
                        <Check className="w-3 h-3 stroke-[3]" />
                      </div>
                      <span><strong>50 AI Tutor</strong> messages / day</span>
                    </li>
                    <li className="flex items-center gap-2.5">
                      <div className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center flex-shrink-0">
                        <Check className="w-3 h-3 stroke-[3]" />
                      </div>
                      <span><strong>30 Flashcards & Quizzes</strong> / day</span>
                    </li>
                    <li className="flex items-center gap-2.5">
                      <div className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center flex-shrink-0">
                        <Check className="w-3 h-3 stroke-[3]" />
                      </div>
                      <span><strong>Full Syllabus</strong> AI breakdown & plan</span>
                    </li>
                    <li className="flex items-center gap-2.5">
                      <div className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center flex-shrink-0">
                        <Check className="w-3 h-3 stroke-[3]" />
                      </div>
                      <span><strong>Khalti ePayment</strong> instant NPR activation</span>
                    </li>
                  </ul>
                </div>

                {/* KHALTI PAYMENT BUTTONS */}
                <div className="space-y-3 pt-2">
                  {!khaltiEnabled ? (
                    <div className="rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 p-3.5 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2.5">
                      <ShieldCheck className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-600" />
                      <span>Online payments are currently in maintenance. Contact administrator to configure <code className="bg-white/50 dark:bg-black/40 px-1 py-0.5 rounded">KHALTI_SECRET_KEY</code>.</span>
                    </div>
                  ) : (
                    <>
                      <button
                        onClick={() => handlePay(selectedCycle)}
                        disabled={!!payingCycle || verifying}
                        className="w-full py-3.5 px-5 rounded-2xl bg-gradient-to-r from-[#5C2D91] via-[#6d35a8] to-[#4a2575] hover:from-[#4a2575] hover:to-[#381b59] text-white font-black text-sm shadow-xl shadow-purple-900/20 flex items-center justify-center gap-2.5 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60"
                      >
                        {payingCycle === selectedCycle ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          <CreditCard className="w-5 h-5" />
                        )}
                        <span>Pay {selectedCycle === "YEARLY" ? fmtNPR(yearlyPaisa) : fmtNPR(monthlyPaisa)} with Khalti</span>
                      </button>

                      <div className="flex items-center justify-between text-[11px] text-slate-400 px-1 pt-1">
                        <span className="flex items-center gap-1">
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" /> 100% Khalti Secure
                        </span>
                        <button
                          onClick={handleManualVerify}
                          disabled={verifying}
                          className="text-primary-600 dark:text-primary-400 font-bold hover:underline disabled:opacity-50"
                        >
                          {verifying ? "Verifying…" : "Verify Payment"}
                        </button>
                      </div>
                    </>
                  )}

                  {/* Sandbox test credentials dropdown */}
                  <details className="text-xs text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/70 rounded-xl p-3 border border-slate-200/60 dark:border-slate-700/60">
                    <summary className="cursor-pointer font-bold text-slate-700 dark:text-slate-300 flex items-center justify-between">
                      <span>Khalti Sandbox Credentials</span>
                      <ChevronDown className="w-3.5 h-3.5" />
                    </summary>
                    <ul className="mt-2 space-y-1 font-mono text-[11px] text-slate-600 dark:text-slate-300">
                      <li>Mobile: 9800000000</li>
                      <li>MPIN: 1111</li>
                      <li>OTP: 987654</li>
                    </ul>
                  </details>
                </div>
              </div>
            </div>

            {/* WHY PRO FEATURE HIGHLIGHTS */}
            <div className="rounded-3xl p-6 sm:p-10 bg-gradient-to-br from-primary-900/10 via-surface to-secondary-900/10 dark:from-primary-950/40 dark:via-slate-900 dark:to-secondary-950/40 border border-slate-200 dark:border-slate-800 shadow-soft space-y-6">
              <div className="text-center space-y-2 max-w-xl mx-auto">
                <h3 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white">Why Upgrade to Mentora Pro?</h3>
                <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">Built specifically for students preparing for competitive exams, board tests, and complex university courses.</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-5 pt-2">
                <div className="p-5 rounded-2xl bg-surface dark:bg-slate-800/80 border border-slate-100 dark:border-slate-700 space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-primary-500/10 text-primary-600 dark:text-primary-400 flex items-center justify-center font-bold">
                    <Zap className="w-5 h-5" />
                  </div>
                  <h4 className="font-bold text-sm text-slate-900 dark:text-white">10× AI Response Speed</h4>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Enjoy 30 requests per minute for instant multi-subject tutoring and quiz generation.</p>
                </div>

                <div className="p-5 rounded-2xl bg-surface dark:bg-slate-800/80 border border-slate-100 dark:border-slate-700 space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-secondary-500/10 text-secondary-600 dark:text-secondary-400 flex items-center justify-center font-bold">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <h4 className="font-bold text-sm text-slate-900 dark:text-white">Full Course Syllabus AI</h4>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Upload your PDF/DOCX course outlines and receive step-by-step topic timelines.</p>
                </div>

                <div className="p-5 rounded-2xl bg-surface dark:bg-slate-800/80 border border-slate-100 dark:border-slate-700 space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold">
                    <Crown className="w-5 h-5" />
                  </div>
                  <h4 className="font-bold text-sm text-slate-900 dark:text-white">30× Daily Limits</h4>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Generate up to 30 flashcards and quizzes every single day.</p>
                </div>

                <div className="p-5 rounded-2xl bg-surface dark:bg-slate-800/80 border border-slate-100 dark:border-slate-700 space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center font-bold">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <h4 className="font-bold text-sm text-slate-900 dark:text-white">Khalti Wallet NPR</h4>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Pay conveniently in NPR using Khalti with instant server verification.</p>
                </div>
              </div>
            </div>

            {/* RECENT KHALTI PAYMENTS TABLE */}
            {payments.length > 0 && (
              <div className="rounded-3xl p-6 sm:p-8 bg-surface dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-soft space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                  <h3 className="font-bold text-lg text-slate-900 dark:text-white flex items-center gap-2">
                    <Receipt className="w-5 h-5 text-primary-500" />
                    Payment History
                  </h3>
                  <button
                    onClick={reload}
                    className="text-xs text-slate-500 hover:text-slate-900 dark:hover:text-white font-semibold flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 transition-colors"
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Refresh
                  </button>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-xs text-slate-400 border-b border-slate-100 dark:border-slate-800">
                        <th className="text-left py-3 px-3 font-semibold">Date</th>
                        <th className="text-left py-3 px-3 font-semibold">Cycle</th>
                        <th className="text-left py-3 px-3 font-semibold">Amount</th>
                        <th className="text-left py-3 px-3 font-semibold">Status</th>
                        <th className="text-left py-3 px-3 font-semibold">Transaction ID</th>
                        <th className="text-right py-3 px-3 font-semibold">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                      {payments.map(p => (
                        <tr key={p.pidx} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                          <td className="py-3 px-3 text-slate-500 font-medium">
                            {p.created_at ? new Date(p.created_at).toLocaleString() : "—"}
                          </td>
                          <td className="py-3 px-3 font-bold text-slate-800 dark:text-slate-200">{p.billing_cycle}</td>
                          <td className="py-3 px-3 font-black text-slate-900 dark:text-white">{fmtNPR(p.amount)}</td>
                          <td className="py-3 px-3">
                            <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold border ${statusBadgeStyle(p.status)}`}>
                              {p.status}
                            </span>
                          </td>
                          <td className="py-3 px-3 font-mono text-slate-400 truncate max-w-[130px]" title={p.pidx}>
                            {p.pidx}
                          </td>
                          <td className="py-3 px-3 text-right">
                            <div className="flex items-center justify-end gap-2">
                              {p.payment_url && p.status !== "Completed" && (
                                <a
                                  href={p.payment_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="px-2.5 py-1 rounded-lg bg-purple-50 dark:bg-purple-950 text-purple-600 dark:text-purple-300 font-bold hover:underline flex items-center gap-1"
                                >
                                  Retry <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                              <button
                                onClick={async () => {
                                  setVerifying(true);
                                  try {
                                    const r = await subscriptionService.verifyKhalti(p.pidx);
                                    setVerifyBanner({ type: r.status === "Completed" ? "success" : "info", msg: r.message });
                                    await reload();
                                  } finally {
                                    setVerifying(false);
                                  }
                                }}
                                disabled={verifying}
                                className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-bold hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
                              >
                                Verify
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* FREQUENTLY ASKED QUESTIONS */}
            <div className="rounded-3xl p-6 sm:p-8 bg-surface dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-soft space-y-4">
              <h3 className="font-bold text-lg text-slate-900 dark:text-white flex items-center gap-2">
                <HelpCircle className="w-5 h-5 text-primary-500" />
                Frequently Asked Questions
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {faqs.map((faq, idx) => (
                  <div key={idx} className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800 space-y-1.5">
                    <h4 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-primary-500" />
                      {faq.q}
                    </h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed pl-4">{faq.a}</p>
                  </div>
                ))}
              </div>
            </div>

            <p className="text-xs text-center text-slate-400 pt-2">
              Payments are verified server-to-server via Khalti lookup API. Only <span className="font-semibold text-slate-600 dark:text-slate-300">Completed</span> payments activate Mentora Pro · <a href="https://docs.khalti.com/khalti-epayment/" target="_blank" rel="noreferrer" className="underline hover:text-slate-600 dark:hover:text-slate-200">Khalti Documentation</a>
            </p>
          </>
        )}
      </div>
    </AppLayout>
  );
}
