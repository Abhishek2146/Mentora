import { useState, useEffect, useRef } from "react";
import { Download, RefreshCw, Maximize2, Wand2, FileText, Sparkles, Copy, Check } from "lucide-react";

interface PollinationsNotesCardProps {
  initialTitle?: string;
  initialContent?: string;
  /** Pre-extracted keywords/concepts from AI-generated notes — auto-fills textarea and triggers generation */
  autoKeywords?: string;
  onOpenModal?: () => void;
}

// ── Canvas text wrap helper ──────────────────────────────────────────────────
function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number
): string[] {
  const lines: string[] = [];
  for (const paragraph of text.split(/\r?\n/)) {
    if (paragraph.trim() === "") { lines.push(""); continue; }
    const words = paragraph.split(" ");
    let line = "";
    for (const word of words) {
      const testLine = line ? line + " " + word : word;
      if (ctx.measureText(testLine).width > maxWidth && line) {
        lines.push(line);
        line = word;
      } else {
        line = testLine;
      }
    }
    if (line) lines.push(line);
  }
  return lines;
}

// ── Main canvas draw function ────────────────────────────────────────────────
function drawHandwrittenNote(
  canvas: HTMLCanvasElement,
  title: string,
  content: string
) {
  const W = 820;
  const MARGIN_LEFT = 80;
  const MARGIN_RIGHT = 50;
  const MARGIN_TOP = 55;
  const LINE_HEIGHT = 40;
  const TITLE_SIZE = 42;
  const BODY_SIZE = 27;
  const INK = "#1a3575"; // Royal blue ballpoint pen

  const ctx = canvas.getContext("2d")!;

  // Split on newlines and commas so each concept gets its own line
  const rawContent = content.trim() || "Start typing keywords above...";
  const rawItems = rawContent
    .split(/\r?\n/)
    .flatMap((l) => l.split(/,\s*/))
    .map((s) => s.trim())
    .filter(Boolean);
  const contentStr = rawItems.join("\n");

  // First pass to measure lines for height calculation
  ctx.font = `600 ${BODY_SIZE}px "Caveat", "Kalam", "Patrick Hand", cursive`;
  const bodyLines = wrapText(ctx, contentStr, W - MARGIN_LEFT - MARGIN_RIGHT - 24);

  ctx.font = `700 ${TITLE_SIZE}px "Caveat", "Kalam", "Patrick Hand", cursive`;
  const titleLines = wrapText(ctx, title || "Study Notes", W - MARGIN_LEFT - MARGIN_RIGHT);

  const titleHeight = titleLines.length * (TITLE_SIZE + 12) + 36;
  const bodyHeight = bodyLines.length * LINE_HEIGHT + 30;
  const footerHeight = 56;
  const H = MARGIN_TOP + titleHeight + bodyHeight + footerHeight + 60;

  canvas.width = W;
  canvas.height = Math.max(H, 560);

  // ── Paper background ─────────────────────────────────────────────────────
  const bg = ctx.createLinearGradient(0, 0, W, canvas.height);
  bg.addColorStop(0, "#fefdf8");
  bg.addColorStop(0.45, "#fdfcf5");
  bg.addColorStop(1, "#fdf9ee");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, canvas.height);

  // Paper grain noise
  ctx.globalAlpha = 0.035;
  for (let i = 0; i < 700; i++) {
    ctx.fillStyle = "#8a7a4a";
    ctx.fillRect(
      Math.random() * W,
      Math.random() * canvas.height,
      Math.random() * 2.5 + 0.5,
      Math.random() * 2.5 + 0.5
    );
  }
  ctx.globalAlpha = 1;

  // ── Ruled lines ──────────────────────────────────────────────────────────
  const ruledStart = MARGIN_TOP + titleHeight - 10;
  ctx.strokeStyle = "#c5d9f7";
  ctx.lineWidth = 1;
  ctx.globalAlpha = 0.65;
  let lineY = ruledStart;
  while (lineY < canvas.height - footerHeight + 10) {
    ctx.beginPath();
    ctx.moveTo(MARGIN_LEFT - 12, lineY);
    ctx.lineTo(W - MARGIN_RIGHT, lineY);
    ctx.stroke();
    lineY += LINE_HEIGHT;
  }
  ctx.globalAlpha = 1;

  // ── Red margin line ──────────────────────────────────────────────────────
  ctx.strokeStyle = "#d95555";
  ctx.lineWidth = 1.8;
  ctx.globalAlpha = 0.55;
  ctx.beginPath();
  ctx.moveTo(MARGIN_LEFT - 20, MARGIN_TOP - 15);
  ctx.lineTo(MARGIN_LEFT - 20, canvas.height - footerHeight + 15);
  ctx.stroke();
  ctx.globalAlpha = 1;

  // ── Hole punches ─────────────────────────────────────────────────────────
  const holes = [canvas.height * 0.2, canvas.height * 0.5, canvas.height * 0.8];
  for (const hy of holes) {
    ctx.shadowColor = "rgba(0,0,0,0.10)";
    ctx.shadowBlur = 4;
    ctx.beginPath();
    ctx.arc(22, hy, 11, 0, Math.PI * 2);
    ctx.fillStyle = "#e4ddd4";
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.beginPath();
    ctx.arc(22, hy, 11, 0, Math.PI * 2);
    ctx.strokeStyle = "#c8bdb0";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  // ── Title ────────────────────────────────────────────────────────────────
  ctx.textBaseline = "top";
  ctx.fillStyle = INK;
  ctx.font = `700 ${TITLE_SIZE}px "Caveat", "Kalam", "Patrick Hand", cursive`;
  ctx.shadowColor = "rgba(0,0,0,0.05)";
  ctx.shadowBlur = 2;

  let ty = MARGIN_TOP;
  for (const tl of titleLines) {
    ctx.fillText(tl, MARGIN_LEFT, ty);
    ty += TITLE_SIZE + 12;
  }
  ctx.shadowBlur = 0;

  // Slightly wavy underline beneath title
  const underlineY = ty + 5;
  const ulLen = W - MARGIN_LEFT - MARGIN_RIGHT;
  ctx.strokeStyle = INK;
  ctx.lineWidth = 2.2;
  ctx.globalAlpha = 0.75;
  ctx.beginPath();
  ctx.moveTo(MARGIN_LEFT, underlineY);
  for (let x = 0; x <= ulLen; x += 8) {
    ctx.lineTo(MARGIN_LEFT + x, underlineY + Math.sin(x * 0.15) * 1.2);
  }
  ctx.stroke();
  ctx.globalAlpha = 1;

  // ── Body lines ────────────────────────────────────────────────────────────
  ctx.font = `600 ${BODY_SIZE}px "Caveat", "Kalam", "Patrick Hand", cursive`;
  ctx.fillStyle = INK;
  ctx.textBaseline = "top";

  let firstBodyY =
    ruledStart +
    Math.ceil((underlineY + 20 - ruledStart) / LINE_HEIGHT) * LINE_HEIGHT -
    BODY_SIZE + 6;
  if (firstBodyY < underlineY + 14) firstBodyY = underlineY + 14;

  let by = firstBodyY;
  for (const bline of bodyLines) {
    if (!bline.trim()) {
      by += LINE_HEIGHT * 0.55;
      continue;
    }
    const jitter = (Math.random() - 0.5) * 1.2;

    // Bullet dot
    ctx.beginPath();
    ctx.arc(MARGIN_LEFT + 5, by + BODY_SIZE / 2 + jitter, 2.8, 0, Math.PI * 2);
    ctx.fillStyle = INK;
    ctx.globalAlpha = 0.6;
    ctx.fill();
    ctx.globalAlpha = 1;

    ctx.fillStyle = INK;
    ctx.fillText(bline, MARGIN_LEFT + 20, by + jitter);
    by += LINE_HEIGHT;
  }

  // ── Footer ───────────────────────────────────────────────────────────────
  const footerY = canvas.height - footerHeight + 10;
  ctx.strokeStyle = INK;
  ctx.lineWidth = 1;
  ctx.globalAlpha = 0.22;
  ctx.beginPath();
  ctx.moveTo(MARGIN_LEFT - 12, footerY);
  ctx.lineTo(W - MARGIN_RIGHT, footerY);
  ctx.stroke();
  ctx.globalAlpha = 1;

  ctx.font = `400 20px "Caveat", "Kalam", "Patrick Hand", cursive`;
  ctx.fillStyle = INK;
  ctx.globalAlpha = 0.45;
  ctx.textBaseline = "middle";
  const today = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
  ctx.fillText(`Mentora  ·  ${today}`, MARGIN_LEFT, footerY + 28);
  ctx.textAlign = "right";
  ctx.fillText("✦ Study Notes", W - MARGIN_RIGHT, footerY + 28);
  ctx.textAlign = "left";
  ctx.globalAlpha = 1;
}

