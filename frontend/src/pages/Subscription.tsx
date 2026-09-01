import { useEffect, useState } from "react";
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
} from "lucide-react";
import { subscriptionService } from "@/services/subscriptionService";
import type {
  PlanInfo,
  Subscription as SubscriptionData,
  UsageReport,
} from "@/types";

const fmtDate = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "—";

export default function Subscription() {
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [usage, setUsage] = useState<UsageReport | null>(null);
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [subRes, usageRes, plansRes] = await Promise.allSettled([
          subscriptionService.getMySubscription(),
          subscriptionService.getMyUsage(),
          subscriptionService.getPlans(),
        ]);

        if (subRes.status === "fulfilled") setSubscription(subRes.value);
        if (usageRes.status === "fulfilled") setUsage(usageRes.value);
        if (plansRes.status === "fulfilled") setPlans(plansRes.value.plans);

        if (
          subRes.status === "rejected" &&
          usageRes.status === "rejected"
        ) {
          setError("Could not load your subscription details.");
        }
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const isPro =
    usage?.effective_plan === "SUBSCRIPTION" ||
    (subscription?.plan_type === "SUBSCRIPTION" &&
      subscription?.status === "ACTIVE");

  const isActive = subscription?.status === "ACTIVE";

  return (
    <AppLayout title="Subscription">
      <div className="max-w-5xl mx-auto space-y-6">
        {error && (
          <div className="card p-4 flex items-center gap-2 text-sm text-danger-600 dark:text-danger-400">
            <AlertCircle className="w-4 h-4" /> {error}
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
              className={`card p-6 border-0 text-white ${
                isPro
                  ? "bg-gradient-to-r from-primary-600 to-secondary-600"
                  : "bg-gradient-to-r from-slate-700 to-slate-800"
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${ isPro ? "bg-white/15" : "bg-white/10" }`}>
                    {isPro ? (
                      <Crown className="w-7 h-7 text-yellow-300" />
                    ) : (
                      <Zap className="w-7 h-7 text-slate-300" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm opacity-80">Current Plan</p>
                    <h2 className="text-2xl font-black">
                      {isPro ? "Mentora Pro" : "Mentora Free"}
                    </h2>
                    <div className="flex flex-wrap items-center gap-2 mt-1 text-xs opacity-90">
                      <span className={`badge ${ isActive ? "bg-success-500 text-white" : "bg-danger-500 text-white" }`}>
                        {isActive ? (
                          <><CheckCircle2 className="w-3 h-3 mr-1" />{subscription?.status ?? "ACTIVE"}</>
                        ) : (
                          <><XCircle className="w-3 h-3 mr-1" />{subscription?.status ?? "INACTIVE"}</>
                        )}
                      </span>
                      {subscription && (
                        <span className="badge bg-white/15 text-white">
                          {subscription.plan_type}
                          {subscription.billing_cycle !== "NONE" &&
                            ` · ${subscription.billing_cycle}`}
                        </span>
                      )}
                      {isPro && usage && (
                        <span className="badge bg-white/15 text-white">
                          <Zap className="w-3 h-3 mr-1" />
                          {usage.rate_limit_per_minute} req/min
                        </span>
                      )}
                    </div>
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
                  </div>
                )}
              </div>
            </div>

            {/* ---------- Usage today ---------- */}
            {usage && (
              <div className="card p-5 sm:p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-800 dark:text-slate-100">Today's Usage</h3>
                  <span className="text-xs text-slate-400">
                    Resets at midnight UTC ({usage.usage_date})
                  </span>
                </div>

                {usage.features.map(f => {
                  const pct =
                    f.daily_limit > 0
                      ? Math.min(100, Math.round((f.used / f.daily_limit) * 100))
                      : 0;
                  return (
                    <div key={f.usage_type}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium text-slate-700 dark:text-slate-300">
                          {subscriptionService.featureLabel(f.usage_type)}
                        </span>
                        <span className={pct >= 100 ? "text-danger-500 font-semibold" : "text-slate-500"}>
                          {f.used} / {f.daily_limit}
                        </span>
                      </div>
                      <div className="progress-bar">
                        <div
                          className={`progress-fill ${ pct >= 100 ? "bg-danger-500" : "" }`}
                          style={{
                            width: `${pct}%`,
                            background: pct >= 100 ? undefined : barGradient(pct),
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* ---------- Available plans ---------- */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
              {plans.map(plan => {
                const current = usage
                  ? plan.plan_type === usage.effective_plan
                  : plan.plan_type === subscription?.plan_type;
                return (
                  <div
                    key={plan.plan_type}
                    className={`card p-5 sm:p-6 relative ${
                      current
                        ? "border-2 border-primary-500 shadow-glow-primary"
                        : ""
                    }`}
                  >
                    {current && (
                      <span className="absolute -top-3 left-1/2 -translate-x-1/2 badge bg-primary-500 text-white">
                        Your Plan
                      </span>
                    )}
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-bold text-lg text-slate-800 dark:text-slate-100">
                        {plan.plan_type === "SUBSCRIPTION" ? "Mentora Pro" : "Mentora Free"}
                      </h3>
                      <span className={subscriptionService.planBadge(plan.plan_type).className}>
                        {plan.plan_type}
                      </span>
                    </div>

                    <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-300 mb-4">
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

                    {plan.plan_type === "SUBSCRIPTION" && (
                      <p className="text-xs text-slate-400">
                        Billing cycles: {plan.billing_cycles.join(" or ").toLowerCase()} ·
                        managed by your administrator until online payments are enabled
                      </p>
                    )}
                  </div>
                );
              })}
            </div>

            <p className="text-xs text-center text-slate-400">
              Need an upgrade? Contact your administrator — subscriptions are activated
              securely on the backend and can never be changed from the client.
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
