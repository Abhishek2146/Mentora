import { useState, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { ChevronLeft, ChevronRight, RotateCcw, Zap } from "lucide-react";
import { flashcardService } from "@/services/flashcardService";

export default function Flashcards() {
  const [cards, setCards] = useState<any[]>([]);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [loading, setLoading] = useState(true);
  const [sessionStats, setSessionStats] = useState({ correct: 0, incorrect: 0 });

  useEffect(() => {
    flashcardService.getFlashcards().then((data) => { setCards(data); setLoading(false); });
  }, []);

  const current = cards[index];

  const next = () => { setFlipped(false); setTimeout(() => setIndex((i) => Math.min(i + 1, cards.length - 1)), 150); };
  const prev = () => { setFlipped(false); setTimeout(() => setIndex((i) => Math.max(i - 1, 0)), 150); };

  const rate = async (rating: "Again" | "Hard" | "Good" | "Easy") => {
    if (!current) return;
    if (rating === "Good" || rating === "Easy") setSessionStats(s => ({ ...s, correct: s.correct + 1 }));
    else setSessionStats(s => ({ ...s, incorrect: s.incorrect + 1 }));
    await flashcardService.submitRating(current.id, rating);
    next();
  };

  const diffColor = (d: string) => d === "Easy" ? "badge-green" : d === "Hard" ? "badge-red" : "badge-yellow";

  return (
    <AppLayout title="Flashcards">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="grid grid-cols-3 gap-4">
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-primary-600">{cards.length}</p>
            <p className="text-xs text-slate-500 mt-1">Total Cards</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-success-600">{sessionStats.correct}</p>
            <p className="text-xs text-slate-500 mt-1">Correct</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-danger-600">{sessionStats.incorrect}</p>
            <p className="text-xs text-slate-500 mt-1">Incorrect</p>
          </div>
        </div>

        {cards.length > 0 && (
          <div className="flex items-center gap-3">
            <div className="flex-1 progress-bar">
              <div className="progress-fill bg-gradient-to-r from-primary-500 to-secondary-500" style={{ width: `${((index + 1) / cards.length) * 100}%` }} />
            </div>
            <span className="text-sm text-slate-500 font-medium">{index + 1}/{cards.length}</span>
          </div>
        )}

        {loading ? (
          <div className="card p-12 flex items-center justify-center">
            <div className="w-10 h-10 border-4 border-primary-200 border-t-primary-500 rounded-full animate-spin" />
          </div>
        ) : current ? (
          <div>
            <div
              onClick={() => setFlipped(!flipped)}
              className="card p-5 sm:p-8 min-h-[240px] sm:min-h-[280px] w-full max-w-full flex flex-col items-center justify-center cursor-pointer select-none hover:shadow-soft transition-all duration-300 relative"
            >
              <div className="absolute top-4 right-4">
                <span className={diffColor(current.difficulty)}>{current.difficulty}</span>
              </div>
              <p className="text-xs text-slate-400 mb-4 uppercase tracking-widest">{flipped ? "Answer" : "Question"}</p>
              <p className="text-center text-base sm:text-lg font-medium text-slate-700 dark:text-slate-200 leading-relaxed break-words max-w-full">
                {flipped ? current.back : current.front}
              </p>
              {!flipped && (
                <p className="absolute bottom-4 text-xs text-slate-400">Click to reveal answer</p>
              )}
            </div>

            {flipped && (
              <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2">
                {(["Again", "Hard", "Good", "Easy"] as const).map((r) => (
                  <button key={r} onClick={() => rate(r)}
                    className={`btn btn-md text-xs font-bold rounded-xl ${
                      r === "Again" ? "bg-danger-500 text-white hover:bg-danger-600" :
                      r === "Hard" ? "bg-warning-500 text-white hover:bg-warning-600" :
                      r === "Good" ? "bg-primary-500 text-white hover:bg-primary-600" :
                      "bg-success-500 text-white hover:bg-success-600"
                    }`}>{r}</button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="card p-12 flex flex-col items-center justify-center gap-4">
            <Zap className="w-12 h-12 text-success-500" />
            <p className="font-bold text-xl text-slate-700 dark:text-slate-200">Session Complete! 🎉</p>
            <button onClick={() => { setIndex(0); setFlipped(false); setSessionStats({ correct: 0, incorrect: 0 }); }} className="btn-primary btn-md">
              <RotateCcw className="w-4 h-4" /> Restart
            </button>
          </div>
        )}

        <div className="flex justify-between gap-2">
          <button onClick={prev} disabled={index === 0} className="btn-outline btn-md disabled:opacity-40">
            <ChevronLeft className="w-4 h-4" /> Previous
          </button>
          <button onClick={() => setFlipped(!flipped)} className="btn-ghost btn-md">
            <RotateCcw className="w-4 h-4" /> Flip
          </button>
          <button onClick={next} disabled={index >= cards.length - 1} className="btn-outline btn-md disabled:opacity-40">
            Next <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </AppLayout>
  );
}
