import { useState, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import {
  Code2,
  Play,
  CheckCircle2,
  XCircle,
  ChevronRight,
  Sparkles,
  Loader2,
  Lightbulb,
} from "lucide-react";
import { codingService } from "@/services/codingService";
import { syllabusService } from "@/services/syllabusService";
import type { CodingProblem, CodingSubmission } from "@/types";

const LANGUAGES = ["python", "javascript", "java", "cpp", "c", "go", "rust"];

export default function CodingPractice() {
  const [problems, setProblems] = useState<CodingProblem[]>([]);
  const [selected, setSelected] = useState<CodingProblem | null>(null);
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("python");
  const [result, setResult] = useState<CodingSubmission | null>(null);
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showHint, setShowHint] = useState(false);

  const [syllabi, setSyllabi] = useState<any[]>([]);
  const [syllabusId, setSyllabusId] = useState<number | "">("");
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState<"easy" | "medium" | "hard">("medium");
  const [genLanguage, setGenLanguage] = useState("python");
  const [generating, setGenerating] = useState(false);
  const [showGenerate, setShowGenerate] = useState(false);

  async function loadProblems() {
    setLoading(true);
    setError(null);
    try {
      const data = await codingService.getProblems();
      setProblems(data || []);
    } catch (e: any) {
      setProblems([]);
      setError(e?.response?.data?.detail || "Failed to load coding problems.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProblems();
    syllabusService.getAllSyllabi().then(setSyllabi).catch(() => {});
  }, []);

  const selectProblem = (p: CodingProblem) => {
    setSelected(p);
    setCode(p.starter_code || "");
    setLanguage(p.language || "python");
    setResult(null);
    setShowHint(false);
    setError(null);
  };

  const run = async () => {
    if (!selected) return;
    setRunning(true);
    setError(null);
    try {
      const res = await codingService.submitCode(selected.id, code, language);
      setResult(res);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      setError(
        typeof detail === "string" && detail
          ? detail
          : e?.message || "Failed to run code."
      );
      setResult(null);
    } finally {
      setRunning(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const problem = await codingService.generateProblem({
        topic: topic.trim() || undefined,
        syllabus_id: (syllabusId as number) || undefined,
        difficulty,
        language: genLanguage,
      });
      setShowGenerate(false);
      await loadProblems();
      selectProblem(problem);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      setError(
        typeof detail === "string" && detail
          ? detail
          : e?.message || "Failed to generate coding problem."
      );
    } finally {
      setGenerating(false);
    }
  };

  const diffColor = (d: string) =>
    d === "easy" ? "badge-green" : d === "hard" ? "badge-red" : "badge-yellow";

  return (
    <AppLayout title="Coding Practice">
      <div className="max-w-6xl mx-auto space-y-4">
        {error && (
          <div className="card p-3 border-danger-200 bg-danger-50 dark:bg-danger-900/20 text-sm text-danger-700 dark:text-danger-300">
            {error}
          </div>
        )}

        {!selected ? (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="font-bold text-xl text-slate-800 dark:text-slate-100">
                  Coding Practice
                </h2>
                <p className="text-sm text-slate-500 mt-1">
                  Solve AI-generated problems with stdin/stdout test cases.
                </p>
              </div>
              <button
                onClick={() => setShowGenerate(!showGenerate)}
                className="btn-primary btn-md"
              >
                <Sparkles className="w-4 h-4" />
                Generate Problem
              </button>
            </div>

            {showGenerate && (
              <div className="card p-4 sm:p-5 space-y-4">
                <h3 className="font-bold text-slate-800 dark:text-slate-100">
                  Generate a new problem
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-slate-500">Topic</label>
                    <input
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      placeholder="e.g. Binary search, Recursion"
                      className="input w-full mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-500">Syllabus</label>
                    <select
                      value={syllabusId}
                      onChange={(e) =>
                        setSyllabusId(e.target.value ? Number(e.target.value) : "")
                      }
                      className="input w-full mt-1"
                    >
                      <option value="">Optional — use latest syllabus</option>
                      {syllabi.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.title}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-500">Difficulty</label>
                    <select
                      value={difficulty}
                      onChange={(e) =>
                        setDifficulty(e.target.value as "easy" | "medium" | "hard")
                      }
                      className="input w-full mt-1"
                    >
                      <option value="easy">Easy</option>
                      <option value="medium">Medium</option>
                      <option value="hard">Hard</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-500">Language</label>
                    <select
                      value={genLanguage}
                      onChange={(e) => setGenLanguage(e.target.value)}
                      className="input w-full mt-1"
                    >
                      {LANGUAGES.map((lang) => (
                        <option key={lang} value={lang}>
                          {lang}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <button
                  onClick={handleGenerate}
                  disabled={generating}
                  className="btn-primary btn-md"
                >
                  {generating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" /> Generating…
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" /> Generate with AI
                    </>
                  )}
                </button>
              </div>
            )}

            {loading ? (
              <div className="flex items-center justify-center py-16 text-slate-500">
                <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading problems…
              </div>
            ) : problems.length === 0 ? (
              <div className="card p-8 text-center text-slate-500">
                <Code2 className="w-10 h-10 mx-auto mb-3 opacity-40" />
                <p>No coding problems yet. Generate one to get started.</p>
              </div>
            ) : (
              problems.map((p) => (
                <div
                  key={p.id}
                  onClick={() => selectProblem(p)}
                  className="card p-4 sm:p-5 cursor-pointer hover:shadow-soft hover:-translate-y-0.5 transition-all"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h3 className="font-bold text-slate-800 dark:text-slate-100">
                        {p.title}
                      </h3>
                      <p className="text-sm text-slate-500 mt-1 line-clamp-2">
                        {p.description}
                      </p>
                      <div className="flex flex-wrap gap-2 mt-2">
                        <span className={`badge ${diffColor(p.difficulty)}`}>
                          {p.difficulty}
                        </span>
                        <span className="badge-blue">{p.language}</span>
                        {p.is_ai_generated && (
                          <span className="badge-purple">AI</span>
                        )}
                        {p.tags?.map((t) => (
                          <span key={t} className="badge-blue">
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-slate-400 flex-shrink-0" />
                  </div>
                </div>
              ))
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
            <div className="space-y-4">
              <button onClick={() => setSelected(null)} className="btn-ghost btn-sm">
                ← Back to problems
              </button>
              <div className="card p-4 sm:p-5 space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <h2 className="font-bold text-lg text-slate-800 dark:text-slate-100">
                    {selected.title}
                  </h2>
                  <span className={`badge ${diffColor(selected.difficulty)}`}>
                    {selected.difficulty}
                  </span>
                </div>
                <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {selected.description}
                </p>

                {selected.input_format && (
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase">Input</p>
                    <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
                      {selected.input_format}
                    </p>
                  </div>
                )}
                {selected.output_format && (
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase">Output</p>
                    <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
                      {selected.output_format}
                    </p>
                  </div>
                )}
                {selected.constraints && (
                  <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-xl">
                    <p className="text-xs font-semibold text-slate-500 uppercase mb-1">
                      Constraints
                    </p>
                    <p className="text-xs font-mono text-slate-600 dark:text-slate-300">
                      {selected.constraints}
                    </p>
                  </div>
                )}

                {selected.examples && selected.examples.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs font-semibold text-slate-500 uppercase">Examples</p>
                    {selected.examples.map((ex, i) => (
                      <div
                        key={i}
                        className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-xl text-xs font-mono"
                      >
                        {ex.input !== undefined && (
                          <p>
                            <span className="text-slate-500">Input: </span>
                            {ex.input}
                          </p>
                        )}
                        {ex.output !== undefined && (
                          <p className="mt-1">
                            <span className="text-slate-500">Output: </span>
                            {ex.output}
                          </p>
                        )}
                        {ex.explanation && (
                          <p className="mt-1 text-slate-500 font-sans">{ex.explanation}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {selected.hints && selected.hints.length > 0 && (
                  <div>
                    <button
                      onClick={() => setShowHint(!showHint)}
                      className="btn-ghost btn-sm"
                    >
                      <Lightbulb className="w-4 h-4" />
                      {showHint ? "Hide hints" : "Show hints"}
                    </button>
                    {showHint && (
                      <ul className="mt-2 space-y-1 text-sm text-slate-600 dark:text-slate-300 list-disc pl-5">
                        {selected.hints.map((hint, i) => (
                          <li key={i}>{hint}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-4">
              <div className="card overflow-hidden">
                <div className="flex items-center justify-between gap-2 px-4 py-2 bg-slate-800 border-b border-slate-700">
                  <div className="flex items-center gap-2">
                    <Code2 className="w-4 h-4 text-slate-400" />
                    <span className="text-sm text-slate-300">Code Editor</span>
                  </div>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="text-xs bg-slate-700 text-slate-200 border-0 rounded px-2 py-1"
                  >
                    {LANGUAGES.map((lang) => (
                      <option key={lang} value={lang}>
                        {lang}
                      </option>
                    ))}
                  </select>
                </div>
                <textarea
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className="w-full p-3 sm:p-4 font-mono text-xs sm:text-sm bg-slate-900 text-slate-100 resize-none focus:outline-none"
                  rows={14}
                  spellCheck={false}
                />
              </div>

              <button onClick={run} disabled={running} className="btn-primary btn-md w-full">
                {running ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Running…
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" /> Run & Submit
                  </>
                )}
              </button>

              {result && (
                <div
                  className={`card p-4 ${
                    result.status === "passed"
                      ? "border-success-200 bg-success-50 dark:bg-success-900/20"
                      : "border-danger-200 bg-danger-50 dark:bg-danger-900/20"
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    {result.status === "passed" ? (
                      <CheckCircle2 className="w-5 h-5 text-success-500" />
                    ) : (
                      <XCircle className="w-5 h-5 text-danger-500" />
                    )}
                    <span className="font-bold text-sm capitalize">{result.status}</span>
                    <span className="text-xs text-slate-500 ml-auto">
                      {result.passed_test_cases}/{result.total_test_cases} tests passed
                      {result.execution_time != null && ` · ${result.execution_time}ms`}
                    </span>
                  </div>
                  {result.score > 0 && (
                    <p className="text-xs text-slate-500 mb-2">Score: {result.score}%</p>
                  )}
                  <pre className="overflow-x-auto text-xs font-mono text-slate-600 dark:text-slate-300 whitespace-pre-wrap">
                    {result.output}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
