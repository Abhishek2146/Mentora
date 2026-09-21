import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Download,
  FileSearch,
  FileText,
  Flame,
  Info,
  Loader2,
  MessageSquareText,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import {
  aiDetectionService,
  DetectionBase,
  DetectionLabel,
  DetectionSpan,
  PdfDetectionResponse,
  TextDetectionResponse,
} from "@/services/aiDetectionService";
import * as pdfjsLib from "pdfjs-dist";
import pdfWorkerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

const MIN_CHARS = 40;
const MAX_CHARS = 12000;
const MAX_FILE_BYTES = 25 * 1024 * 1024;
const VIEWPORT_WIDTH_PX = 640;

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

type Tab = "text" | "pdf";

type VerdictMeta = {
  label: string;
  tone: string;
  bar: string;
  icon: typeof Info;
};

function verdictFor(label: DetectionLabel): VerdictMeta {
  switch (label) {
    case "likely_human":
      return { label: "Likely human-written", tone: "text-emerald-700 dark:text-emerald-300", bar: "bg-emerald-500", icon: CheckCircle2 };
    case "uncertain":
      return { label: "Mixed or uncertain", tone: "text-sky-700 dark:text-sky-300", bar: "bg-sky-500", icon: Info };
    case "potentially_ai_generated":
      return { label: "Potentially AI-generated", tone: "text-amber-700 dark:text-amber-300", bar: "bg-amber-500", icon: AlertTriangle };
    case "strong_ai_like_signals":
      return { label: "Strong AI-like signals", tone: "text-rose-700 dark:text-rose-300", bar: "bg-rose-500", icon: Flame };
  }
}

function scoreLabel(score: number): string {
  return `${Math.round(score * 100)}%`;
}

function DistributionBar({ result }: { result: DetectionBase }) {
  const { ai_like, uncertain, human } = result.distribution;
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-xs text-slate-400">
        <span>Word-level distribution</span>
        <span>{result.analyzed_words.toLocaleString()} words analyzed</span>
      </div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div className="h-full bg-emerald-500 transition-all duration-500" style={{ width: `${human * 100}%` }} />
        <div className="h-full bg-sky-400 transition-all duration-500" style={{ width: `${uncertain * 100}%` }} />
        <div className="h-full bg-rose-500 transition-all duration-500" style={{ width: `${ai_like * 100}%` }} />
      </div>
      <div className="mt-2 flex gap-4 text-[11px] text-slate-500">
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500" /> Human-like {scoreLabel(human)}</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-sky-400" /> Uncertain {scoreLabel(uncertain)}</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-rose-500" /> AI-like {scoreLabel(ai_like)}</span>
      </div>
    </div>
  );
}

