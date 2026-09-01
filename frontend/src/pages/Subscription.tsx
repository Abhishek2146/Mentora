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

const statusColor = (s: string) => {
  if (s === "Completed") return "text-success-600 bg-success-50 dark:bg-success-900/20";
  if (s === "Pending" || s === "Initiated" || s === "INITIATED") return "text-amber-600 bg-amber-50";
  if (s === "User canceled" || s === "Expired") return "text-slate-500 bg-slate-100";
  return "text-slate-600 bg-slate-100";
};

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

  // Initial load
  useEffect(() => {
    reload();
  }, []);

  // Handle Khalti return_url redirect: ?pidx=...&status=Completed&...
  useEffect(() => {
    const pidx = searchParams.get("pidx");
    if (!pidx) return;
    // Prevent double-verify on remount after we cleared params.
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
        // Clean URL without pidx to avoid re-trigger on refresh.
        const clean = new URLSearchParams(searchParams);
        ["pidx", "status", "transaction_id", "tidx", "amount", "total_amount", "mobile", "purchase_order_id", "purchase_order_name"].forEach(k => clean.delete(k));
        setSearchParams(clean, { replace: true });
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      // Persist pidx for manual re-verify fallback.
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

  return (
    <AppLayout title="Subscription">
      <div className="max-w-5xl mx-auto space-y-6">
        {error && (
          <div className="card p-4 flex items-center gap-2 text-sm text-danger-600 dark:text-danger-400">
            <AlertCircle className="w-4 h-4" /> {error}
          </div>
        )}

        {/* Khalti verification banner */}
        {verifyBanner && (
          <div className={`card p-4 flex items-start gap-3 text-sm border ${verifyBanner.type === "success" ? "border-success-200 bg-success-50 text-success-700" : verifyBanner.type === "error" ? "border-danger-200 bg-danger-50 text-danger-700" : "border-amber-200 bg-amber-50 text-amber-700"}`}>
            {verifying ? <Loader2 className="w-4 h-4 animate-spin mt-0.5" /> : verifyBanner.type === "success" ? <CheckCircle2 className="w-5 h-5 flex-shrink-0" /> : <AlertCircle className="w-5 h-5 flex-shrink-0" />}
            <span className="flex-1">{verifyBanner.msg}</span>
            <button onClick={() => setVerifyBanner(null)} className="text-xs underline opacity-70">Dismiss</button>
          </div>
        )}
        {payError && (
          <div className="card p-4 flex items-center gap-2 text-sm text-danger-600 bg-danger-50 border border-danger-200">
            <AlertCircle className="w-4 h-4" /> {payError}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="w-7 h-7 animate-spin text-primary-500" />
          </div>
        ) : (
          <>
            {/* ---------- Current plan ---------- */}
            <div
              className={`card p-6 border-0 text-white ${isPro ? "bg-gradient-to-r from-primary-600 to-secondary-600" : "bg-gradient-to-r from-slate-700 to-slate-800"}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${isPro ? "bg-white/15" : "bg-white/10"}`}>
                    {isPro ? <Crown className="w-7 h-7 text-yellow-300" /> : <Zap className="w-7 h-7 text-slate-300" />}
                  </div>
                  <div>
                    <p className="text-sm opacity-80">Current Plan</p>
                    <h2 className="text-2xl font-black">{isPro ? "Mentora Pro" : "Mentora Free"}</h2>
                    <div className="flex flex-wrap items-center gap-2 mt-1 text-xs opacity-90">
                      <span className={`badge ${isActive ? "bg-success-500 text-white" : "bg-danger-500 text-white"}`}>
                        {isActive ? <><CheckCircle2 className="w-3 h-3 mr-1" />{subscription?.status ?? "ACTIVE"}</> : <><XCircle className="w-3 h-3 mr-1" />{subscription?.status ?? "INACTIVE"}</>}
                      </span>
                      {subscription && (
                        <span className="badge bg-white/15 text-white">
                          {subscription.plan_type}
                          {subscription.billing_cycle !== "NONE" && ` · ${subscription.billing_cycle}`}
                        </span>
                      )}
                      {isPro && usage && (
                        <span className="badge bg-white/15 text-white">
                          <Zap className="w-3 h-3 mr-1" />
                          {usage.rate_limit_per_minute} req/min
                        </span>
                      )}
                    </div>
                    {!isPro && khaltiEnabled && (
                      <button onClick={scrollToPlans} className="mt-3 text-xs bg-white text-slate-800 font-bold px-3 py-1.5 rounded-full hover:bg-yellow-100 transition-colors flex items-center gap-1.5">
                        <Crown className="w-3.5 h-3.5" /> Upgrade to Pro →
                      </button>
                    )}
                  </div>
                </div>

                {subscription && (
                  <div className="text-sm space-y-1 opacity-90">
                    <p className="flex items-center gap-2">
                      <CalendarClock className="w-4 h-4" />
                      Started {fmtDate(subscription.started_at)}
                    </p>
                    {subscription.expires_at && (
                      <p className="flex items-center gap-2">
                        <CalendarClock className="w-4 h-4" />
                        Expires {fmtDate(subscription.expires_at)}
                      </p>
                    )}
                    <p className="flex items-center gap-2">
                      <RefreshCw className="w-4 h-4" />
                      Auto-renew {subscription.auto_renew ? "on" : "off"}
                    </p>
                    {isPro && subscription.expires_at && (
                      <p className="text-xs opacity-75 mt-1">Renew anytime via Khalti below</p>
                    )}
                  </div>
                )}
              </div>
              {!isPro && (
                <div className="mt-4 pt-4 border-t border-white/20 flex flex-wrap items-center gap-2 text-xs opacity-90">
                  <span className="flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> 10× AI chat quota</span>
                  <span>·</span>
                  <span className="flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> 30/day notes & quizzes</span>
                  <span>·</span>
                  <span className="flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> Khalti NPR secure</span>
                </div>
              )}
            </div>

            {/* Free → Pro nudge */}
            {!isPro && !loading && (
              <div className="card p-4 border border-primary-200 bg-gradient-to-r from-primary-50 to-secondary-50 dark:from-slate-800 dark:to-slate-800 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center">
                    <Crown className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className="text-sm font-bold">Ready to unlock Mentora Pro?</p>
                    <p className="text-xs text-slate-500">Pay securely with Khalti wallet — NPR, instant activation.</p>
                  </div>
                </div>
                <button onClick={scrollToPlans} className="btn bg-[#5C2D91] hover:bg-[#4a2575] text-white text-sm font-bold px-5">
                  Subscribe Now
                </button>
              </div>
            )}

            {/* ---------- Usage today ---------- */}
            {usage && (
              <div className="card p-5 sm:p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-800 dark:text-slate-100">Today&apos;s Usage</h3>
                  <span className="text-xs text-slate-400">Resets at midnight UTC ({usage.usage_date})</span>
                </div>
                {usage.features.map(f => {
                  const pct = f.daily_limit > 0 ? Math.min(100, Math.round((f.used / f.daily_limit) * 100)) : 0;
                  return (
                    <div key={f.usage_type}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium text-slate-700 dark:text-slate-300">{subscriptionService.featureLabel(f.usage_type)}</span>
                        <span className={pct >= 100 ? "text-danger-500 font-semibold" : "text-slate-500"}>
                          {f.used} / {f.daily_limit}
                        </span>
                      </div>
                      <div className="progress-bar">
                        <div
                          className={`progress-fill ${pct >= 100 ? "bg-danger-500" : ""}`}
                          style={{ width: `${pct}%`, background: pct >= 100 ? undefined : barGradient(pct) }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* ---------- Available plans ---------- */}
            <div id="pro-plans" className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
              {plans.map(plan => {
                const current = usage ? plan.plan_type === usage.effective_plan : plan.plan_type === subscription?.plan_type;
                const isProCard = plan.plan_type === "SUBSCRIPTION";
                return (
                  <div key={plan.plan_type} className={`card p-5 sm:p-6 relative flex flex-col ${current ? "border-2 border-primary-500 shadow-glow-primary" : ""}`}>
                    {current && <span className="absolute -top-3 left-1/2 -translate-x-1/2 badge bg-primary-500 text-white">Your Plan</span>}
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-bold text-lg text-slate-800 dark:text-slate-100">{isProCard ? "Mentora Pro" : "Mentora Free"}</h3>
                      <span className={subscriptionService.planBadge(plan.plan_type).className}>{plan.plan_type}</span>
                    </div>

                    <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-300 mb-4 flex-1">
                      <li className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-primary-500" />
                        {plan.rate_limit_per_minute} requests / minute
                      </li>
                      {Object.entries(plan.daily_limits).map(([key, limit]) => (
                        <li key={key} className="flex items-center justify-between gap-2">
                          <span>{subscriptionService.featureLabel(key)}</span>
                          <span className="font-semibold">{limit}/day</span>
                        </li>
                      ))}
                    </ul>

                    {isProCard ? (
                      <div className="space-y-3 mt-2">
                        {/* Pricing */}
                        <div className="grid grid-cols-2 gap-2 text-center">
                          <div className="rounded-xl bg-slate-50 dark:bg-slate-800 p-3 border">
                            <p className="text-[11px] uppercase tracking-widest text-slate-400">Monthly</p>
                            <p className="text-xl font-black text-slate-800 dark:text-slate-100">{fmtNPR(monthlyPaisa)}</p>
                            <p className="text-[11px] text-slate-400">per month</p>
                          </div>
                          <div className="rounded-xl bg-gradient-to-br from-primary-50 to-secondary-50 dark:from-primary-900/20 dark:to-secondary-900/20 p-3 border border-primary-200 dark:border-primary-800">
                            <p className="text-[11px] uppercase tracking-widest text-primary-600">Yearly</p>
                            <p className="text-xl font-black text-primary-700 dark:text-primary-300">{fmtNPR(yearlyPaisa)}</p>
                            <p className="text-[11px] text-primary-600/70">save ~16%</p>
                          </div>
                        </div>

                        {/* Khalti actions */}
                        {!khaltiEnabled ? (
                          <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-xs text-amber-800 flex gap-2">
                            <ShieldCheck className="w-4 h-4 flex-shrink-0 mt-0.5" />
                            <span>Online payments are not configured. Contact your administrator to activate Mentora Pro, or set <code className="bg-white px-1 rounded">KHALTI_SECRET_KEY</code> on the backend.</span>
                          </div>
                        ) : (
                          <>
                            <button
                              onClick={() => handlePay("MONTHLY")}
                              disabled={!!payingCycle || verifying}
                              className="btn w-full bg-[#5C2D91] hover:bg-[#4a2575] text-white font-bold flex items-center justify-center gap-2 disabled:opacity-60"
                              title="Pay with Khalti Wallet"
                            >
                              {payingCycle === "MONTHLY" ? <Loader2 className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />}
                              Pay Monthly — {fmtNPR(monthlyPaisa)} with Khalti
                            </button>
                            <button
                              onClick={() => handlePay("YEARLY")}
                              disabled={!!payingCycle || verifying}
                              className="btn w-full bg-gradient-to-r from-primary-600 to-secondary-600 hover:from-primary-700 hover:to-secondary-700 text-white font-bold flex items-center justify-center gap-2 disabled:opacity-60"
                            >
                              {payingCycle === "YEARLY" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Crown className="w-4 h-4" />}
                              Pay Yearly — {fmtNPR(yearlyPaisa)} with Khalti
                            </button>
                            <p className="text-[11px] text-center text-slate-400 flex items-center justify-center gap-1">
                              <ShieldCheck className="w-3 h-3" /> Secured by Khalti ePayment · NPR payments only
                            </p>
                            <button onClick={handleManualVerify} disabled={verifying} className="text-xs text-primary-600 hover:underline w-full text-center disabled:opacity-50">
                              {verifying ? "Verifying…" : "Already paid? Verify payment"}
                            </button>
                          </>
                        )}

                        {/* Test hint */}
                        <details className="text-xs text-slate-500 bg-slate-50 dark:bg-slate-800 rounded-lg p-2">
                          <summary className="cursor-pointer font-medium">Sandbox test credentials</summary>
                          <ul className="list-disc ml-4 mt-1 space-y-0.5">
                            <li>Khalti ID: 9800000000 – 9800000005</li>
                            <li>MPIN: 1111</li>
                            <li>OTP: 987654</li>
                            <li>Use <code>test-admin.khalti.com</code> live_secret_key in KHALTI_SECRET_KEY for sandbox.</li>
                          </ul>
                        </details>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400 mt-2">Free forever — no payment required.</p>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Recent payments */}
            {payments.length > 0 && (
              <div className="card p-5 sm:p-6">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold flex items-center gap-2">
                    <Receipt className="w-4 h-4 text-primary-500" />
                    Recent Khalti Payments
                  </h3>
                  <button onClick={reload} className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1">
                    <RefreshCw className="w-3 h-3" /> Refresh
                  </button>
                </div>
                <div className="overflow-x-auto -mx-2">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-xs text-slate-400 border-b">
                        <th className="text-left py-2 px-2">Date</th>
                        <th className="text-left py-2 px-2">Cycle</th>
                        <th className="text-left py-2 px-2">Amount</th>
                        <th className="text-left py-2 px-2">Status</th>
                        <th className="text-left py-2 px-2">pidx</th>
                        <th className="text-right py-2 px-2">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {payments.map(p => (
                        <tr key={p.pidx} className="border-b last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                          <td className="py-2 px-2 text-xs text-slate-500">{p.created_at ? new Date(p.created_at).toLocaleString() : "—"}</td>
                          <td className="py-2 px-2">{p.billing_cycle}</td>
                          <td className="py-2 px-2 font-medium">{fmtNPR(p.amount)}</td>
                          <td className="py-2 px-2">
                            <span className={`badge text-xs ${statusColor(p.status)}`}>{p.status}</span>
                          </td>
                          <td className="py-2 px-2 font-mono text-xs truncate max-w-[140px]" title={p.pidx}>{p.pidx}</td>
                          <td className="py-2 px-2 text-right">
                            <div className="flex justify-end gap-1">
                              {p.payment_url && p.status !== "Completed" && (
                                <a href={p.payment_url} target="_blank" rel="noreferrer" className="btn btn-sm btn-ghost text-xs flex items-center gap-1">
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
                                  } finally { setVerifying(false); }
                                }}
                                className="btn btn-sm btn-ghost text-xs"
                                disabled={verifying}
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

            <p className="text-xs text-center text-slate-400">
              Payments are verified server-to-server via Khalti lookup. Only <span className="font-semibold">Completed</span> payments activate Mentora Pro · <a href="https://docs.khalti.com/khalti-epayment/" target="_blank" rel="noreferrer" className="underline">Khalti docs</a>
            </p>
          </>
        )}
      </div>
    </AppLayout>
  );
}

function barGradient(pct: number) {
  return pct >= 80
    ? "linear-gradient(90deg,#f59e0b,#d97706)"
    : pct >= 60
      ? "linear-gradient(90deg,#0ea5e9,#0284c7)"
      : "linear-gradient(90deg,#22c55e,#16a34a)";
}
