import apiClient from "@/lib/api";
import type { PlanInfo, PlansResponse, Subscription, UsageReport } from "@/types";

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
};
