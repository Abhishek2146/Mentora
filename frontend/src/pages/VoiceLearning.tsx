import AppLayout from "@/components/layout/AppLayout";
import { Mic, Volume2, Play, Pause } from "lucide-react";
import { useState } from "react";

export default function VoiceLearning() {
  const [recording, setRecording] = useState(false);
  return (
    <AppLayout title="Voice Learning">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="card p-5 sm:p-8 flex flex-col items-center gap-6 text-center">
          <div className={`w-24 h-24 rounded-full flex items-center justify-center transition-all ${ recording ? "bg-danger-500 shadow-lg animate-pulse" : "bg-gradient-to-br from-primary-500 to-secondary-500" }`}>
            <Mic className="w-12 h-12 text-white" />
          </div>
          <div>
            <h2 className="text-xl sm:text-2xl font-bold text-slate-800 dark:text-slate-100">Voice Learning Mode</h2>
            <p className="text-slate-500 mt-2">Ask questions out loud — AI responds with voice & text</p>
          </div>
          <button onClick={() => setRecording(!recording)}
            className={`btn btn-lg px-10 ${ recording ? "bg-danger-500 hover:bg-danger-600 text-white" : "btn-primary" }`}>
            {recording ? <><Pause className="w-5 h-5" /> Stop Recording</> : <><Mic className="w-5 h-5" /> Start Speaking</>}
          </button>
        </div>
        <div className="card p-4 sm:p-6">
          <h3 className="font-bold text-slate-700 dark:text-slate-200 mb-4 flex items-center gap-2"><Volume2 className="w-5 h-5 text-primary-500" /> Try These Phrases</h3>
          <div className="space-y-2">
            {["Explain what normalization is", "What are the ACID properties?", "How does a B+ tree work?", "Quiz me on SQL joins"].map(p => (
              <div key={p} className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-xl">
                <Play className="w-4 h-4 text-primary-500 flex-shrink-0" />
                <span className="min-w-0 break-words text-sm text-slate-600 dark:text-slate-300 italic">"{p}"</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
