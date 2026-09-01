import apiClient from "@/lib/api";
import type {
  KhaltiConfig,
  KhaltiInitiateResponse,
  KhaltiVerifyResponse,
  PaymentOut,
  PlanInfo,
  PlansResponse,
  Subscription,
  UsageReport,
  BillingCycle,
} from "@/types";

export const subscriptionService = {
  /** Public plan catalogue with limits. */
  async getPlans(): Promise<PlansResponse> {
    const res = await apiClient.get("/api/v1/subscriptions/plans");
    return res.data;
  },

  /** The authenticated user's own subscription. */
  async getMySubscription(): Promise<Subscription> {
    const res = await apiClient.get("/api/v1/subscriptions/me");
    return res.data;
  },

  /** Effective plan limits + per-minute rate limit. */
  async getMyLimits() {
    const res = await apiClient.get("/api/v1/subscriptions/me/limits");
    return res.data;
  },

  /** Today's usage and remaining quota for every feature. */
  async getMyUsage(): Promise<UsageReport> {
    const res = await apiClient.get("/api/v1/usage/me");
    return res.data;
  },

  // -------- Khalti ePayment (NPR via Khalti Wallet) --------

  /** Public pricing/config + enabled flag. */
  async getKhaltiConfig(): Promise<KhaltiConfig> {
    const res = await apiClient.get("/api/v1/subscriptions/khalti/config");
    return res.data;
  },

  /** Initiate a Khalti payment; returns payment_url for redirect. */
  async initiateKhalti(billingCycle: BillingCycle): Promise<KhaltiInitiateResponse> {
    const res = await apiClient.post("/api/v1/subscriptions/khalti/initiate", {
      billing_cycle: billingCycle,
    });
    return res.data;
  },

  /** Verify a Khalti pidx via server-side lookup and activate plan if Completed. */
  async verifyKhalti(pidx: string): Promise<KhaltiVerifyResponse> {
    const res = await apiClient.post("/api/v1/subscriptions/khalti/verify", { pidx });
    return res.data;
  },

  /** GET lookup convenience (same as verify but via query param). */
  async lookupKhalti(pidx: string): Promise<KhaltiVerifyResponse> {
    const res = await apiClient.get("/api/v1/subscriptions/khalti/lookup", {
      params: { pidx },
    });
    return res.data;
  },

  /** Recent payments for the authenticated user. */
  async listMyPayments(limit = 20): Promise<PaymentOut[]> {
    const res = await apiClient.get("/api/v1/subscriptions/khalti/payments", {
      params: { limit },
    });
    return res.data;
  },

  featureLabel(usageType: string): string {
    return (
      (
        {
          AI_CHAT: "AI Tutor Chat",
          NOTE_GENERATION: "Note Generation",
          QUIZ_GENERATION: "Quiz Generation",
          FLASHCARD_GENERATION: "Flashcard Generation",
          STUDY_PLAN_GENERATION: "Study Plan Generation",
          CODING_PROBLEM_GENERATION: "Coding Problem Generation",
          SYLLABUS_ANALYSIS: "Syllabus Analysis",
        } as Record<string, string>
      )[usageType] ?? usageType
    );
  },

  planBadge(plan: PlanInfo["plan_type"]): { label: string; className: string } {
    return plan === "SUBSCRIPTION"
      ? { label: "PRO", className: "badge bg-gradient-to-r from-primary-500 to-secondary-500 text-white" }
      : { label: "FREE", className: "badge badge-blue" };
  },

  /** NPR formatter from paisa or NPR float. */
  formatNPR(paisaOrNpr: number, isPaisa = false): string {
    const npr = isPaisa ? paisaOrNpr / 100 : paisaOrNpr;
    return `Rs. ${npr.toLocaleString("en-NP", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  },
};
