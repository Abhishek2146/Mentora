import { useState, useEffect, useRef } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { Trophy, Clock, BookOpen, AlertTriangle, Loader2 } from "lucide-react";
import apiClient from "@/lib/api";
import { quizService } from "@/services/quizService";
import { syllabusService } from "@/services/syllabusService";

const questionCounts = [10, 20, 30];
const durations = [
  { label: "15 min", value: 15 },
  { label: "45 min", value: 45 },
  { label: "90 min", value: 90 },
];

export default function ExamSimulator() {
  const [syllabi, setSyllabi] = useState<any[]>([]);
  const [syllabusId, setSyllabusId] = useState<number | "">("");
  const [numQuestions, setNumQuestions] = useState(20);
  const [durationMinutes, setDurationMinutes] = useState(45);

  const [exam, setExam] = useState<any>(null);
  const [questions, setQuestions] = useState<any[]>([]);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [started, setStarted] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);
  const [generating, setGenerating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const submittingRef = useRef(false);

  useEffect(() => {
    syllabusService
      .getAllSyllabi()
      .then(setSyllabi)
      .catch(() => {});
  }, []);

  // Countdown + auto-submit
  useEffect(() => {
    if (!started || result || !exam) return;
    if (timeLeft <= 0) {
      handleSubmit();
      return;
    }
    const t = setTimeout(() => setTimeLeft((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [started, timeLeft, exam]);

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const res = await apiClient.post("/api/v1/exams/generate", {
        syllabus_id: (syllabusId as number) || null,
        num_questions: numQuestions,
        duration_minutes: durationMinutes,
      }, { timeout: 300000 });
      setExam(res.data.quiz);
      setQuestions(res.data.questions || []);
      setAnswers({});
      setResult(null);
      setTimeLeft((res.data.quiz?.time_limit || durationMinutes * 60));
      setStarted(true);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to generate the exam");
    } finally {
      setGenerating(false);
    }
  }

  async function handleSubmit() {
    if (!exam || submittingRef.current) return;
    submittingRef.current = true;
    setSubmitting(true);
    try {
      const payload = questions.map((q) => ({
        question_id: q.id,
        selected: answers[q.id] ?? null,
      }));
      const res = await quizService.submitQuiz(exam.id, payload, exam.time_limit - timeLeft);
      setResult(res);
    } catch {
      setError("Failed to submit the exam. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const answered = Object.keys(answers).length;
  const score = result ? result.correct : 0;
  const pct = result ? result.score : 0;

  if (result) return (
    <AppLayout title="Exam Simulator">
      <div className="max-w-xl mx-auto card p-6 sm:p-10 flex flex-col items-center gap-6 text-center">
        <div className={`w-20 h-20 sm:w-24 sm:h-24 rounded-full flex items-center justify-center text-white text-2xl sm:text-3xl font-black ${ pct >= 60 ? "bg-gradient-to-br from-success-400 to-success-600" : "bg-gradient-to-br from-danger-400 to-danger-600" }`}>
          {pct}%
        </div>
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-800 dark:text-slate-100">{pct >= 60 ? "🎉 Passed!" : "📚 Keep Practicing"}</h2>
          <p className="text-slate-500 mt-1">{score}/{questions.length} correct</p>
        </div>
        {result.results && (
          <div className="w-full space-y-2 text-left max-h-96 overflow-y-auto">
            {result.results.map((r: any) => (
              <div key={r.question_id} className={`p-3 rounded-xl border text-sm ${r.is_correct ? "border-emerald-200 bg-emerald-50 dark:bg-emerald-900/20" : "border-red-200 bg-red-50 dark:bg-red-900/20"}`}>
                <p className="font-medium">{r.is_correct ? "✓" : "✗"} {r.question}</p>
                {!r.is_correct && <p className="text-xs text-slate-500 mt-1">Correct: {r.correct_answer}</p>}
              </div>
            ))}
          </div>
        )}
        <button onClick={() => { setStarted(false); setExam(null); setResult(null); }} className="btn-primary btn-lg">
          New Exam
        </button>
      </div>
    </AppLayout>
  );

  if (!started || !exam) return (
    <AppLayout title="Exam Simulator">
      <div className="max-w-xl mx-auto space-y-6">
        <div className="card p-5 sm:p-8 flex flex-col items-center gap-6 text-center">
          <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center shadow-glow-primary">
            <Trophy className="w-10 h-10 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Mock Exam</h2>
            <p className="text-slate-500 mt-2">
              AI-generated from your syllabus. {numQuestions} questions • {durationMinutes} minutes
            </p>
          </div>
          <div className="grid grid-cols-3 gap-4 w-full">
            {[{ label: "Questions", value: numQuestions, icon: BookOpen }, { label: "Time", value: `${durationMinutes} min`, icon: Clock }, { label: "Pass Mark", value: "60%", icon: Trophy }].map(s => (
              <div key={s.label} className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-3 text-center">
                <s.icon className="w-5 h-5 text-primary-500 mx-auto mb-1" />
                <p className="font-bold text-slate-800 dark:text-slate-100">{s.value}</p>
                <p className="text-xs text-slate-400">{s.label}</p>
              </div>
            ))}
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <div className="w-full space-y-3 text-left">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Syllabus</label>
              <select
                value={syllabusId}
                onChange={(e) => setSyllabusId(Number(e.target.value) || "")}
                className="w-full border rounded-xl px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-600"
              >
                <option value="">Latest syllabus (auto)</option>
                {syllabi.map((s) => (
                  <option key={s.id} value={s.id}>{s.title}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Number of questions</label>
              <div className="flex gap-2">
                {questionCounts.map((n) => (
                  <button key={n} onClick={() => setNumQuestions(n)} className={`flex-1 px-4 py-2 rounded-xl text-sm font-medium border transition-all ${ numQuestions===n ? "bg-primary-500 text-white border-primary-500" : "border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-primary-300" }`}>{n}</button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Duration</label>
              <div className="flex gap-2">
                {durations.map((d) => (
                  <button key={d.value} onClick={() => setDurationMinutes(d.value)} className={`flex-1 px-4 py-2 rounded-xl text-sm font-medium border transition-all ${ durationMinutes===d.value ? "bg-primary-500 text-white border-primary-500" : "border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-primary-300" }`}>{d.label}</button>
                ))}
              </div>
            </div>
          </div>
          <div className="flex items-start gap-2 p-3 bg-warning-50 dark:bg-yellow-900/20 rounded-xl text-sm text-warning-700 dark:text-yellow-300 w-full">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            Do not refresh the page once the exam starts. Timer cannot be paused.
          </div>
          <button onClick={handleGenerate} disabled={generating} className="btn-primary btn-lg w-full disabled:opacity-40">
            {generating ? (<><Loader2 className="w-5 h-5 animate-spin inline mr-2" /> Generating exam…</>) : "Generate & Start Exam"}
          </button>
        </div>
      </div>
    </AppLayout>
  );

  return (
    <AppLayout title="Exam Simulator">
      <div className="max-w-3xl mx-auto space-y-4 sticky-wrapper">
        <div className="card p-4 flex items-center justify-between">
          <span className="font-medium text-slate-600 dark:text-slate-400">{answered}/{questions.length} answered</span>
          <div className={`flex items-center gap-2 font-mono font-bold ${ timeLeft < 300 ? "text-danger-600" : "text-warning-600" }`}>
            <Clock className="w-4 h-4" />
            {Math.floor(timeLeft/60).toString().padStart(2,"0")}:{(timeLeft%60).toString().padStart(2,"0")}
          </div>
          <button onClick={handleSubmit} disabled={submitting} className="btn-primary btn-sm disabled:opacity-40">
            {submitting ? "Submitting…" : "Submit Exam"}
          </button>
        </div>
        <div className="space-y-4">
          {questions.map((q, i) => (
            <div key={q.id} className="card p-5">
              <p className="font-semibold text-slate-800 dark:text-slate-100 mb-4">{i+1}. {q.question_text}</p>
              <div className="space-y-2">
                {q.options?.map((opt: string) => (
                  <button key={opt} onClick={() => setAnswers({...answers, [q.id]: opt})}
                    className={`w-full text-left p-3 rounded-xl border text-sm transition-all ${
                      answers[q.id]===opt ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300" : "border-slate-200 dark:border-slate-600 hover:border-primary-300"
                    }`}>{opt}</button>
                ))}
              </div>
            </div>
          ))}
        </div>
        <button onClick={handleSubmit} disabled={submitting} className="btn-primary btn-lg w-full disabled:opacity-40">
          {submitting ? "Submitting…" : "Submit Exam"}
        </button>
      </div>
    </AppLayout>
  );
}
