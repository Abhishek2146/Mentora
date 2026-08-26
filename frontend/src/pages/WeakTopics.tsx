import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { AlertTriangle, TrendingUp, BookOpen, Loader2 } from "lucide-react";
import { Link } from "react-router-dom";
import apiClient from "@/lib/api";

interface WeakTopic {
  id: number;
  topic_name: string;
  accuracy: number;
  confidence_level: number;
  total_attempts: number;
  recommended_action: string | null;
}

export default function WeakTopics() {
  const [topics, setTopics] = useState<WeakTopic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await apiClient.get("/api/v1/weak-topics/");
        setTopics(res.data ?? []);
      } catch {
        setError("Could not load your weak topics. Please try again later.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <AppLayout title="Weak Topics">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="card p-4 sm:p-5 bg-gradient-to-r from-warning-50 to-danger-50 dark:from-warning-900/20 dark:to-danger-900/20 border-warning-200 dark:border-warning-700">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-warning-600 flex-shrink-0" />
            <div>
              <h2 className="font-bold text-slate-800 dark:text-slate-100">Topics Needing Attention</h2>
              <p className="text-sm text-slate-500">Based on your quiz performance — focus here first</p>
            </div>
          </div>
        </div>

        {loading && (
          <div className="flex justify-center py-10">
            <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
          </div>
        )}

        {!loading && error && (
          <div className="card p-5 text-sm text-danger-600 dark:text-danger-400">{error}</div>
        )}

        {!loading && !error && topics.length === 0 && (
          <div className="card p-8 text-center">
            <TrendingUp className="w-10 h-10 mx-auto text-success-500 mb-3" />
            <p className="font-semibold text-slate-700 dark:text-slate-200">No weak topics detected</p>
            <p className="text-sm text-slate-500 mt-1">Take a quiz and we'll highlight the topics you need to work on.</p>
          </div>
        )}

        <div className="space-y-4">
          {topics.map(topic => (
            <div key={topic.id} className="card p-4 sm:p-5 hover:shadow-soft transition-all">
              <div className="flex flex-col sm:flex-row items-start justify-between gap-3 sm:gap-4">
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-2">
                    <h3 className="font-bold text-slate-800 dark:text-slate-100">{topic.topic_name}</h3>
                    <span className={`badge ${ topic.accuracy < 50 ? "badge-red" : "badge-yellow" }`}>
                      {topic.accuracy < 50 ? "High Priority" : "Medium Priority"}
                    </span>
                  </div>
                  {topic.recommended_action && (
                    <p className="text-sm text-slate-500 mb-3">{topic.recommended_action}</p>
                  )}

                  <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-3">
                    {[
                      { label: "Accuracy", value: `${Math.round(topic.accuracy)}%` },
                      { label: "Confidence", value: `${Math.round(topic.confidence_level)}%` },
                      { label: "Attempts", value: topic.total_attempts },
                    ].map(s => (
                      <div key={s.label} className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-2 text-center">
                        <p className="text-lg font-bold text-slate-700 dark:text-slate-200">{s.value}</p>
                        <p className="text-xs text-slate-400">{s.label}</p>
                      </div>
                    ))}
                  </div>

                  <div className="progress-bar">
                    <div className="progress-fill bg-gradient-to-r from-warning-500 to-danger-500" style={{ width: `${topic.accuracy}%` }} />
                  </div>
                </div>

                <div className="flex flex-row sm:flex-col gap-2">
                  <Link to="/ai-tutor" className="btn-primary btn-sm">
                    <BookOpen className="w-4 h-4" /> Study
                  </Link>
                  <Link to="/mcq" className="btn-outline btn-sm">
                    <TrendingUp className="w-4 h-4" /> Practice
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
