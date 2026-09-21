import { useEffect, useRef, useState } from "react";
import { X, Download, RefreshCw, PenLine } from "lucide-react";
import { buildMasterPrompt } from "@/lib/masterPrompt";

interface HandwrittenNoteModalProps {
  title: string;
  content: string;
  date?: string | null;
  onClose: () => void;
}

// ── Handwriting style presets ───────────────────────────────────────────────
const STYLES = [
  { label: "Caveat", font: "Caveat", inkColor: "#1a1a3e", weight: "600" },
  { label: "Kalam",  font: "Kalam",  inkColor: "#1a2a1a", weight: "400" },
  { label: "Patrick Hand", font: "Patrick Hand", inkColor: "#1a1a1a", weight: "400" },
];

// ── Canvas drawing helpers ───────────────────────────────────────────────────
function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number
): string[] {
  const lines: string[] = [];
  for (const paragraph of text.split("\n")) {
    if (paragraph.trim() === "") { lines.push(""); continue; }
    const words = paragraph.split(" ");
    let line = "";
    for (const word of words) {
      const testLine = line ? line + " " + word : word;
      const { width } = ctx.measureText(testLine);
      if (width > maxWidth && line) {
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

function drawHandwrittenNote(
  canvas: HTMLCanvasElement,
  title: string,
  content: string,
  date: string,
  styleIdx: number
) {
  const style = STYLES[styleIdx];

  // ── Canvas dimensions (A4-ish proportion) ─────────────────────────────────
  const W = 820;
  const MARGIN_LEFT = 80;
  const MARGIN_RIGHT = 60;
  const MARGIN_TOP = 60;
  const LINE_HEIGHT = 38;
  const TITLE_SIZE = 42;
  const BODY_SIZE = 28;

  const ctx = canvas.getContext("2d")!;

  // First pass to calculate height
  ctx.font = `${style.weight} ${BODY_SIZE}px "${style.font}", cursive`;
  const bodyLines = wrapText(ctx, content, W - MARGIN_LEFT - MARGIN_RIGHT);

  // Title lines
  ctx.font = `${style.weight} ${TITLE_SIZE}px "${style.font}", cursive`;
  const titleLines = wrapText(ctx, title, W - MARGIN_LEFT - MARGIN_RIGHT - 20);

  const titleHeight = titleLines.length * (TITLE_SIZE + 14) + 30;
  const bodyHeight = bodyLines.length * LINE_HEIGHT + 20;
  const footerHeight = 60;
  const H = MARGIN_TOP + titleHeight + bodyHeight + footerHeight + 60;

  canvas.width = W;
  canvas.height = Math.max(H, 600);

  // ── Background: cream paper ──────────────────────────────────────────────
  const bgGrad = ctx.createLinearGradient(0, 0, W, canvas.height);
  bgGrad.addColorStop(0, "#fefdf8");
  bgGrad.addColorStop(0.5, "#fdfcf4");
  bgGrad.addColorStop(1, "#fdf9ef");
  ctx.fillStyle = bgGrad;
  ctx.fillRect(0, 0, W, canvas.height);

  // Subtle paper grain overlay (tiny noise-like dots)
  ctx.globalAlpha = 0.04;
  for (let i = 0; i < 800; i++) {
    ctx.fillStyle = "#8a7a4a";
    ctx.fillRect(
      Math.random() * W,
      Math.random() * canvas.height,
      Math.random() * 3 + 1,
      Math.random() * 3 + 1
    );
  }
  ctx.globalAlpha = 1;

  // ── Ruled lines ──────────────────────────────────────────────────────────
  const ruledStart = MARGIN_TOP + titleHeight - 8;
  ctx.strokeStyle = "#cce0ff";
  ctx.lineWidth = 1;
  ctx.globalAlpha = 0.6;
  let lineY = ruledStart;
  while (lineY < canvas.height - footerHeight + 10) {
    ctx.beginPath();
    ctx.moveTo(MARGIN_LEFT - 10, lineY);
    ctx.lineTo(W - MARGIN_RIGHT, lineY);
    ctx.stroke();
    lineY += LINE_HEIGHT;
  }
  ctx.globalAlpha = 1;

  // ── Red margin line ──────────────────────────────────────────────────────
  ctx.strokeStyle = "#e05d5d";
  ctx.lineWidth = 2;
  ctx.globalAlpha = 0.5;
  ctx.beginPath();
  ctx.moveTo(MARGIN_LEFT - 18, MARGIN_TOP - 10);
  ctx.lineTo(MARGIN_LEFT - 18, canvas.height - footerHeight + 10);
  ctx.stroke();
  ctx.globalAlpha = 1;

  // ── Hole punches (3 circles on left) ────────────────────────────────────
  const holePositions = [
    canvas.height * 0.2,
    canvas.height * 0.5,
    canvas.height * 0.8,
  ];
  for (const hy of holePositions) {
    // Shadow
    ctx.shadowColor = "rgba(0,0,0,0.12)";
    ctx.shadowBlur = 4;
    ctx.beginPath();
    ctx.arc(22, hy, 12, 0, Math.PI * 2);
    ctx.fillStyle = "#e8e0d4";
    ctx.fill();
    ctx.shadowBlur = 0;
    // Inner ring
    ctx.beginPath();
    ctx.arc(22, hy, 12, 0, Math.PI * 2);
    ctx.strokeStyle = "#ccc0b0";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  // ── Title ────────────────────────────────────────────────────────────────
  ctx.shadowColor = "rgba(0,0,0,0.06)";
  ctx.shadowBlur = 2;
  ctx.fillStyle = style.inkColor;
  ctx.font = `${style.weight} ${TITLE_SIZE}px "${style.font}", cursive`;
  ctx.textBaseline = "top";

  let ty = MARGIN_TOP;
  for (const line of titleLines) {
    ctx.fillText(line, MARGIN_LEFT, ty);
    ty += TITLE_SIZE + 14;
  }
  ctx.shadowBlur = 0;

  // Title underline (hand-drawn style — slightly wavy)
  const underlineY = ty + 4;
  ctx.strokeStyle = style.inkColor;
  ctx.lineWidth = 2.5;
  ctx.globalAlpha = 0.7;
  ctx.beginPath();
  ctx.moveTo(MARGIN_LEFT, underlineY);
  // Slightly wavy underline
  const ulLen = W - MARGIN_LEFT - MARGIN_RIGHT;
  for (let x = 0; x <= ulLen; x += 8) {
    const waveY = underlineY + Math.sin(x * 0.18) * 1.5;
    ctx.lineTo(MARGIN_LEFT + x, waveY);
  }
  ctx.stroke();
  ctx.globalAlpha = 1;

  // ── Body content ─────────────────────────────────────────────────────────
  ctx.font = `${style.weight} ${BODY_SIZE}px "${style.font}", cursive`;
  ctx.fillStyle = style.inkColor;
  ctx.textBaseline = "top";

  // Align first body line to nearest ruled line below title
  let firstBodyY =
    ruledStart +
    Math.ceil((ty + 24 - ruledStart) / LINE_HEIGHT) * LINE_HEIGHT -
    BODY_SIZE + 4;
  if (firstBodyY < ty + 20) firstBodyY = ty + 20;

  let by = firstBodyY;
  for (const line of bodyLines) {
    if (!line.trim()) {
      by += LINE_HEIGHT * 0.6;
      continue;
    }
    // Tiny Y jitter per line for organic feel
    const jitter = (Math.random() - 0.5) * 1.5;
    ctx.fillText(line, MARGIN_LEFT, by + jitter);
    by += LINE_HEIGHT;
  }

  // ── Footer separator ─────────────────────────────────────────────────────
  const footerY = canvas.height - footerHeight + 10;
  ctx.strokeStyle = style.inkColor;
  ctx.lineWidth = 1;
  ctx.globalAlpha = 0.25;
  ctx.beginPath();
  ctx.moveTo(MARGIN_LEFT - 10, footerY);
  ctx.lineTo(W - MARGIN_RIGHT, footerY);
  ctx.stroke();
  ctx.globalAlpha = 1;

  // ── Footer: date + brand ─────────────────────────────────────────────────
  ctx.font = `400 22px "${style.font}", cursive`;
  ctx.fillStyle = style.inkColor;
  ctx.globalAlpha = 0.55;
  ctx.textBaseline = "middle";
  ctx.fillText(`Mentora  •  ${date}`, MARGIN_LEFT, footerY + 28);

  // Small pen nib icon equivalent — a tiny star doodle on right
  ctx.textAlign = "right";
  ctx.fillText("✦ Study Notes", W - MARGIN_RIGHT, footerY + 28);
  ctx.textAlign = "left";
  ctx.globalAlpha = 1;
}

// ── Component ────────────────────────────────────────────────────────────────
export default function HandwrittenNoteModal({
  title,
  content,
  date,
  onClose,
}: HandwrittenNoteModalProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [generatorMode, setGeneratorMode] = useState<"canvas" | "pollinations">("canvas");
  const [styleIdx, setStyleIdx] = useState(0);
  const [rendering, setRendering] = useState(true);

  // Pollinations AI state
  const [pollinationsPrompt, setPollinationsPrompt] = useState(() =>
    buildMasterPrompt(content ? `${title}\n\n${content}` : title)
  );
  const [pollinationsModel, setPollinationsModel] = useState<"flux" | "turbo">("flux");
  const [pollinationsSeed, setPollinationsSeed] = useState(Math.floor(Math.random() * 100000));
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState(false);

  const displayDate = date
    ? new Date(date).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : new Date().toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      });

  useEffect(() => {
    if (generatorMode !== "canvas") return;
    setRendering(true);
    const draw = () => {
      if (!canvasRef.current) return;
      drawHandwrittenNote(
        canvasRef.current,
        title || "Untitled Note",
        content || "(No content yet)",
        displayDate,
        styleIdx
      );
      setRendering(false);
    };

    if (document.fonts) {
      document.fonts.ready.then(draw);
    } else {
      setTimeout(draw, 500);
    }
  }, [title, content, displayDate, styleIdx, generatorMode]);

  // Construct Pollinations AI Image URL
  const pollinationsImageUrl = `https://image.pollinations.ai/prompt/${encodeURIComponent(
    pollinationsPrompt
  )}?width=800&height=1000&seed=${pollinationsSeed}&nologo=true&model=${pollinationsModel}`;

  function handleDownloadCanvas() {
    if (!canvasRef.current) return;
    const link = document.createElement("a");
    const slug = title.replace(/\s+/g, "-").replace(/[^a-zA-Z0-9-]/g, "").toLowerCase();
    link.download = `${slug || "note"}-handwritten.png`;
    link.href = canvasRef.current.toDataURL("image/png");
    link.click();
  }

  async function handleDownloadPollinations() {
    try {
      const response = await fetch(pollinationsImageUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      const slug = title.replace(/\s+/g, "-").replace(/[^a-zA-Z0-9-]/g, "").toLowerCase();
      link.download = `${slug || "note"}-ai-generated.png`;
      link.href = url;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch {
      window.open(pollinationsImageUrl, "_blank");
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        className="bg-white dark:bg-[#222120] border border-[#E7E5E0] dark:border-[#383533] rounded-2xl shadow-2xl flex flex-col"
        style={{ maxWidth: 920, width: "100%", maxHeight: "92vh" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#E7E5E0] dark:border-[#383533] flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#EBE5F6] dark:bg-[#6F4FB1]/20 flex items-center justify-center">
              <PenLine className="w-5 h-5 text-[#6F4FB1]" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-[#252525] dark:text-[#F8F7F4]">
                Note Image Generator
              </h3>
              <p className="text-[11px] text-[#6B6B6B] dark:text-[#A8A5A0]">
                {generatorMode === "canvas"
                  ? "Canvas Rendering · 100% Accurate Handwriting"
                  : "Pollinations AI · Free Generative AI Image"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-[#6B6B6B] hover:text-[#252525] dark:hover:text-[#F8F7F4] hover:bg-[#F8F7F4] dark:hover:bg-[#383533] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mode Tabs & Controls Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 border-b border-[#E7E5E0] dark:border-[#383533] bg-[#F8F7F4]/60 dark:bg-[#1A1918]/60 flex-shrink-0">
          {/* Mode Switcher */}
          <div className="flex rounded-xl p-1 bg-[#E7E5E0]/60 dark:bg-[#383533]/60">
            <button
              onClick={() => setGeneratorMode("canvas")}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                generatorMode === "canvas"
                  ? "bg-white dark:bg-[#222120] text-[#6F4FB1] shadow-sm"
                  : "text-[#6B6B6B] dark:text-[#A8A5A0] hover:text-[#252525]"
              }`}
            >
              ✍️ Handwritten Canvas (Exact Text)
            </button>
            <button
              onClick={() => setGeneratorMode("pollinations")}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                generatorMode === "pollinations"
                  ? "bg-white dark:bg-[#222120] text-[#6F4FB1] shadow-sm"
                  : "text-[#6B6B6B] dark:text-[#A8A5A0] hover:text-[#252525]"
              }`}
            >
              🌸 Pollinations AI (Generative)
            </button>
          </div>

          {/* Controls for Canvas Mode */}
          {generatorMode === "canvas" && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-[#6B6B6B] dark:text-[#A8A5A0]">
                Font:
              </span>
              <div className="flex gap-1.5">
                {STYLES.map((s, i) => (
                  <button
                    key={s.label}
                    onClick={() => setStyleIdx(i)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                      styleIdx === i
                        ? "bg-[#EBE5F6] text-[#6F4FB1] border border-[#6F4FB1]/40"
                        : "bg-white dark:bg-[#222120] text-[#6B6B6B] dark:text-[#A8A5A0] border border-[#E7E5E0] dark:border-[#383533]"
                    }`}
                    style={{ fontFamily: `'${s.font}', cursive` }}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Controls for Pollinations AI Mode */}
          {generatorMode === "pollinations" && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-[#6B6B6B] dark:text-[#A8A5A0]">
                Model:
              </span>
              <select
                value={pollinationsModel}
                onChange={(e) => setPollinationsModel(e.target.value as "flux" | "turbo")}
                className="px-2 py-1 text-xs rounded-lg border border-[#E7E5E0] dark:border-[#383533] bg-white dark:bg-[#222120] text-[#252525] dark:text-[#F8F7F4]"
              >
                <option value="flux">Flux (High Detail)</option>
                <option value="turbo">Turbo (Fast)</option>
              </select>
              <button
                onClick={() => setPollinationsSeed(Math.floor(Math.random() * 100000))}
                className="btn-outline btn-sm text-xs py-1"
                title="Generate new variation with random seed"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${aiLoading ? "animate-spin" : ""}`} />
                Re-roll Seed
              </button>
            </div>
          )}
        </div>

        {/* Pollinations AI Prompt Input Bar */}
        {generatorMode === "pollinations" && (
          <div className="px-5 py-2.5 border-b border-[#E7E5E0] dark:border-[#383533] bg-white dark:bg-[#222120] flex gap-2 items-center flex-shrink-0">
            <span className="text-xs font-semibold text-[#6F4FB1] flex-shrink-0">
              AI Prompt:
            </span>
            <input
              type="text"
              value={pollinationsPrompt}
              onChange={(e) => setPollinationsPrompt(e.target.value)}
              className="input text-xs flex-1 py-1"
              placeholder="Describe the image prompt for Pollinations AI..."
            />
            <button
              onClick={() => setPollinationsSeed(Math.floor(Math.random() * 100000))}
              className="btn-primary btn-sm text-xs py-1 flex-shrink-0"
            >
              Generate Image
            </button>
          </div>
        )}

        {/* Image Preview Container */}
        <div className="flex-1 overflow-auto p-4 bg-[#F0EDE8] dark:bg-[#1A1918] flex items-center justify-center">
          {generatorMode === "canvas" ? (
            <canvas
              ref={canvasRef}
              className="rounded-xl shadow-2xl"
              style={{
                maxWidth: "100%",
                height: "auto",
                display: "block",
                border: "1px solid #D3CFCA",
              }}
            />
          ) : (
            <div className="relative flex flex-col items-center max-w-full">
              {aiLoading && (
                <div className="absolute inset-0 bg-white/70 dark:bg-black/70 backdrop-blur-xs rounded-xl flex flex-col items-center justify-center z-10 p-6 text-center">
                  <RefreshCw className="w-8 h-8 animate-spin text-[#6F4FB1] mb-2" />
                  <p className="text-xs font-bold text-[#252525] dark:text-[#F8F7F4]">
                    Pollinations AI is generating your image...
                  </p>
                  <p className="text-[11px] text-[#6B6B6B] dark:text-[#A8A5A0]">
                    Powered by pollinations.ai (Free API)
                  </p>
                </div>
              )}
              {aiError ? (
                <div className="bg-white dark:bg-[#222120] p-8 rounded-xl border border-red-200 text-center max-w-md space-y-3 shadow-lg">
                  <p className="text-sm font-bold text-red-600">Failed to load Pollinations AI image.</p>
                  <p className="text-xs text-[#6B6B6B]">The API might be temporarily busy or rate-limited.</p>
                  <button
                    onClick={() => {
                      setAiError(false);
                      setPollinationsSeed(Math.floor(Math.random() * 100000));
                    }}
                    className="btn-primary btn-sm mx-auto"
                  >
                    Retry Generation
                  </button>
                </div>
              ) : (
                <img
                  src={pollinationsImageUrl}
                  alt="Pollinations AI generated note image"
                  className="rounded-xl shadow-2xl max-h-[65vh] object-contain border border-[#D3CFCA]"
                  onLoadStart={() => setAiLoading(true)}
                  onLoad={() => {
                    setAiLoading(false);
                    setAiError(false);
                  }}
                  onError={() => {
                    setAiLoading(false);
                    setAiError(true);
                  }}
                />
              )}
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-between px-5 py-4 border-t border-[#E7E5E0] dark:border-[#383533] flex-shrink-0">
          <p className="text-xs text-[#6B6B6B] dark:text-[#A8A5A0]">
            {generatorMode === "canvas"
              ? "💡 Canvas mode guarantees exact word-for-word text rendering"
              : "🌸 Pollinations.ai free API generates creative artistic handwritten note images"}
          </p>
          <div className="flex gap-2">
            <button onClick={onClose} className="btn-outline btn-sm">
              Close
            </button>
            <button
              onClick={generatorMode === "canvas" ? handleDownloadCanvas : handleDownloadPollinations}
              disabled={generatorMode === "canvas" ? rendering : aiLoading}
              className="btn-primary btn-sm disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              Download PNG
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
