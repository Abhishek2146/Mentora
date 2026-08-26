import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import {
  TrendingUp,
  TrendingDown,
  Loader2,
  BookOpen,
  FileText,
  Layers,
  GraduationCap,
} from "lucide-react";
import apiClient from "@/lib/api";

interface TopicMastery {
  topic_name: string;
  accuracy: number;
  attempts: number;
}

interface Overview {
  overall_mastery: number;
  improvement: number | null;
  total_attempts: number;
  sources: {
    quizzes: number;
    exams: number;
    mcqs: number;
    flashcards: number;
  };
  topics: TopicMastery[];
}

const barColor = (pct: number) =>
  pct >= 80
    ? "linear-gradient(90deg,#22c55e,#16a34a)"
    : pct >= 60
    ? "linear-gradient(90deg,#0ea5e9,#0284c7)"
    : "linear-gradient(90deg,#f59e0b,#d97706)";

export default function Progress() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await apiClient.get("/api/v1/progress/overview");
        setOverview(res.data ?? null);
      } catch {
        setError("Could not load your progress. Please try again later.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const topics = overview?.topics ?? [];
  const sources = overview?.sources;

  const sourceCards = [
    { label: "Quizzes", value: sources?.quizzes ?? 0, icon: BookOpen },
    { label: "Mock Exams", value: sources?.exams ?? 0, icon: GraduationCap },
    { label: "MCQ Practice", value: sources?.mcqs ?? 0, icon: FileText },
    { label: "Flashcard Reviews", value: sources?.flashcards ?? 0, icon: Layers },
  ];

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
                <p className="text-primary-100">Overall Mastery</p>
                <p className="text-3xl sm:text-4xl font-black">
                  {Math.round(overview?.overall_mastery ?? 0)}%
                </p>
                <p className="text-primary-100 text-sm flex items-center gap-2 mt-1">
                  {overview && overview.improvement !== null && (
                    <span
                      className={`inline-flex items-center gap-1 badge ${
                        overview.improvement >= 0 ? "badge-green" : "badge-red"
                      }`}
                    >
                      {overview.improvement >= 0 ? (
                        <TrendingUp className="w-3 h-3" />
                      ) : (
                        <TrendingDown className="w-3 h-3" />
                      )}
                      {overview.improvement >= 0 ? "+" : ""}
                      {overview.improvement}% recent vs earlier
                    </span>
                  )}
                  <span>
                    {overview?.total_attempts ?? 0} practice questions & reviews
                  </span>
                </p>
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

        {!loading && !error && overview && topics.length === 0 && (
          <div className="card p-8 text-center">
            <TrendingUp className="w-10 h-10 mx-auto text-primary-400 mb-3" />
            <p className="font-semibold text-slate-700 dark:text-slate-200">No progress data yet</p>
            <p className="text-sm text-slate-500 mt-1">
              Upload a syllabus, then review flashcards or take quizzes/MCQs/mock exams —
              your mastery will show up here.
            </p>
          </div>
        )}

        {!loading && topics.length > 0 && sources && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {sourceCards.map(s => (
                <div key={s.label} className="card p-3 sm:p-4 text-center">
                  <s.icon className="w-5 h-5 mx-auto text-primary-500 mb-1" />
                  <p className="text-xl font-bold text-slate-700 dark:text-slate-200">{s.value}</p>
                  <p className="text-xs text-slate-400">{s.label}</p>
                </div>
              ))}
            </div>

            <div className="card p-5 sm:p-6 space-y-4">
              <h3 className="font-bold text-slate-800 dark:text-slate-100">
                Topic-wise Mastery
                <span className="text-xs font-normal text-slate-400 ml-2">
                  across quizzes, MCQs, exams and flashcards
                </span>
              </h3>
              {topics.map(t => {
                const pct = Math.round(t.accuracy);
                return (
                  <div key={t.topic_name}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-medium text-slate-700 dark:text-slate-300">
                        {t.topic_name}
                      </span>
                      <span className="text-slate-500">
                        {pct}% · {t.attempts} attempts
                      </span>
                    </div>
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{ width: `${pct}%`, background: barColor(pct) }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
