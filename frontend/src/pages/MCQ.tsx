import { useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { ChevronRight, Shuffle } from "lucide-react";
import { quizService } from "@/services/quizService";

const topics = ["Normalization", "SQL Joins", "Transactions", "Indexing", "ER Diagrams", "Relational Algebra"];
const difficulties = ["Easy", "Medium", "Hard"];

export default function MCQ() {
  const [topic, setTopic] = useState(topics[0]);
  const [difficulty, setDifficulty] = useState("Medium");
  const [questions, setQuestions] = useState<any[]>([]);
  const [current, setCurrent] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [score, setScore] = useState(0);
  const [started, setStarted] = useState(false);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  const start = async () => {
    setLoading(true);
    const qs = await quizService.generateMCQ(topic, difficulty, 5);
    setQuestions(qs);
    setStarted(true);
    setCurrent(0);
    setScore(0);
    setDone(false);
    setSelected(null);
    setLoading(false);
  };

  const q = questions[current];

  const next = () => {
    if (selected === q?.correct_answer) setScore(s => s + 1);
    setSelected(null);
    if (current + 1 >= questions.length) setDone(true);
    else setCurrent(c => c + 1);
  };

  if (done) return (
    <AppLayout title="MCQ Practice">
      <div className="max-w-xl mx-auto card p-6 sm:p-10 flex flex-col items-center gap-6 text-center">
        <p className="text-4xl sm:text-5xl font-black gradient-text">{Math.round((score/questions.length)*100)}%</p>
        <p className="text-slate-500">{score}/{questions.length} correct on {topic} ({difficulty})</p>
        <div className="flex flex-wrap justify-center gap-3">
          <button onClick={() => setStarted(false)} className="btn-outline btn-md">Change Topic</button>
          <button onClick={start} className="btn-primary btn-md"><Shuffle className="w-4 h-4" /> New Set</button>
        </div>
      </div>
    </AppLayout>
  );

  if (!started) return (
    <AppLayout title="MCQ Practice">
      <div className="max-w-xl mx-auto space-y-6">
        <div className="card p-4 sm:p-6 space-y-5">
          <h2 className="font-bold text-xl text-slate-800 dark:text-slate-100">Configure Your Practice Set</h2>
          <div>
            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">Select Topic</label>
            <div className="flex flex-wrap gap-2">
              {topics.map(t => (
                <button key={t} onClick={() => setTopic(t)} className={`px-4 py-2 rounded-xl text-sm font-medium border transition-all ${ topic===t ? "bg-primary-500 text-white border-primary-500" : "border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-primary-300" }`}>{t}</button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">Difficulty</label>
            <div className="flex flex-wrap gap-2">
              {difficulties.map(d => (
                <button key={d} onClick={() => setDifficulty(d)} className={`px-4 py-2 rounded-xl text-sm font-medium border transition-all ${ difficulty===d ? "bg-primary-500 text-white border-primary-500" : "border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-primary-300" }`}>{d}</button>
              ))}
            </div>
          </div>
          <button onClick={start} disabled={loading} className="btn-primary btn-lg w-full">
            {loading ? "Generating…" : "Start Practice"} <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </AppLayout>
  );

  return (
    <AppLayout title="MCQ Practice">
      <div className="max-w-xl mx-auto space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex-1 progress-bar"><div className="progress-fill bg-gradient-to-r from-primary-500 to-secondary-500" style={{ width: `${(current/questions.length)*100}%` }} /></div>
          <span className="text-sm text-slate-500">{current+1}/{questions.length}</span>
        </div>
        {q && (
          <div className="card p-4 sm:p-6 space-y-5">
            <p className="font-semibold text-lg text-slate-800 dark:text-slate-100">{q.question_text}</p>
            <div className="space-y-3">
              {q.options?.map((opt: string) => (
                <button key={opt} onClick={() => !selected && setSelected(opt)}
                  className={`w-full text-left p-4 rounded-xl border-2 text-sm font-medium transition-all ${
                    selected === opt && opt === q.correct_answer ? "border-success-500 bg-success-50" :
                    selected === opt ? "border-danger-500 bg-danger-50" :
                    selected ? "border-slate-200 opacity-60" :
                    "border-slate-200 hover:border-primary-400"
                  }`}>{opt}</button>
              ))}
            </div>
            {selected && (
              <button onClick={next} className="btn-primary btn-md w-full">
                {current+1===questions.length?"Finish":"Next"} <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
