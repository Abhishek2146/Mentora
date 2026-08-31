import apiClient from "@/lib/api";

export interface VoiceResponse {
  transcript: string;
  response: string;
  audio_url: string | null;
  session_id: number;
}

export interface VoiceSession {
  id: number;
  user_id: number;
  session_id: number | null;
  audio_path: string | null;
  transcript: string | null;
  response_text: string | null;
  voice_used: string;
  duration: number | null;
  created_at: string;
  updated_at: string | null;
}

export const voiceService = {
  async listen(
    audioBlob: Blob,
    syllabusId?: number,
    sessionId?: number,
    voice: string = "default",
  ): Promise<VoiceResponse> {
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.webm");
    if (syllabusId) formData.append("syllabus_id", syllabusId.toString());
    if (sessionId) formData.append("session_id", sessionId.toString());
    formData.append("voice", voice);

    const res = await apiClient.post<VoiceResponse>("/api/v1/voice/listen", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000,
    });
    return res.data;
  },

  async speak(text: string, voice: string = "default"): Promise<{ audio_url: string; text: string }> {
    const res = await apiClient.post("/api/v1/voice/speak", null, {
      params: { text, voice },
    });
    return res.data;
  },

  async getSessions(): Promise<VoiceSession[]> {
    const res = await apiClient.get<VoiceSession[]>("/api/v1/voice/sessions");
    return res.data;
  },
};
