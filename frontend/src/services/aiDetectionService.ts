import apiClient from "@/lib/api";

export type DetectionLabel =
  | "likely_human"
  | "uncertain"
  | "potentially_ai_generated"
  | "strong_ai_like_signals";

export type DetectionVerdict = "likely_human" | "mixed_or_uncertain" | "likely_ai";

export interface DetectionSignal {
  name: string;
  explanation: string;
  value: number;
}

export interface DetectionBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface DetectionSpan {
  text: string;
  start: number;
  end: number;
  confidence: number;
  label: DetectionLabel;
  signals: DetectionSignal[];
  page: number | null;
  boxes: DetectionBox[];
}

export interface DetectionDistribution {
  ai_like: number;
  uncertain: number;
  human: number;
}

export interface DetectionBase {
  result_id: string;
  overall_score: number;
  label: DetectionLabel;
  confidence: number;
  analyzed_words: number;
  summary: string;
  distribution: DetectionDistribution;
  detections: DetectionSpan[];
  insufficient_text: boolean;
  message: string | null;
  disclaimer: string;
}

export interface TextDetectionResponse extends DetectionBase {}

export interface PdfWord {
  text: string;
  start: number;
  end: number;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface PdfPage {
  page: number;
  text: string;
  width: number;
  height: number;
  words: PdfWord[];
  ocr: boolean;
}

export interface PdfDetectionResponse extends DetectionBase {
  file_name: string;
  pdf_url: string;
  pages: PdfPage[];
  scanned: boolean;
  extraction_warning: string | null;
}

// Legacy response of the /analyze endpoint, kept for backwards compatibility.
export interface DetectionResult {
  score: number;
  verdict: DetectionVerdict;
  confidence: number;
  summary: string;
  signals: DetectionSignal[];
  disclaimer: string;
}

export interface TextDetectionRequest {
  text: string;
}

export const aiDetectionService = {
  /** Analyze pasted text. */
  async analyzeText(text: string): Promise<TextDetectionResponse> {
    const response = await apiClient.post<TextDetectionResponse>(
      "/api/v1/ai-detection/text",
      { text }
    );
    return response.data;
  },

  /** Analyze an uploaded PDF file. */
  async uploadPdf(file: File): Promise<PdfDetectionResponse> {
    const formData = new FormData();
    formData.append("file", file);
    const response = await apiClient.post<PdfDetectionResponse>(
      "/api/v1/ai-detection/pdf",
      formData,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    return response.data;
  },

  /** Fetch an earlier analysis by id. */
  async getResult(analysisId: string): Promise<TextDetectionResponse | PdfDetectionResponse> {
    const response = await apiClient.get<TextDetectionResponse | PdfDetectionResponse>(
      `/api/v1/ai-detection/${analysisId}`
    );
    return response.data;
  },

  /** Fetch the original uploaded PDF bytes (for in-page rendering). */
  async getPdfFile(analysisId: string): Promise<ArrayBuffer> {
    const response = await apiClient.get<ArrayBuffer>(
      `/api/v1/ai-detection/${analysisId}/file`,
      { responseType: "arraybuffer" }
    );
    return response.data;
  },

  /** Download the analyzed PDF with flagged regions highlighted. */
  async downloadHighlightedPdf(analysisId: string, fileName: string): Promise<void> {
    const response = await apiClient.get<Blob>(
      `/api/v1/ai-detection/${analysisId}/highlighted`,
      { responseType: "blob" }
    );
    const url = window.URL.createObjectURL(response.data);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `highlighted-${fileName || "document.pdf"}`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  },

  /** Backwards-compatible call against the legacy /analyze endpoint. */
  async analyze(text: string): Promise<DetectionResult> {
    const response = await apiClient.post<DetectionResult>("/api/v1/ai-detection/analyze", { text });
    return response.data;
  },
};