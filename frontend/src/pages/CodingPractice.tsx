import { useState, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { Code2, Play, CheckCircle2, XCircle, ChevronRight } from "lucide-react";
import { codingService } from "@/services/codingService";

export default function CodingPractice() {
  const [problems, setProblems] = useState<any[]>([]);
  const [selected, setSelected] = useState<any | null>(null);
  const [code, setCode] = useState("");
  const [result, setResult] = useState<any>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => { codingService.getProblems().then(setProblems); }, []);

  const selectProblem = (p: any) => { setSelected(p); setCode(p.starter_code || ""); setResult(null); };

  const run = async () => {
    if (!selected) return;
    setRunning(true);
    const res = await codingService.runCode(selected.id, code, "sql");
    setResult(res);
    setRunning(false);
  };

  const diffColor = (d: string) => d === "easy" ? "badge-green" : d === "hard" ? "badge-red" : "badge-yellow";

  return (
    <AppLayout title="Coding Practice">
      <div className="max-w-6xl mx-auto">
        {!selected ? (
          <div className="space-y-4">
            <h2 className="font-bold text-xl text-slate-800 dark:text-slate-100">SQL & Coding Problems</h2>
            {problems.map(p => (
              <div key={p.id} onClick={() => selectProblem(p)}
                className="card p-4 sm:p-5 cursor-pointer hover:shadow-soft hover:-translate-y-0.5 transition-all">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h3 className="font-bold text-slate-800 dark:text-slate-100">{p.title}</h3>
                    <p className="text-sm text-slate-500 mt-1">{p.description.slice(0, 100)}…</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      <span className={`badge ${diffColor(p.difficulty)}`}>{p.difficulty}</span>
                      {p.tags?.map((t: string) => <span key={t} className="badge-blue">{t}</span>)}
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-400 flex-shrink-0" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
            <div className="space-y-4">
              <button onClick={() => setSelected(null)} className="btn-ghost btn-sm">← Back to problems</button>
              <div className="card p-4 sm:p-5">
                <div className="flex items-start justify-between gap-3 mb-3">
                  <h2 className="font-bold text-lg text-slate-800 dark:text-slate-100">{selected.title}</h2>
                  <span className={`badge ${diffColor(selected.difficulty)}`}>{selected.difficulty}</span>
                </div>
                <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">{selected.description}</p>
                {selected.constraints && (
                  <div className="mt-4 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-xl">
                    <p className="text-xs font-mono text-slate-600 dark:text-slate-300">{selected.constraints}</p>
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-4">
              <div className="card overflow-hidden">
                <div className="flex items-center gap-2 px-4 py-2 bg-slate-800 border-b border-slate-700">
                  <Code2 className="w-4 h-4 text-slate-400" />
                  <span className="text-sm text-slate-300">SQL Editor</span>
                </div>
                <textarea
                  value={code}
                  onChange={e => setCode(e.target.value)}
                  className="w-full p-3 sm:p-4 font-mono text-xs sm:text-sm bg-slate-900 text-slate-100 resize-none focus:outline-none"
                  rows={12}
                  spellCheck={false}
                />
              </div>

              <button onClick={run} disabled={running} className="btn-primary btn-md w-full">
                <Play className="w-4 h-4" /> {running ? "Running…" : "Run Code"}
              </button>

              {result && (
                <div className={`card p-4 ${result.status==="passed" ? "border-success-200 bg-success-50 dark:bg-success-900/20" : "border-danger-200 bg-danger-50 dark:bg-danger-900/20"}`}>
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    {result.status==="passed" ? <CheckCircle2 className="w-5 h-5 text-success-500" /> : <XCircle className="w-5 h-5 text-danger-500" />}
                    <span className="font-bold text-sm capitalize">{result.status}</span>
                    <span className="text-xs text-slate-500 ml-auto">{result.passed_tests}/{result.total_tests} tests passed</span>
                  </div>
                  <pre className="overflow-x-auto text-xs font-mono text-slate-600 dark:text-slate-300">{result.output}</pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
