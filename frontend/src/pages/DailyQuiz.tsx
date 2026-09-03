import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import AppLayout from "@/components/layout/AppLayout";
import {
  CheckCircle2,
  XCircle,
  ChevronRight,
  Trophy,
  Loader2,
  RefreshCw,
  BookOpen,
  Sparkles,
  Upload,
} from "lucide-react";
import { quizService } from "@/services/quizService";

export default function DailyQuiz() {
  const [quizTitle, setQuizTitle] = useState<string>("");
  const [questions, setQuestions] = useState<any[]>([]);
  const [current, setCurrent] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [answers, setAnswers] = useState<{ question_id: number; selected: string }[]>([]);
  const [result, setResult] = useState<any>(null);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<number>(Date.now());
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    loadQuiz();
  }, []);

  async function loadQuiz() {
    setLoading(true);
    setError(null);
    try {
      const d = await quizService.getDailyQuiz(5);
      setQuizTitle(d.title || "Daily Quiz");
      setQuestions(d.questions || []);
      setCurrent(0);
      setSelected(null);
      setAnswers([]);
      setDone(false);
      setResult(null);
      setStartedAt(Date.now());
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Could not load today's quiz.");
    } finally {
      setLoading(false);
    }
  }

  async function regenerateQuiz() {
    setRegenerating(true);
    setError(null);
    try {
      const d = await quizService.regenerateDailyQuiz(5);
      setQuizTitle(d.title || "Daily Quiz");
      setQuestions(d.questions || []);
      setCurrent(0);
      setSelected(null);
      setAnswers([]);
      setDone(false);
      setResult(null);
      setStartedAt(Date.now());
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to regenerate quiz.");
    } finally {
      setRegenerating(false);
    }
  }

  const q = questions[current];
  const correctCount = result ? result.correct : answers.filter((a) =>
    questions.some((qq) => qq.id === a.question_id && qq.correct_answer === a.selected)
  ).length;

  const next = async () => {
    if (!selected || !q) return;
    const newAnswers = [...answers, { question_id: q.id, selected }];
    setAnswers(newAnswers);
    setSelected(null);
    if (current + 1 >= questions.length) {
      setSubmitting(true);
      try {
        // Quiz submission - grading done locally
        setResult(null);
      } catch {
        // Fall back to local grading if submission fails.
      } finally {
        setSubmitting(false);
        setDone(true);
      }
    } else {
      setCurrent((c) => c + 1);
    }
  };

  if (loading) {
    return (
      <AppLayout title="Daily Quiz">
        <div className="flex flex-col items-center justify-center h-64 gap-3">
          <div className="w-10 h-10 border-4 border-primary-200 border-t-primary-500 rounded-full animate-spin" />
          <p className="text-sm text-slate-500 animate-pulse">
            Generating today's quiz...
          </p>
        </div>
      </AppLayout>
    );
  }

  if (error) {
    return (
      <AppLayout title="Daily Quiz">
        <div className="max-w-xl mx-auto">
          <div className="card p-10 flex flex-col items-center gap-5 text-center">
            <div className="w-16 h-16 rounded-2xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center text-primary-600 dark:text-primary-400">
              <BookOpen className="w-8 h-8" />
            </div>
            <div className="space-y-1">
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">
                Quiz Generation Error
              </h3>
              <p className="text-sm text-slate-500 max-w-md">{error}</p>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                onClick={() => loadQuiz()}
                className="btn-primary btn-md inline-flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" /> Retry
              </button>
            </div>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (done) {
    const pct = result
      ? result.score
      : questions.length
      ? Math.round((correctCount / questions.length) * 100)
      : 0;
    return (
      <AppLayout title="Daily Quiz">
        <div className="max-w-xl mx-auto space-y-4">
          <div className="card p-8 sm:p-10 flex flex-col items-center gap-6 text-center">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center shadow-lg">
              <Trophy className="w-10 h-10 text-white" />
            </div>
            <div>
              <h2 className="text-3xl font-black text-slate-800 dark:text-slate-100">{pct}%</h2>
              <p className="text-slate-500 mt-1">
                {correctCount} of {questions.length} correct
              </p>
              {!result && <p className="text-xs text-slate-400 mt-2">(score could not be saved)</p>}
            </div>
            {result?.results && (
              <div className="w-full space-y-3 text-left">
                {result.results.map((r: any) => (
                  <div
                    key={r.question_id}
                    className={`p-4 rounded-xl border text-sm space-y-1.5 ${
                      r.is_correct
                        ? "border-emerald-200 bg-emerald-50 dark:bg-emerald-900/20"
                        : "border-red-200 bg-red-50 dark:bg-red-900/20"
                    }`}
                  >
                    <p className="font-semibold text-slate-800 dark:text-slate-100">
                      {r.is_correct ? "✓" : "✗"} {r.question}
                    </p>
                    {!r.is_correct && (
                      <p className="text-xs font-medium text-red-600 dark:text-red-400">
                        Correct Answer: {r.correct_answer}
                      </p>
                    )}
                    {r.explanation && (
                      <p className="text-xs text-slate-600 dark:text-slate-300 pt-1 border-t border-slate-200/50 dark:border-slate-700/50">
                        💡 {r.explanation}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
            <div className="flex items-center gap-3">
              <button onClick={() => loadQuiz()} className="btn-primary btn-md">
                Done
              </button>
              <button
                onClick={regenerateQuiz}
                disabled={regenerating}
                className="btn-secondary btn-md inline-flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${regenerating ? "animate-spin" : ""}`} /> New Daily Questions
              </button>
            </div>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Daily Quiz">
      <div className="max-w-xl mx-auto space-y-5">
        {/* Header */}
        <div className="card p-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary-100 dark:bg-primary-900/40 flex items-center justify-center text-primary-600 dark:text-primary-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Syllabus Curriculum Practice
              </p>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                Daily Syllabus Quiz
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={regenerateQuiz}
              disabled={regenerating}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-primary-600 hover:border-primary-400 dark:hover:border-primary-500 transition-colors disabled:opacity-40"
              title="Generate fresh daily questions"
            >
              <RefreshCw className={`w-4 h-4 ${regenerating ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Progress bar */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex-1 progress-bar">
            <div
              className="progress-fill bg-gradient-to-r from-primary-500 to-secondary-500"
              style={{ width: `${(current / questions.length) * 100}%` }}
            />
          </div>
          <span className="text-sm text-slate-500 font-medium">
            {current + 1} / {questions.length}
          </span>
        </div>

        {/* Question card */}
        {q && (
          <div className="card p-5 sm:p-7 space-y-6">
            <div className="flex items-start justify-between gap-3 sm:gap-4">
              <p className="font-semibold text-slate-800 dark:text-slate-100 text-lg leading-snug">
                {q.question_text}
              </p>
              <span
                className={`badge flex-shrink-0 ${
                  q.difficulty === "Easy"
                    ? "badge-green"
                    : q.difficulty === "Hard"
                    ? "badge-red"
                    : "badge-yellow"
                }`}
              >
                {q.difficulty}
              </span>
            </div>

            <div className="space-y-3">
              {q.options?.map((opt: string) => {
                const isCorrect = selected && opt === q.correct_answer;
                const isWrong = selected === opt && opt !== q.correct_answer;
                return (
                  <button
                    key={opt}
                    onClick={() => !selected && setSelected(opt)}
                    className={`w-full text-left p-4 rounded-xl border-2 transition-all text-sm font-medium ${
                      isCorrect
                        ? "border-success-500 bg-success-50 dark:bg-success-900/20 text-success-700 dark:text-success-300"
                        : isWrong
                        ? "border-danger-500 bg-danger-50 dark:bg-danger-50 dark:text-danger-300"
                        : selected && opt !== selected
                        ? "border-slate-200 dark:border-slate-600 text-slate-400 opacity-60"
                        : "border-slate-200 dark:border-slate-600 hover:border-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 text-slate-700 dark:text-slate-200"
                    }`}
                  >
                    <span className="flex items-center justify-between gap-2">
                      {opt}
                      {isCorrect && <CheckCircle2 className="w-5 h-5 text-success-500 flex-shrink-0" />}
                      {isWrong && <XCircle className="w-5 h-5 text-danger-500 flex-shrink-0" />}
                    </span>
                  </button>
                );
              })}
            </div>

            {selected && q.explanation && (
              <div className="p-4 bg-primary-50 dark:bg-primary-900/20 rounded-xl border border-primary-200 dark:border-primary-700">
                <p className="text-sm text-primary-700 dark:text-primary-300">
                  <span className="font-bold">💡 Explanation: </span>
                  {q.explanation}
                </p>
              </div>
            )}

            <button
              onClick={next}
              disabled={!selected || submitting}
              className="btn-primary btn-md w-full disabled:opacity-40"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin inline mr-2" /> Grading...
                </>
              ) : (
                <>
                  {current + 1 === questions.length ? "Finish Quiz" : "Next Question"}{" "}
                  <ChevronRight className="w-4 h-4 inline ml-1" />
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </AppLayout>
  );
}