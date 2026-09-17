import { useMemo, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, FileSearch, Info, Loader2, Sparkles } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { aiDetectionService, DetectionResult } from "@/services/aiDetectionService";

const MIN_CHARS = 40;

function verdictCopy(result: DetectionResult) {
  if (result.verdict === "likely_ai") {
    return { label: "Likely AI-generated", tone: "text-amber-700 dark:text-amber-300", bar: "bg-amber-500", icon: AlertTriangle };
  }
  if (result.verdict === "likely_human") {
    return { label: "Likely human-written", tone: "text-emerald-700 dark:text-emerald-300", bar: "bg-emerald-500", icon: CheckCircle2 };
  }
  return { label: "Mixed or uncertain", tone: "text-sky-700 dark:text-sky-300", bar: "bg-sky-500", icon: Info };
}

export default function AIDetection() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const analysisRequestRef = useRef(0);

  const wordCount = useMemo(() => text.trim() ? text.trim().split(/\s+/).length : 0, [text]);
  const canAnalyze = text.trim().length >= MIN_CHARS && text.trim().length <= 12000;
  const meta = result ? verdictCopy(result) : null;
  const ResultIcon = meta?.icon;

  const handleTextChange = (value: string) => {
    analysisRequestRef.current += 1;
    setText(value);
    setResult(null);
    setError("");
    setLoading(false);
  };

  const handleAnalyze = async () => {
    const submittedText = text.trim();
    if (submittedText.length < MIN_CHARS) {
      setError(`Add at least ${MIN_CHARS} characters for a meaningful estimate.`);
      return;
    }
    setError("");
    setLoading(true);
    const requestId = ++analysisRequestRef.current;
    try {
      const detection = await aiDetectionService.analyze(submittedText);
      if (requestId === analysisRequestRef.current) {
        setResult(detection);
      }
    } catch (err: any) {
      if (requestId === analysisRequestRef.current) {
        setResult(null);
        setError(err?.response?.data?.detail || "The detector is unavailable right now. Please try again.");
      }
    } finally {
      if (requestId === analysisRequestRef.current) {
        setLoading(false);
      }
    }
  };

  return (
    <AppLayout title="AI Detection">
      <div className="max-w-6xl mx-auto space-y-6">
        <section className="relative overflow-hidden rounded-2xl border border-primary-100 bg-gradient-to-r from-primary-50 via-white to-secondary-50 p-4 shadow-sm dark:border-primary-900/40 dark:from-primary-950/40 dark:via-slate-900 dark:to-secondary-950/30 sm:p-5">
          <div className="absolute -right-12 -top-16 h-40 w-40 rounded-full bg-primary-200/40 blur-3xl dark:bg-primary-500/10" />
          <div className="relative max-w-3xl">
            <div className="mb-1.5 flex items-center gap-2 text-primary-600 dark:text-primary-300 text-[11px] font-bold uppercase tracking-widest">
              <Sparkles className="h-3 w-3" /> Writing insight
            </div>
            <h1 className="text-xl sm:text-2xl font-black tracking-tight text-slate-800 dark:text-slate-100">Could this text be AI-generated?</h1>
            <p className="mt-1.5 max-w-2xl text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              Paste an essay, answer, or draft to get a transparent likelihood estimate. Use it as a reflection tool—not as proof of authorship.
            </p>
          </div>
        </section>

        <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <section className="card p-5 sm:p-7">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">Paste your text</h2>
                <p className="mt-1 text-sm text-slate-500">Longer passages produce more useful signals.</p>
              </div>
              <FileSearch className="h-5 w-5 text-primary-500" />
            </div>
            <textarea
              value={text}
              onChange={(event) => handleTextChange(event.target.value)}
              placeholder="Paste an essay, discussion response, or study draft here..."
              className="input min-h-[320px] resize-y p-4 leading-relaxed"
              maxLength={12000}
              aria-label="Text to analyze"
            />
            <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
              <span>{wordCount} words</span>
              <span>{text.length.toLocaleString()} / 12,000 characters</span>
            </div>
            {error && <div className="mt-4 rounded-xl border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">{error}</div>}
            <button
              type="button"
              onClick={handleAnalyze}
              disabled={!canAnalyze || loading}
              className="btn-primary btn-md mt-5 w-full sm:w-auto"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {loading ? "Analyzing..." : "Analyze text"}
            </button>
            {text.trim().length > 0 && text.trim().length < MIN_CHARS && (
              <p className="mt-2 text-xs text-slate-400">Add {MIN_CHARS - text.trim().length} more characters to enable analysis.</p>
            )}
          </section>

          <section className="card p-5 sm:p-7">
            {!result || !meta || !ResultIcon ? (
              <div className="flex min-h-[420px] flex-col items-center justify-center text-center">
                <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-50 text-primary-600 dark:bg-primary-950/50 dark:text-primary-300">
                  <FileSearch className="h-8 w-8" />
                </div>
                <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">Your result will appear here</h2>
                <p className="mt-2 max-w-xs text-sm leading-relaxed text-slate-500">Submit at least {MIN_CHARS} characters to see an estimate, confidence level, and the signals behind it.</p>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-widest text-slate-400">Estimate</p>
                    <div className={`mt-2 flex items-center gap-2 ${meta.tone}`}><ResultIcon className="h-5 w-5" /><span className="font-bold">{meta.label}</span></div>
                  </div>
                  <div className="text-right"><span className="text-4xl font-black text-slate-800 dark:text-white">{result.score}%</span><p className="text-xs text-slate-400">AI likelihood</p></div>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"><div className={`h-full rounded-full transition-all duration-500 ${meta.bar}`} style={{ width: `${result.score}%` }} /></div>
                <div className="rounded-2xl bg-slate-50 p-4 dark:bg-slate-800/60"><p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{result.summary}</p><p className="mt-3 text-xs font-semibold text-slate-400">Confidence: {result.confidence}%</p></div>
                <div><h3 className="mb-3 font-bold text-slate-800 dark:text-slate-100">Signals considered</h3><div className="space-y-3">{result.signals.map((signal) => <div key={`${signal.name}-${signal.explanation}`} className="rounded-xl border border-slate-100 p-3 dark:border-slate-700"><p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{signal.name}</p><p className="mt-1 text-xs leading-relaxed text-slate-500">{signal.explanation}</p></div>)}</div></div>
                <p className="border-t border-slate-100 pt-4 text-xs leading-relaxed text-slate-400 dark:border-slate-700">{result.disclaimer}</p>
              </div>
            )}
          </section>
        </div>
      </div>
    </AppLayout>
  );
}
