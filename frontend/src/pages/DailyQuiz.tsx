import { useState, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { CheckCircle2, XCircle, ChevronRight, Trophy } from "lucide-react";
import { quizService } from "@/services/quizService";

export default function DailyQuiz() {
  const [questions, setQuestions] = useState<any[]>([]);
  const [current, setCurrent] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [answers, setAnswers] = useState<string[]>([]);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => { quizService.getDailyQuiz().then(d => { setQuestions(d); setLoading(false); }); }, []);

  const q = questions[current];
  const correct = answers.filter((a, i) => a === questions[i]?.correct_answer).length;

  const next = () => {
    if (!selected) return;
    setAnswers([...answers, selected]);
    setSelected(null);
    if (current + 1 >= questions.length) setDone(true);
    else setCurrent(c => c + 1);
  };

  if (loading) return <AppLayout title="Daily Quiz"><div className="flex items-center justify-center h-64"><div className="w-10 h-10 border-4 border-primary-200 border-t-primary-500 rounded-full animate-spin" /></div></AppLayout>;

  if (done) return (
    <AppLayout title="Daily Quiz">
      <div className="max-w-xl mx-auto">
        <div className="card p-10 flex flex-col items-center gap-6 text-center">
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center shadow-lg">
            <Trophy className="w-10 h-10 text-white" />
          </div>
          <div>
            <h2 className="text-3xl font-black text-slate-800 dark:text-slate-100">{Math.round((correct/questions.length)*100)}%</h2>
            <p className="text-slate-500 mt-1">{correct} of {questions.length} correct</p>
          </div>
          <button onClick={() => { setCurrent(0); setSelected(null); setAnswers([]); setDone(false); }} className="btn-primary btn-lg">
            Try Again
          </button>
        </div>
      </div>
    </AppLayout>
  );

  return (
    <AppLayout title="Daily Quiz">
      <div className="max-w-xl mx-auto space-y-6">
        <div className="flex items-center gap-3">
          <div className="flex-1 progress-bar">
            <div className="progress-fill bg-gradient-to-r from-primary-500 to-secondary-500" style={{ width: `${((current) / questions.length) * 100}%` }} />
          </div>
          <span className="text-sm text-slate-500 font-medium">{current + 1}/{questions.length}</span>
        </div>

        {q && (
          <div className="card p-6 space-y-6">
            <div className="flex items-start justify-between gap-4">
              <p className="font-semibold text-slate-800 dark:text-slate-100 text-lg leading-snug">{q.question_text}</p>
              <span className={`badge flex-shrink-0 ${ q.difficulty === "Easy" ? "badge-green" : q.difficulty === "Hard" ? "badge-red" : "badge-yellow" }`}>{q.difficulty}</span>
            </div>

            <div className="space-y-3">
              {q.options?.map((opt: string) => {
                const isCorrect = selected && opt === q.correct_answer;
                const isWrong = selected === opt && opt !== q.correct_answer;
                return (
                  <button key={opt} onClick={() => !selected && setSelected(opt)}
                    className={`w-full text-left p-4 rounded-xl border-2 transition-all text-sm font-medium ${
                      isCorrect ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300" :
                      isWrong ? "border-danger-500 bg-danger-50 dark:bg-red-900/20 text-danger-700 dark:text-red-300" :
                      selected && opt !== selected ? "border-slate-200 dark:border-slate-600 text-slate-400 opacity-60" :
                      "border-slate-200 dark:border-slate-600 hover:border-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 text-slate-700 dark:text-slate-200"
                    }`}>
                    <span className="flex items-center justify-between gap-2">
                      {opt}
                      {isCorrect && <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0" />}
                      {isWrong && <XCircle className="w-5 h-5 text-danger-500 flex-shrink-0" />}
                    </span>
                  </button>
                );
              })}
            </div>

            {selected && q.explanation && (
              <div className="p-4 bg-primary-50 dark:bg-primary-900/20 rounded-xl border border-primary-200 dark:border-primary-700">
                <p className="text-sm text-primary-700 dark:text-primary-300"><span className="font-bold">💡 Explanation: </span>{q.explanation}</p>
              </div>
            )}

            <button onClick={next} disabled={!selected} className="btn-primary btn-md w-full disabled:opacity-40">
              {current + 1 === questions.length ? "Finish Quiz" : "Next Question"} <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
