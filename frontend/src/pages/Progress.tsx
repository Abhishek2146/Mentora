import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { TrendingUp, Loader2 } from "lucide-react";
import apiClient from "@/lib/api";

interface WeakTopic {
  id: number;
  topic_name: string;
  accuracy: number;
}

const barColor = (pct: number) =>
  pct >= 80
    ? "linear-gradient(90deg,#22c55e,#16a34a)"
    : pct >= 60
    ? "linear-gradient(90deg,#0ea5e9,#0284c7)"
    : "linear-gradient(90deg,#f59e0b,#d97706)";

export default function Progress() {
  const [topics, setTopics] = useState<WeakTopic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await apiClient.get("/api/v1/weak-topics/");
        setTopics(res.data ?? []);
      } catch {
        setError("Could not load your progress. Please try again later.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const overallPct =
    topics.length > 0
      ? Math.round(topics.reduce((sum, t) => sum + (t.accuracy ?? 0), 0) / topics.length)
      : 0;
  const mastered = topics.filter(t => (t.accuracy ?? 0) >= 80).length;

  return (
    <AppLayout title="Progress">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="card p-5 sm:p-6 bg-gradient-to-r from-primary-600 to-secondary-600 text-white border-0">
          <div className="flex items-center gap-4">
            <TrendingUp className="w-10 h-10 flex-shrink-0" />
            {loading ? (
              <Loader2 className="w-8 h-8 animate-spin" />
            ) : (
              <div>
                <p className="text-primary-100">Overall Progress</p>
                <p className="text-3xl sm:text-4xl font-black">{overallPct}%</p>
                <p className="text-primary-100 text-sm">{mastered} of {topics.length} topics mastered</p>
              </div>
            )}
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
            <TrendingUp className="w-10 h-10 mx-auto text-primary-400 mb-3" />
            <p className="font-semibold text-slate-700 dark:text-slate-200">No progress data yet</p>
            <p className="text-sm text-slate-500 mt-1">Upload a syllabus and take quizzes — your topic mastery will show up here.</p>
          </div>
        )}

        {!loading && topics.length > 0 && (
          <div className="card p-5 sm:p-6 space-y-4">
            <h3 className="font-bold text-slate-800 dark:text-slate-100">Topic-wise Mastery</h3>
            {topics.map(t => {
              const pct = Math.round(t.accuracy ?? 0);
              return (
                <div key={t.id}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-slate-700 dark:text-slate-300">{t.topic_name}</span>
                    <span className="text-slate-500">{pct}%</span>
                  </div>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${pct}%`, background: barColor(pct) }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
