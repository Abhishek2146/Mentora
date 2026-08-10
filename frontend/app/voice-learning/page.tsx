import DashboardLayout from "@/components/layout/DashboardLayout";
import apiClient from "@/lib/api";
import { useState } from "react";

export default function VoiceLearningPage() {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const startRecording = async () => {
    setIsRecording(true);
    setTranscript("");
    setResponse("");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      const chunks: BlobPart[] = [];

      mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunks, { type: "audio/wav" });
        const formData = new FormData();
        formData.append("audio", blob);

        setLoading(true);
        try {
          const res = await apiClient.post("/api/v1/voice/listen", formData, {
            headers: { "Content-Type": "multipart/form-data" },
          });
          setTranscript(res.data.transcript);
          setResponse(res.data.response);
          setAudioUrl(res.data.audio_url);
        } catch (error) {
          console.error("Voice processing failed:", error);
        } finally {
          setLoading(false);
        }
      };

      mediaRecorder.start();
      setTimeout(() => {
        mediaRecorder.stop();
        setIsRecording(false);
        stream.getTracks().forEach(track => track.stop());
      }, 10000);
    } catch (error) {
      console.error("Recording failed:", error);
      alert("Microphone access denied or not available");
      setIsRecording(false);
    }
  };

  const speakText = async () => {
    if (!response) return;
    try {
      await apiClient.post("/api/v1/voice/speak", { text: response });
    } catch (error) {
      console.error("TTS failed:", error);
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Voice Learning</h1>
        <p className="text-gray-600 mb-6">
          Practice speaking and listening with AI-powered voice recognition.
        </p>

        <div className="bg-white rounded-lg shadow p-6 space-y-6">
          <div className="flex items-center space-x-4">
            <button
              onClick={startRecording}
              disabled={isRecording || loading}
              className={`px-6 py-3 rounded-md text-white transition-colors ${
                isRecording
                  ? "bg-red-600 hover:bg-red-700 animate-pulse"
                  : "bg-primary-600 hover:bg-primary-700 disabled:opacity-50"
              }`}
            >
              {isRecording ? "Recording..." : loading ? "Processing..." : "Start Recording"}
            </button>
            {audioUrl && (
              <button
                onClick={speakText}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Play Response
              </button>
            )}
          </div>

          {transcript && (
            <div className="p-4 bg-gray-50 rounded-lg">
              <h3 className="font-semibold text-gray-700 mb-2">Your Voice:</h3>
              <p className="text-gray-800">{transcript}</p>
            </div>
          )}

          {response && (
            <div className="p-4 bg-primary-50 rounded-lg">
              <h3 className="font-semibold text-primary-700 mb-2">AI Response:</h3>
              <p className="text-gray-800">{response}</p>
            </div>
          )}

          {audioUrl && (
            <div className="p-4">
              <audio controls src={audioUrl} className="w-full" />
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
