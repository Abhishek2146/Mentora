import apiClient from "@/lib/api";

export type DetectionVerdict = "likely_human" | "mixed_or_uncertain" | "likely_ai";

export interface DetectionSignal {
  name: string;
  explanation: string;
}

export interface DetectionResult {
  score: number;
  verdict: DetectionVerdict;
  confidence: number;
  summary: string;
  signals: DetectionSignal[];
  disclaimer: string;
}

export const aiDetectionService = {
  async analyze(text: string): Promise<DetectionResult> {
    const response = await apiClient.post<DetectionResult>("/api/v1/ai-detection/analyze", { text });
    return response.data;
  },
};