// ── Component ────────────────────────────────────────────────────────────────
export default function PollinationsNotesCard({
  initialTitle,
  initialContent,
  autoKeywords,
  onOpenModal,
}: PollinationsNotesCardProps) {
  const [topic, setTopic] = useState(initialTitle || "");
  const [notesConcept, setNotesConcept] = useState(
    initialContent || initialTitle || ""
  );
  const [seed, setSeed] = useState(() => Math.floor(Math.random() * 100000));
  const [copied, setCopied] = useState(false);
  const prevAutoKeywordsRef = useRef<string | undefined>(undefined);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Sync when selected note changes
  useEffect(() => {
    if (initialTitle || initialContent) {
      setTopic(initialTitle || "");
      setNotesConcept(initialContent || initialTitle || "");
    }
  }, [initialTitle, initialContent]);

  // Auto-fill keywords when AI sends them, trigger re-draw
  useEffect(() => {
    if (autoKeywords && autoKeywords !== prevAutoKeywordsRef.current) {
      prevAutoKeywordsRef.current = autoKeywords;
      const cleanKeywords = autoKeywords.replace(/\|\|\d+$/, "").trim();
      if (!cleanKeywords) return;
      setNotesConcept(cleanKeywords);
      setSeed(Math.floor(Math.random() * 100000));
    }
  }, [autoKeywords]);

  // Re-draw canvas whenever topic, content, or seed changes
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    drawHandwrittenNote(canvas, topic.trim(), notesConcept.trim());
  }, [topic, notesConcept, seed]);

  function handleGenerateVariation() {
    setSeed(Math.floor(Math.random() * 100000));
  }

  async function handleDownload() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const a = document.createElement("a");
    const filename = (topic || "handwritten-note")
      .toLowerCase()
      .replace(/[^a-z0-9]/g, "-")
      .replace(/-+/g, "-");
    a.download = `${filename}-handwritten.png`;
    a.href = canvas.toDataURL("image/png");
    a.click();
  }

  function handleCopyImage() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.toBlob((blob) => {
      if (blob && navigator.clipboard && window.ClipboardItem) {
        navigator.clipboard
          .write([new ClipboardItem({ "image/png": blob })])
          .then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
          });
      }
    });
  }

  const wordCount = notesConcept.trim()
    ? notesConcept.trim().split(/\s+/).length
    : 0;

  return (
    <div className="card p-5 space-y-4 border border-[#6F4FB1]/30 bg-gradient-to-br from-white via-[#F8F7F4] to-[#EBE5F6]/40 dark:from-[#222120] dark:via-[#1A1918] dark:to-[#2A2927]">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E7E5E0] dark:border-[#383533] pb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-[#EBE5F6] text-[#6F4FB1] dark:bg-[#6F4FB1]/20 dark:text-[#EBE5F6]">
            <Wand2 className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-base text-[#252525] dark:text-[#F8F7F4]">
                Handwritten Study Notes
              </h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#EBE5F6] text-[#6F4FB1] border border-[#6F4FB1]/30">
                Instant · Canvas
              </span>
            </div>
            <p className="text-xs text-[#6B6B6B] dark:text-[#A8A5A0]">
              Royal blue ballpoint pen on textured ruled notebook paper
            </p>
          </div>
        </div>

        {onOpenModal && (
          <button
            onClick={onOpenModal}
            className="btn-ghost btn-sm text-xs text-[#6F4FB1] hover:bg-[#EBE5F6]/50 flex items-center gap-1.5"
          >
            <Maximize2 className="w-3.5 h-3.5" /> Full Modal View
          </button>
        )}
      </div>

      {/* Topic input */}
      <div>
        <label className="block text-xs font-semibold text-[#6B6B6B] dark:text-[#A8A5A0] mb-1">
          Note Title / Topic
        </label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. Rectangle Formula"
          className="input text-xs w-full"
        />
      </div>

      {/* Keywords textarea */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-xs font-semibold text-[#6B6B6B] dark:text-[#A8A5A0] flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-[#6F4FB1]" />
            Keywords &amp; Concepts (up to 20 words)
          </label>
          <div className="flex items-center gap-2">
            {autoKeywords &&
              notesConcept === autoKeywords.replace(/\|\|\d+$/, "").trim() && (
                <span className="text-[10px] font-bold text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <Sparkles className="w-2.5 h-2.5" /> Auto-extracted
                </span>
              )}
            <span
              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                wordCount > 20
                  ? "text-red-600 bg-red-50 border-red-200"
                  : "text-[#6B6B6B] dark:text-[#A8A5A0] border-transparent"
              }`}
            >
              {wordCount}/20 words
            </span>
          </div>
        </div>
        <textarea
          value={notesConcept}
          onChange={(e) => setNotesConcept(e.target.value)}
          placeholder="e.g. Area = l x b, Perimeter = 2(l + b), Diagonal = sqrt(l^2 + b^2), l = length, b = breadth"
          rows={3}
          className="input text-xs font-sans w-full resize-none leading-relaxed"
        />
        <div className="flex items-center justify-between mt-2">
          <span className="text-[11px] text-[#6B6B6B] dark:text-[#A8A5A0]">
            Type keywords above — the handwritten note updates instantly.
          </span>
          <button
            type="button"
            onClick={handleGenerateVariation}
            disabled={!notesConcept.trim()}
            className="btn-primary btn-sm text-xs bg-gradient-to-r from-[#6F4FB1] to-[#9376C8] border-0 flex items-center gap-1.5 shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5" />
            New Variation
          </button>
        </div>
      </div>

      {/* Canvas preview */}
      <div className="relative rounded-2xl overflow-hidden border border-[#E7E5E0] dark:border-[#383533] bg-[#f5f0e4] min-h-[320px] flex items-center justify-center group shadow-inner">
        <div className="w-full overflow-x-auto p-3 flex justify-center">
          <canvas
            ref={canvasRef}
            className="max-w-full h-auto rounded-lg shadow-md border border-[#ddd5c0]"
            style={{ maxHeight: "460px" }}
          />
        </div>

        {/* Hover action overlay */}
        <div className="absolute bottom-3 right-3 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={handleCopyImage}
            className="p-2 rounded-xl bg-black/60 hover:bg-black/80 text-white backdrop-blur-md text-xs flex items-center gap-1.5 transition-colors"
            title="Copy image to clipboard"
          >
            {copied ? (
              <Check className="w-3.5 h-3.5 text-green-400" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </div>

      {/* Footer actions */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
        <p className="text-[11px] text-[#6B6B6B] dark:text-[#A8A5A0]">
          ✏️ Canvas rendered · Seed:{" "}
          <code className="font-mono text-[#6F4FB1]">{seed}</code>
        </p>
        <div className="flex gap-2">
          <button
            onClick={handleGenerateVariation}
            className="btn-outline btn-sm text-xs flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Re-roll
          </button>
          <button
            onClick={handleDownload}
            disabled={!notesConcept.trim() && !topic.trim()}
            className="btn-primary btn-sm text-xs bg-gradient-to-r from-[#6F4FB1] to-[#9376C8] border-0 flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" /> Download PNG
          </button>
        </div>
      </div>
    </div>
  );
}
