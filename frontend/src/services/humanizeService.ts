import apiClient from "@/lib/api";

export type HumanizeIntensity = "subtle" | "balanced" | "strong";

export interface HumanizeRequest {
  text: string;
  intensity?: HumanizeIntensity;
}

export interface HumanizeResponse {
  humanized_text: string;
  summary: string;
  disclaimer: string;
}

export const humanizeService = {
  /** Rewrite the given text so it reads more naturally. */
  async humanizeText(text: string, intensity: HumanizeIntensity = "balanced"): Promise<HumanizeResponse> {
    const response = await apiClient.post<HumanizeResponse>("/api/v1/humanize/text", {
      text,
      intensity,
    });
    return response.data;
  },
};