function DetectionSignals({ span }: { span: DetectionSpan }) {
  if (!span.signals || span.signals.length === 0) return null;
  return (
    <div className="mt-3 space-y-2">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">Why this passage was flagged</p>
      {span.signals.map((signal) => (
        <div key={`${signal.name}-${signal.explanation}`} className="rounded-lg border border-slate-100 bg-white p-2.5 dark:border-slate-700 dark:bg-slate-800/60">
          <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{signal.name}</p>
          <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{signal.explanation}</p>
          {signal.value !== undefined && (
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
              <div className="h-full rounded-full bg-primary-500" style={{ width: `${Math.round(signal.value * 100)}%` }} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

type HighlightSegment =
  | { kind: "plain"; text: string }
  | { kind: "flagged"; text: string; span: DetectionSpan };

function buildSegments(text: string, spans: DetectionSpan[]): HighlightSegment[] {
  if (spans.length === 0) return text ? [{ kind: "plain", text }] : [];
  const ordered = [...spans].sort((a, b) => a.start - b.start);
  const segments: HighlightSegment[] = [];
  let cursor = 0;
  for (const span of ordered) {
    if (span.start > cursor) segments.push({ kind: "plain", text: text.slice(cursor, span.start) });
    segments.push({ kind: "flagged", text: text.slice(span.start, span.end), span });
    cursor = span.end;
  }
  if (cursor < text.length) segments.push({ kind: "plain", text: text.slice(cursor) });
  return segments;
}

function HighlightedTextView({
  text,
  spans,
  selected,
  onSelect,
}: {
  text: string;
  spans: DetectionSpan[];
  selected: DetectionSpan | null;
  onSelect: (span: DetectionSpan | null) => void;
}) {
  const segments = useMemo(() => buildSegments(text, spans), [text, spans]);
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 text-[15px] leading-relaxed text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
      {segments.map((segment, index) =>
        segment.kind === "flagged" ? (
          <mark
            key={index}
            onClick={() => onSelect(selected === segment.span ? null : segment.span)}
            className={`cursor-pointer rounded px-0.5 transition-colors ${
              selected === segment.span
                ? "bg-rose-300/70 text-rose-950 ring-2 ring-rose-400 dark:bg-rose-500/50 dark:text-rose-50"
                : "bg-rose-200/70 text-rose-950 hover:bg-rose-300/80 dark:bg-rose-500/30 dark:text-rose-100"
            }`}
            title="Click to inspect this passage"
          >
            {segment.text}
          </mark>
        ) : (
          <span key={index}>{segment.text}</span>
        )
      )}
      {selected && (
        <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 dark:border-rose-800 dark:bg-rose-950/30">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-bold text-rose-700 dark:text-rose-300">Flagged passage</p>
              <p className="mt-1 text-xs text-slate-500">Confidence {scoreLabel(selected.confidence)} · {selected.label.replace(/_/g, " ")}</p>
            </div>
            <button type="button" onClick={() => onSelect(null)} aria-label="Close" className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"><X className="h-4 w-4" /></button>
          </div>
          <p className="mt-2 rounded-lg bg-white/70 p-3 text-sm italic leading-relaxed text-slate-600 dark:bg-slate-900/40 dark:text-slate-300">“{selected.text.trim()}”</p>
          <DetectionSignals span={selected} />
        </div>
      )}
    </div>
  );
}

function ResultHeader({ result }: { result: DetectionBase }) {
  const meta = verdictFor(result.label);
  const ResultIcon = meta.icon;
  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-widest text-slate-400">Estimate</p>
          <div className={`mt-2 flex items-center gap-2 ${meta.tone}`}>
            <ResultIcon className="h-5 w-5" />
            <span className="font-bold">{meta.label}</span>
          </div>
        </div>
        <div className="text-right">
          <span className="text-4xl font-black text-slate-800 dark:text-white">{scoreLabel(result.overall_score)}</span>
          <p className="text-xs text-slate-400">AI-like score</p>
        </div>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div className={`h-full rounded-full transition-all duration-500 ${meta.bar}`} style={{ width: `${Math.min(100, Math.max(0, result.overall_score * 100))}%` }} />
      </div>
      <DistributionBar result={result} />
      {(result.insufficient_text || result.message) && (
        <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-800 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-200">
          <p className="font-semibold">Insufficient text to analyze confidently</p>
          {result.message && <p className="mt-1 text-xs leading-relaxed">{result.message}</p>}
        </div>
      )}
    </div>
  );
}

function ResultsPanel({
  result,
  text,
  selected,
  onSelect,
}: {
  result: DetectionBase;
  text?: string;
  selected: DetectionSpan | null;
  onSelect: (span: DetectionSpan | null) => void;
}) {
  return (
    <div className="space-y-5">
      <ResultHeader result={result} />
      <div className="rounded-2xl bg-slate-50 p-4 dark:bg-slate-800/60">
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{result.summary}</p>
      </div>
      {text !== undefined && (
        <div>
          <h3 className="mb-2 text-sm font-bold text-slate-800 dark:text-slate-100">Highlighted view</h3>
          <HighlightedTextView text={text} spans={result.detections} selected={selected} onSelect={onSelect} />
        </div>
      )}
      {result.detections.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-bold text-slate-800 dark:text-slate-100">
            Flagged passages {result.detections.length > 1 ? `(${result.detections.length})` : ""}
          </h3>
          <div className="space-y-2">
            {result.detections.map((detection, index) => (
              <button
                key={`${detection.start}-${index}`}
                type="button"
                onClick={() => onSelect(selected === detection ? null : detection)}
                className={`w-full rounded-xl border p-3 text-left transition-colors ${
                  selected === detection
                    ? "border-rose-300 bg-rose-50 dark:border-rose-700 dark:bg-rose-950/30"
                    : "border-slate-100 hover:border-rose-200 dark:border-slate-700 dark:hover:border-rose-800"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-2 text-xs font-bold text-rose-700 dark:text-rose-300">
                    <AlertTriangle className="h-3.5 w-3.5" /> {detection.label.replace(/_/g, " ")}
                  </span>
                  <span className="text-xs text-slate-400">Confidence {scoreLabel(detection.confidence)}</span>
                </div>
                <p className="mt-1.5 line-clamp-2 text-sm italic leading-relaxed text-slate-600 dark:text-slate-300">
                  “{detection.text.trim()}”
                </p>
                {selected === detection && (
                  <div>
                    <DetectionSignals span={detection} />
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
      <p className="border-t border-slate-100 pt-4 text-xs leading-relaxed text-slate-400 dark:border-slate-700">{result.disclaimer}</p>
    </div>
  );
}

function PdfViewer({ result }: { result: PdfDetectionResponse }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const docRef = useRef<pdfjsLib.PDFDocumentProxy | null>(null);
  const [pageNum, setPageNum] = useState(1);
  const [totalPages, setTotalPages] = useState(result.pages.length || 1);
  const [pageDims, setPageDims] = useState<{ width: number; height: number } | null>(null);
  const [rendering, setRendering] = useState(true);
  const [loadError, setLoadError] = useState("");

  const page = result.pages.find((p) => p.page === pageNum) || result.pages[0];
  const pageDetections = page
    ? result.detections.filter((d) => d.page === page.page && d.boxes.length > 0)
    : [];

  const renderPage = useCallback(async (doc: pdfjsLib.PDFDocumentProxy, number: number) => {
    const pdfPage = await doc.getPage(number);
    const base = pdfPage.getViewport({ scale: 1 });
    const containerWidth = containerRef.current?.clientWidth || VIEWPORT_WIDTH_PX;
    const width = Math.min(Math.max(containerWidth, 280), VIEWPORT_WIDTH_PX);
    const scale = width / base.width;
    const viewport = pdfPage.getViewport({ scale });
    setPageDims({ width: viewport.width, height: viewport.height });

    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    canvas.style.width = `${viewport.width}px`;
    canvas.style.height = `${viewport.height}px`;
    await pdfPage.render({ canvas, viewport }).promise;
  }, []);

  useEffect(() => {
    let cancelled = false;
    const mount = async () => {
      setRendering(true);
      setLoadError("");
      try {
        const fileBytes = await aiDetectionService.getPdfFile(result.result_id);
        if (cancelled) return;
        const doc = await pdfjsLib.getDocument({
          data: new Uint8Array(fileBytes),
        }).promise;
        if (cancelled) return;
        docRef.current = doc;
        setTotalPages(doc.numPages);
        await renderPage(doc, 1);
      } catch (err) {
        if (!cancelled) {
          const detail = (err as Error)?.message || String(err);
          setLoadError(
            `Could not open the PDF preview${detail ? ` (${detail})` : ""}. ` +
              "Use the Highlighted text view instead, or download the highlighted PDF."
          );
        }
      } finally {
        if (!cancelled) setRendering(false);
      }
    };
    mount();
  }, [result.result_id, renderPage]);

  const changePage = async (delta: number) => {
    const doc = docRef.current;
    if (!doc || rendering) return;
    const next = pageNum + delta;
    if (next < 1 || next > doc.numPages) return;
    setRendering(true);
    try {
      await renderPage(doc, next);
      setPageNum(next);
    } finally {
      setRendering(false);
    }
  };

  const overlayScale = page
    ? (pageDims ? pageDims.width : VIEWPORT_WIDTH_PX) / page.width
    : 1;

  return (
    <div>
      {loadError && <div className="mb-3 rounded-xl border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">{loadError}</div>}

      <div ref={containerRef} className="overflow-auto rounded-xl border border-slate-200 dark:border-slate-700">
        {pageDims ? (
          <div className="relative inline-block">
            <canvas ref={canvasRef} className="block" />
            <div className="pointer-events-none absolute inset-0">
              {pageDetections.map((detection, index) =>
                detection.boxes.map((box, boxIndex) => {
                  const left = box.x0 * overlayScale;
                  const top = (page.height - box.y1) * overlayScale;
                  const width = Math.max(box.x1 - box.x0, 0) * overlayScale;
                  const height = Math.max(box.y1 - box.y0, 0) * overlayScale;
                  return (
                    <div
                      key={`${detection.start}-${index}-${boxIndex}`}
                      className="pointer-events-auto absolute rounded-sm border-2 border-rose-500 bg-rose-400/30"
                      style={{ left, top, width, height }}
                      title={detection.text}
                    />
                  );
                })
              )}
            </div>
          </div>
        ) : (
          <div className="flex min-h-[360px] items-center justify-center text-sm text-slate-400">
            {rendering ? (
              <span className="flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> Rendering…</span>
            ) : (
              "Preview unavailable"
            )}
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => changePage(-1)} disabled={!docRef.current || pageNum <= 1 || rendering} className="btn-ghost btn-sm">
            <ChevronLeft className="h-4 w-4" /> Prev
          </button>
          <span className="text-sm text-slate-500">Page {pageNum} of {totalPages}</span>
          <button type="button" onClick={() => changePage(1)} disabled={!docRef.current || pageNum >= totalPages || rendering} className="btn-ghost btn-sm">
            Next <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
      {pageDetections.length > 0 && (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-rose-700 dark:text-rose-400">
          <span className="inline-block h-2.5 w-2.5 rounded-sm border border-rose-500 bg-rose-400/30" />
          {pageDetections.length} flagged region{pageDetections.length > 1 ? "s" : ""} on this page are highlighted in red.
        </p>
      )}
    </div>
  );
}

export default function AIDetection() {
  const [tab, setTab] = useState<Tab>("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [textResult, setTextResult] = useState<TextDetectionResponse | null>(null);
  const [pdfResult, setPdfResult] = useState<PdfDetectionResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedSpan, setSelectedSpan] = useState<DetectionSpan | null>(null);
  const analysisRequestRef = useRef(0);

  const wordCount = useMemo(() => (text.trim() ? text.trim().split(/\s+/).length : 0), [text]);
  const canAnalyzeText = text.trim().length >= MIN_CHARS && text.trim().length <= MAX_CHARS;

  const handleTextChange = (value: string) => {
    analysisRequestRef.current += 1;
    setText(value);
    setTextResult(null);
    setSelectedSpan(null);
    setError("");
    setLoading(false);
  };

  const handleFile = (selected: File | null) => {
    analysisRequestRef.current += 1;
    setFile(selected);
    setPdfResult(null);
    setSelectedSpan(null);
    setError("");
    setLoading(false);
  };

  const handleAnalyzeText = async () => {
    const submitted = text.trim();
    if (submitted.length < MIN_CHARS) {
      setError(`Add at least ${MIN_CHARS} characters for a meaningful estimate.`);
      return;
    }
    setError("");
    setLoading(true);
    const requestId = ++analysisRequestRef.current;
    try {
      const detection = await aiDetectionService.analyzeText(submitted);
      if (requestId === analysisRequestRef.current) {
        setTextResult(detection);
        setSelectedSpan(detection.detections[0] ?? null);
      }
    } catch (err: any) {
      if (requestId === analysisRequestRef.current) {
        setError(err?.response?.data?.detail || "The detector is unavailable right now. Please try again.");
      }
    } finally {
      if (requestId === analysisRequestRef.current) setLoading(false);
    }
  };

  const handleAnalyzePdf = async () => {
    if (!file) return;
    if (file.size > MAX_FILE_BYTES) {
      setError("That file is larger than 25 MB. Please upload a smaller PDF.");
      return;
    }
    setError("");
    setLoading(true);
    const requestId = ++analysisRequestRef.current;
    try {
      const detection = await aiDetectionService.uploadPdf(file);
      if (requestId === analysisRequestRef.current) {
        setPdfResult(detection);
        setSelectedSpan(detection.detections[0] ?? null);
      }
    } catch (err: any) {
      if (requestId === analysisRequestRef.current) {
        setError(err?.response?.data?.detail || "Could not analyze that PDF. Please try another file.");
      }
    } finally {
      if (requestId === analysisRequestRef.current) setLoading(false);
    }
  };

  return (
    <AppLayout title="AI Detection">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="relative overflow-hidden rounded-2xl border border-primary-100 bg-gradient-to-r from-primary-50 via-white to-secondary-50 p-4 shadow-sm dark:border-primary-900/40 dark:from-primary-950/40 dark:via-slate-900 dark:to-secondary-950/30 sm:p-5">
          <div className="absolute -right-12 -top-16 h-40 w-40 rounded-full bg-primary-200/40 blur-3xl dark:bg-primary-500/10" />
          <div className="relative max-w-3xl">
            <div className="mb-1.5 flex items-center gap-2 text-primary-600 dark:text-primary-300 text-[11px] font-bold uppercase tracking-widest">
              <Sparkles className="h-3 w-3" /> Writing insight
            </div>
            <h1 className="text-xl font-black tracking-tight text-slate-800 dark:text-slate-100 sm:text-2xl">
              Could this text be AI-generated?
            </h1>
            <p className="mt-1.5 max-w-2xl text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              Paste an essay or upload a PDF to get a transparent, explainable likelihood estimate. Use it as a reflection
              tool—not as proof of authorship.
            </p>
          </div>
        </section>

        <div className="card overflow-hidden">
          <div className="border-b border-slate-200 dark:border-slate-700">
            <nav className="flex -mb-px" aria-label="Tabs">
              {[
                { id: "text" as Tab, label: "Paste text", icon: MessageSquareText },
                { id: "pdf" as Tab, label: "Upload PDF", icon: FileText },
              ].map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    setTab(item.id);
                    setError("");
                  }}
                  className={`flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                    tab === item.id
                      ? "border-primary-500 text-primary-600 dark:text-primary-400"
                      : "border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                  }`}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </button>
              ))}
            </nav>
          </div>

          <div className="p-4 sm:p-6">
            {tab === "text" ? (
              <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
                <div className="flex flex-col">
                  <textarea
                    value={text}
                    onChange={(event) => handleTextChange(event.target.value)}
                    placeholder="Paste an essay, discussion response, or study draft here..."
                    className="input min-h-[320px] max-h-[420px] resize-y p-4 leading-relaxed"
                    maxLength={MAX_CHARS}
                    aria-label="Text to analyze"
                  />
                  <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                    <span>{wordCount} words</span>
                    <span>{text.length.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters</span>
                  </div>
                  {error && <div className="mt-4 rounded-xl border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">{error}</div>}
                  <button
                    type="button"
                    onClick={handleAnalyzeText}
                    disabled={!canAnalyzeText || loading}
                    className="btn-primary btn-md mt-5 w-full sm:w-auto"
                  >
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                    {loading ? "Analyzing..." : "Analyze text"}
                  </button>
                  {text.trim().length > 0 && text.trim().length < MIN_CHARS && (
                    <p className="mt-2 text-xs text-slate-400">Add {MIN_CHARS - text.trim().length} more characters to enable analysis.</p>
                  )}
                </div>

                <section className="card p-5 bg-white dark:bg-slate-900">
                  {!textResult ? (
                    <div className="flex min-h-[420px] flex-col items-center justify-center text-center">
                      <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-50 text-primary-600 dark:bg-primary-950/50 dark:text-primary-300">
                        <FileSearch className="h-8 w-8" />
                      </div>
                      <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">Your result will appear here</h2>
                      <p className="mt-2 max-w-xs text-sm leading-relaxed text-slate-500">
                        Submit at least {MIN_CHARS} characters to see an estimate, the signals behind it, and any flagged passages.
                      </p>
                    </div>
                  ) : (
                    <ResultsPanel
                      result={textResult}
                      text={text}
                      selected={selectedSpan}
                      onSelect={setSelectedSpan}
                    />
                  )}
                </section>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
                  <div className="flex flex-col">
                    <div
                      onDrop={(e) => {
                        e.preventDefault();
                        handleFile(e.dataTransfer.files?.[0] ?? null);
                      }}
                      onDragOver={(e) => { e.preventDefault(); }}
                      className="card flex flex-1 flex-col items-center justify-center gap-4 border-2 border-dashed p-8 transition-all sm:p-12"
                    >
                      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-50 text-primary-600 dark:bg-primary-950/50 dark:text-primary-300">
                        <Upload className="h-8 w-8" />
                      </div>
                      <div className="text-center">
                        <p className="font-bold text-slate-700 dark:text-slate-200">Drop your PDF here, or pick one</p>
                        <p className="text-sm text-slate-400 mt-1">Essays, reports, and homework documents · up to 25 MB</p>
                      </div>
                      {file && (
                        <div className="flex items-center gap-2 rounded-xl bg-primary-50 px-4 py-2 text-sm font-medium text-primary-700 max-w-full dark:bg-primary-900/30 dark:text-primary-300">
                          <FileText className="h-4 w-4 flex-shrink-0" />
                          <span className="truncate">{file.name}</span>
                        </div>
                      )}
                      <input
                        id="pdf-input"
                        type="file"
                        className="hidden"
                        accept=".pdf,application/pdf"
                        onChange={(event) => handleFile(event.target.files?.[0] ?? null)}
                      />
                      {!file && (
                        <button type="button" onClick={() => document.getElementById("pdf-input")?.click()} className="btn-ghost btn-sm">
                          Choose a file
                        </button>
                      )}
                    </div>
                    {error && <div className="mt-4 rounded-xl border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">{error}</div>}
                    {file && !pdfResult && (
                      <button type="button" onClick={handleAnalyzePdf} disabled={loading} className="btn-primary btn-md mt-5 w-full">
                        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSearch className="h-4 w-4" />}
                        {loading ? "Analyzing PDF..." : "Analyze PDF"}
                      </button>
                    )}
                  </div>

                  <section className="card p-5 bg-white dark:bg-slate-900">
                    {!pdfResult ? (
                      <div className="flex min-h-[380px] flex-col items-center justify-center text-center">
                        <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-50 text-primary-600 dark:bg-primary-950/50 dark:text-primary-300">
                          <FileSearch className="h-8 w-8" />
                        </div>
                        <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">PDF analysis appears here</h2>
                        <p className="mt-2 max-w-xs text-sm leading-relaxed text-slate-500">
                          Page thumbnails and highlighted regions appear once the document has been analyzed.
                        </p>
                      </div>
                    ) : (
                      <PdfHost result={pdfResult} />
                    )}
                  </section>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}

function PdfHost({ result }: { result: PdfDetectionResponse }) {
  const [selected, setSelected] = useState<DetectionSpan | null>(result.detections[0] ?? null);
  const [previewMode, setPreviewMode] = useState<"text" | "canvas">("text");
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState("");

  const downloadHighlighted = async () => {
    setDownloadError("");
    setDownloading(true);
    try {
      await aiDetectionService.downloadHighlightedPdf(result.result_id, result.file_name);
    } catch {
      setDownloadError("Could not download the highlighted PDF right now. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-5 pb-2">
      <ResultHeader result={result} />
      <div className="rounded-2xl bg-slate-50 p-4 dark:bg-slate-800/60">
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{result.summary}</p>
      </div>
      {result.scanned && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
          This PDF was scanned and recognized with OCR; positions are approximate.
        </div>
      )}
      {result.extraction_warning && (
        <div className="rounded-xl border border-sky-200 bg-sky-50 p-3 text-xs text-sky-800 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-200">
          {result.extraction_warning}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="inline-flex rounded-xl border border-slate-200 p-1 dark:border-slate-700">
          {[
            { id: "text" as const, label: "Highlighted text" },
            { id: "canvas" as const, label: "Page view" },
          ].map((mode) => (
            <button
              key={mode.id}
              type="button"
              onClick={() => setPreviewMode(mode.id)}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                previewMode === mode.id
                  ? "bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300"
                  : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              }`}
            >
              {mode.label}
            </button>
          ))}
        </div>
        <button type="button" onClick={downloadHighlighted} disabled={downloading} className="btn-primary btn-sm">
          {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
          {downloading ? "Preparing…" : "Download highlighted PDF"}
        </button>
      </div>
      {downloadError && <div className="rounded-xl border border-danger-200 bg-danger-50 p-3 text-xs text-danger-700">{downloadError}</div>}

      {previewMode === "text" ? (
        <TextPagePreview result={result} selected={selected} onSelect={setSelected} />
      ) : (
        <PdfViewer result={result} />
      )}

      {result.detections.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-bold text-slate-800 dark:text-slate-100">
            Flagged passages {result.detections.length > 1 ? `(${result.detections.length})` : ""}
          </h3>
          <div className="space-y-2">
            {result.detections.map((detection, index) => (
              <button
                key={`${detection.start}-${index}`}
                type="button"
                onClick={() => setSelected(selected === detection ? null : detection)}
                className={`w-full rounded-xl border p-3 text-left transition-colors ${
                  selected === detection
                    ? "border-rose-300 bg-rose-50 dark:border-rose-700 dark:bg-rose-950/30"
                    : "border-slate-100 hover:border-rose-200 dark:border-slate-700 dark:hover:border-rose-800"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-2 text-xs font-bold text-rose-700 dark:text-rose-300">
                    <AlertTriangle className="h-3.5 w-3.5" /> {detection.label.replace(/_/g, " ")}
                  </span>
                  <span className="text-xs text-slate-400">Page {detection.page ?? "—"} · {detection.text.split(/\s+/).length} words</span>
                </div>
                <p className="mt-1.5 line-clamp-2 text-sm italic leading-relaxed text-slate-600 dark:text-slate-300">“{detection.text.trim()}”</p>
                {selected === detection && <DetectionSignals span={detection} />}
              </button>
            ))}
          </div>
        </div>
      )}
      <p className="border-t border-slate-100 pt-4 text-xs leading-relaxed text-slate-400 dark:border-slate-700">{result.disclaimer}</p>
    </div>
  );
}

function TextPagePreview({
  result,
  selected,
  onSelect,
}: {
  result: PdfDetectionResponse;
  selected: DetectionSpan | null;
  onSelect: (span: DetectionSpan | null) => void;
}) {
  const [pageNum, setPageNum] = useState(1);
  const page = result.pages.find((p) => p.page === pageNum) || result.pages[0];

  if (!page) {
    return (
      <div className="rounded-xl border border-slate-200 p-6 text-sm text-slate-400 dark:border-slate-700">
        No extractable text for this document.
      </div>
    );
  }

  const segments = useMemo(
    () =>
      buildSegments(
        page.text,
        result.detections.filter((d) => d.page === page.page)
      ),
    [page.text, result.detections, page.page]
  );
  const pageSpanCount = result.detections.filter((d) => d.page === page.page).length;

  const changePage = (delta: number) => {
    const next = pageNum + delta;
    if (next < 1 || next > result.pages.length) return;
    setPageNum(next);
    if (selected && selected.page !== next) onSelect(null);
  };

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">AI-detected text</p>
        <span className="text-xs text-slate-400">Page {page.page} of {result.pages.length}</span>
      </div>
      <p className="mb-2 text-xs text-slate-500">
        <span className="mr-2 inline-block h-3 w-3 rounded-sm border border-rose-500 bg-rose-300/70 align-[-1px]" />
        Rose highlighting marks the detected AI-generated passages.
      </p>
      <div className="max-h-[460px] overflow-auto rounded-xl border border-slate-200 bg-white p-4 text-[15px] leading-relaxed text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
        {segments.map((segment, index) =>
          segment.kind === "flagged" ? (
            <mark
              key={index}
              onClick={() => onSelect(selected === segment.span ? null : segment.span)}
              className={`cursor-pointer rounded px-0.5 transition-colors ${
                selected === segment.span
                  ? "bg-rose-300/70 text-rose-950 ring-2 ring-rose-400 dark:bg-rose-500/50 dark:text-rose-50"
                  : "bg-rose-200/70 text-rose-950 hover:bg-rose-300/80 dark:bg-rose-500/30 dark:text-rose-100"
              }`}
              title="Click to inspect this passage"
            >
              {segment.text}
            </mark>
          ) : (
            <span key={index}>{segment.text}</span>
          )
        )}
        {pageSpanCount === 0 && (
          <p className="text-sm italic text-slate-400">No flagged passage on this page.</p>
        )}
      </div>
      <div className="mt-3 flex items-center gap-2">
        <button type="button" onClick={() => changePage(-1)} disabled={pageNum <= 1} className="btn-ghost btn-sm">
          <ChevronLeft className="h-4 w-4" /> Prev
        </button>
        <button type="button" onClick={() => changePage(1)} disabled={pageNum >= result.pages.length} className="btn-ghost btn-sm">
          Next <ChevronRight className="h-4 w-4" />
        </button>
      </div>
      {selected && (
        <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 dark:border-rose-800 dark:bg-rose-950/30">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-bold text-rose-700 dark:text-rose-300">Flagged passage</p>
              <p className="mt-1 text-xs text-slate-500">
                Page {selected.page ?? "—"} · Confidence {scoreLabel(selected.confidence)} · {selected.label.replace(/_/g, " ")}
              </p>
            </div>
            <button type="button" onClick={() => onSelect(null)} aria-label="Close" className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
              <X className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-2 rounded-lg bg-white/70 p-3 text-sm italic leading-relaxed text-slate-600 dark:bg-slate-900/40 dark:text-slate-300">“{selected.text.trim()}”</p>
          <DetectionSignals span={selected} />
        </div>
      )}
    </div>
  );
}