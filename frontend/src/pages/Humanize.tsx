import { useMemo, useState } from "react";
import {
  Check,
  ClipboardCopy,
  Copy,
  Loader2,
  MessageSquareHeart,
  PenLine,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import {
  humanizeService,
  HumanizeIntensity,
  HumanizeResponse,
} from "@/services/humanizeService";

const MIN_CHARS = 40;
const MAX_CHARS = 12000;

const INTENSITY_OPTIONS: { id: HumanizeIntensity; label: string; description: string }[] = [
  { id: "subtle", label: "Subtle", description: "Light touch, keeps most wording" },
  { id: "balanced", label: "Balanced", description: "Smooths phrasing into natural prose" },
  { id: "strong", label: "Strong", description: "Rewrites freely, meaning preserved" },
];

export default function Humanize() {
  const [text, setText] = useState("");
  const [intensity, setIntensity] = useState<HumanizeIntensity>("balanced");
  const [result, setResult] = useState<HumanizeResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const wordCount = useMemo(() => (text.trim() ? text.trim().split(/\s+/).length : 0), [text]);
  const canHumanize = text.trim().length >= MIN_CHARS && text.trim().length <= MAX_CHARS;

  const handleTextChange = (value: string) => {
    setText(value);
    setResult(null);
    setError("");
    setLoading(false);
    setCopied(false);
  };

  const handleHumanize = async () => {
    const submitted = text.trim();
    if (submitted.length < MIN_CHARS) {
      setError(`Add at least ${MIN_CHARS} characters for a meaningful rewrite.`);
      return;
    }
    setError("");
    setLoading(true);
    try {
      const humanized = await humanizeService.humanizeText(submitted, intensity);
      setResult(humanized);
      setCopied(false);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "The humanizer is unavailable right now. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.humanized_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setError("Could not copy to the clipboard. Select the text and copy it manually.");
    }
  };

  const handleCopyOriginal = () => {
    if (text.trim()) {
      navigator.clipboard?.writeText(text).catch(() => undefined);
    }
  };

  return (
    <AppLayout title="Humanize">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="relative overflow-hidden rounded-2xl border border-primary-100 bg-gradient-to-r from-primary-50 via-white to-secondary-50 p-4 shadow-sm dark:border-primary-900/40 dark:from-primary-950/40 dark:via-slate-900 dark:to-secondary-950/30 sm:p-5">
          <div className="absolute -right-12 -top-16 h-40 w-40 rounded-full bg-secondary-200/40 blur-3xl dark:bg-secondary-500/10" />
          <div className="relative max-w-3xl">
            <div className="mb-1.5 flex items-center gap-2 text-secondary-600 dark:text-secondary-300 text-[11px] font-bold uppercase tracking-widest">
              <MessageSquareHeart className="h-3 w-3" /> Writing polish
            </div>
            <h1 className="text-xl font-black tracking-tight text-slate-800 dark:text-slate-100 sm:text-2xl">
              Make your writing sound more human
            </h1>
            <p className="mt-1.5 max-w-2xl text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              Paste a stiff, formulaic, or machine-like draft and get a natural rewrite that keeps
              your meaning and facts intact. A companion to AI Detection — use it to polish your
              own drafts, not to pass off someone else's work as yours.
            </p>
          </div>
        </section>

        <div className="card overflow-hidden">
          <div className="border-b border-slate-200 p-4 sm:p-6 dark:border-slate-700">
            <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
              <div className="flex flex-col">
                <textarea
                  value={text}
                  onChange={(event) => handleTextChange(event.target.value)}
                  placeholder="Paste an AI-generated draft, essay, or study summary here..."
                  className="input min-h-[320px] max-h-[420px] resize-y p-4 leading-relaxed"
                  maxLength={MAX_CHARS}
                  aria-label="Text to humanize"
                />
                <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                  <span>{wordCount} words</span>
                  <span>{text.length.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters</span>
                </div>

                <div className="mt-4">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-400">Rewrite strength</p>
                  <div className="grid gap-2 sm:grid-cols-3">
                    {INTENSITY_OPTIONS.map((option) => (
                      <button
                        key={option.id}
                        type="button"
                        onClick={() => setIntensity(option.id)}
                        className={`rounded-xl border p-3 text-left transition-colors ${
                          intensity === option.id
                            ? "border-primary-400 bg-primary-50 dark:border-primary-600 dark:bg-primary-950/40"
                            : "border-slate-200 hover:border-primary-200 dark:border-slate-700 dark:hover:border-primary-800"
                        }`}
                      >
                        <p className={`text-sm font-bold ${intensity === option.id ? "text-primary-700 dark:text-primary-300" : "text-slate-700 dark:text-slate-200"}`}>
                          {option.label}
                        </p>
                        <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">{option.description}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {error && <div className="mt-4 rounded-xl border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">{error}</div>}

                <button
                  type="button"
                  onClick={handleHumanize}
                  disabled={!canHumanize || loading}
                  className="btn-primary btn-md mt-5 w-full sm:w-auto"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  {loading ? "Rewriting..." : "Humanize text"}
                </button>
                {text.trim().length > 0 && text.trim().length < MIN_CHARS && (
                  <p className="mt-2 text-xs text-slate-400">Add {MIN_CHARS - text.trim().length} more characters to enable rewriting.</p>
                )}
              </div>

              <section className="card p-5 bg-white dark:bg-slate-900">
                {!result ? (
                  <div className="flex min-h-[420px] flex-col items-center justify-center text-center">
                    <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-secondary-50 text-secondary-600 dark:bg-secondary-950/50 dark:text-secondary-300">
                      <PenLine className="h-8 w-8" />
                    </div>
                    <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">Your rewrite will appear here</h2>
                    <p className="mt-2 max-w-xs text-sm leading-relaxed text-slate-500">
                      Submit at least {MIN_CHARS} characters to see a natural rewrite of your text, with a
                      short summary of what changed.
                    </p>
                  </div>
                ) : (
                  <div className="flex h-full flex-col space-y-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold uppercase tracking-widest text-slate-400">Rewritten text</p>
                        <p className="mt-0.5 text-xs capitalize text-slate-500">{intensity} rewrite</p>
                      </div>
                      <button type="button" onClick={handleCopy} disabled={copied} className="btn-ghost btn-sm">
                        {copied ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
                        {copied ? "Copied" : "Copy"}
                      </button>
                    </div>

                    <div className="max-h-[420px] overflow-auto rounded-xl border border-slate-200 bg-slate-50 p-4 text-[15px] leading-relaxed text-slate-700 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-200">
                      {result.humanized_text.split("\n").map((paragraph, index) => (
                        <p key={index} className={index > 0 ? "mt-3" : ""}>{paragraph}</p>
                      ))}
                    </div>

                    <div className="rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm text-sky-800 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-200">
                      <p className="text-xs font-bold uppercase tracking-widest">What changed</p>
                      <p className="mt-1 text-xs leading-relaxed">{result.summary}</p>
                    </div>

                    <button
                      type="button"
                      onClick={handleCopyOriginal}
                      className="btn-ghost btn-sm self-end"
                      title="Copy your original text back to the input for comparison"
                    >
                      <ClipboardCopy className="h-4 w-4" /> Copy original
                    </button>

                    <p className="border-t border-slate-100 pt-3 text-xs leading-relaxed text-slate-400 dark:border-slate-700">{result.disclaimer}</p>
                  </div>
                )}
              </section>
            </div>
          </div>

          <div className="border-t border-slate-100 p-4 dark:border-slate-700">
            <p className="flex items-center gap-2 text-xs text-slate-400">
              <RefreshCw className="h-3.5 w-3.5" />
              Humanize rewrites wording, rhythm, and transitions — it never invents facts, statistics, or sources.
            </p>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}