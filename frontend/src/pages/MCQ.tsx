import { useState, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { ChevronRight, Shuffle, Loader2, RefreshCw } from "lucide-react";
import { quizService } from "@/services/quizService";
import { syllabusService } from "@/services/syllabusService";

const difficulties = ["easy", "medium", "hard"];

export default function MCQ() {
  const [syllabi, setSyllabi] = useState<any[]>([]);
  const [topics, setTopics] = useState<string[]>([]);
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState("medium");
  const [count, setCount] = useState(5);

  const [quizId, setQuizId] = useState<number | null>(null);
  const [questions, setQuestions] = useState<any[]>([]);
  const [current, setCurrent] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [answers, setAnswers] = useState<{ question_id: number; selected: string }[]>([]);
  const [result, setResult] = useState<any>(null);
  const [started, setStarted] = useState(false);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<number>(Date.now());

  useEffect(() => {
    syllabusService
      .getAllSyllabi()
      .then((data) => {
        setSyllabi(data);
        // Collect chapter/topic names from all syllabi as suggestions.
        const names: string[] = [];
        for (const s of data) {
          for (const subj of s.subjects || []) {
            for (const ch of subj.chapters || []) {
              if (ch.name) names.push(ch.name);
              for (const t of ch.topics || []) if (t) names.push(t);
            }
          }
        }
        setTopics([...new Set(names)].slice(0, 24));
      })
      .catch(() => {});
  }, []);

  const start = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await quizService.generateMCQ(topic.trim(), difficulty, count);
      const qs = res?.questions || [];
      if (!qs.length) throw new Error("No questions were generated. Try another topic.");
      setQuizId(res.id ?? null);
      setQuestions(qs);
      setStarted(true);
      setCurrent(0);
      setSelected(null);
      setAnswers([]);
      setResult(null);
      setDone(false);
      setStartedAt(Date.now());
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || "Failed to generate MCQs");
    } finally {
      setLoading(false);
    }
  };

  const q = questions[current];

  const next = async () => {
    if (!selected || !q) return;
    const newAnswers = [...answers, { question_id: q.id, selected }];
    setAnswers(newAnswers);
    setSelected(null);
    if (current + 1 >= questions.length) {
      setSubmitting(true);
      try {
        if (quizId) {
          const res = await quizService.submitQuiz(
            quizId,
            newAnswers,
            Math.round((Date.now() - startedAt) / 1000)
          );
          setResult(res);
        }
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

  const correctCount = result
    ? result.correct
    : answers.filter((a) =>
        questions.some((qq) => qq.id === a.question_id && qq.correct_answer === a.selected)
      ).length;

  if (done) {
    const pct = result ? result.score : questions.length ? Math.round((correctCount / questions.length) * 100) : 0;
    return (
      <AppLayout title="MCQ Practice">
        <div className="max-w-xl mx-auto space-y-4">
          <div className="card p-10 flex flex-col items-center gap-6 text-center">
            <p className="text-5xl font-black gradient-text">{pct}%</p>
            <p className="text-slate-500">{correctCount}/{questions.length} correct on {topic || "mixed"} ({difficulty})</p>
            {!result && <p className="text-xs text-slate-400">(score could not be saved)</p>}
            {result?.results && (
              <div className="w-full space-y-2 text-left">
                {result.results.map((r: any) => (
                  <div key={r.question_id} className={`p-3 rounded-xl border text-sm ${r.is_correct ? "border-emerald-200 bg-emerald-50 dark:bg-emerald-900/20" : "border-red-200 bg-red-50 dark:bg-red-900/20"}`}>
                    <p className="font-medium">{r.is_correct ? "✓" : "✗"} {r.question}</p>
                    {!r.is_correct && (
                      <>
                        <p className="text-xs text-slate-500 mt-1">Your answer: {r.user_answer ?? "—"}</p>
                        <p className="text-xs text-slate-500">Correct: {r.correct_answer}</p>
                      </>
                    )}
                    {r.explanation && <p className="text-xs text-slate-400 mt-1">{r.explanation}</p>}
                  </div>
                ))}
              </div>
            )}
            <div className="flex gap-3">
              <button onClick={() => setStarted(false)} className="btn-outline btn-md">Change Topic</button>
              <button onClick={start} className="btn-primary btn-md"><Shuffle className="w-4 h-4" /> New Set</button>
            </div>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (!started) return (
    <AppLayout title="MCQ Practice">
      <div className="max-w-xl mx-auto space-y-6">
        <div className="card p-4 sm:p-6 space-y-5">
          <h2 className="font-bold text-xl text-slate-800 dark:text-slate-100">Configure Your Practice Set</h2>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <div>
            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">Topic</label>
            {topics.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {topics.map((t) => (
                  <button key={t} onClick={() => setTopic(t)} className={`px-4 py-2 rounded-xl text-sm font-medium border transition-all ${ topic===t ? "bg-primary-500 text-white border-primary-500" : "border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-primary-300" }`}>{t}</button>
                ))}
              </div>
            )}
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder={topics.length ? "Or type any topic..." : "e.g. Normalization"}
              className="w-full border rounded-xl px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-600"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">Difficulty</label>
            <div className="flex gap-2">
              {difficulties.map((d) => (
                <button key={d} onClick={() => setDifficulty(d)} className={`px-4 py-2 rounded-xl text-sm font-medium capitalize border transition-all ${ difficulty===d ? "bg-primary-500 text-white border-primary-500" : "border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-primary-300" }`}>{d}</button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">Questions</label>
            <select
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="w-full border rounded-xl px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-600"
            >
              {[5, 10, 15, 20].map((n) => (
                <option key={n} value={n}>{n} questions</option>
              ))}
            </select>
          </div>
          <button onClick={start} disabled={loading || !topic.trim()} className="btn-primary btn-lg w-full disabled:opacity-40">
            {loading ? (<><Loader2 className="w-5 h-5 animate-spin inline mr-2" /> Generating…</>) : (<>Start Practice <ChevronRight className="w-5 h-5 inline" /></>)}
          </button>
        </div>
      </div>
    </AppLayout>
  );

  return (
    <AppLayout title="MCQ Practice">
      <div className="max-w-xl mx-auto space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex-1 progress-bar"><div className="progress-fill bg-gradient-to-r from-primary-500 to-secondary-500" style={{ width: `${(current/questions.length)*100}%` }} /></div>
          <span className="text-sm text-slate-500">{current+1}/{questions.length}</span>
        </div>
        {q && (
          <div className="card p-6 space-y-5">
            <div className="flex items-start justify-between gap-4">
              <p className="font-semibold text-lg text-slate-800 dark:text-slate-100">{q.question_text}</p>
              <span className={`badge flex-shrink-0 ${q.difficulty === "Easy" ? "badge-green" : q.difficulty === "Hard" ? "badge-red" : "badge-yellow"}`}>{q.difficulty}</span>
            </div>
            <div className="space-y-3">
              {q.options?.map((opt: string) => (
                <button key={opt} onClick={() => !selected && setSelected(opt)}
                  className={`w-full text-left p-4 rounded-xl border-2 text-sm font-medium transition-all ${
                    selected === opt && opt === q.correct_answer ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20" :
                    selected === opt ? "border-danger-500 bg-danger-50 dark:bg-red-900/20" :
                    selected ? "border-slate-200 opacity-60" :
                    "border-slate-200 hover:border-primary-400"
                  }`}>{opt}</button>
              ))}
            </div>
            {selected && q.explanation && (
              <div className="p-4 bg-primary-50 dark:bg-primary-900/20 rounded-xl border border-primary-200 dark:border-primary-700">
                <p className="text-sm text-primary-700 dark:text-primary-300"><span className="font-bold">💡 Explanation: </span>{q.explanation}</p>
              </div>
            )}
            {selected && (
              <button onClick={next} disabled={submitting} className="btn-primary btn-md w-full disabled:opacity-40">
                {submitting ? (<><Loader2 className="w-4 h-4 animate-spin inline mr-2" /> Grading...</>) : (<>{current+1===questions.length ? "Finish" : "Next"} <ChevronRight className="w-4 h-4 inline" /></>)}
              </button>
            )}
          </div>
        )}
        <button onClick={() => { setStarted(false); setError(null); }} className="btn-ghost btn-sm w-full">
          <RefreshCw className="w-4 h-4 inline mr-1" /> Cancel practice
        </button>
      </div>
    </AppLayout>
  );
}
