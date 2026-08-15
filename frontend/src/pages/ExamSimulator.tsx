import { useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { Trophy, Clock, BookOpen, AlertTriangle } from "lucide-react";
import { mockQuizQuestions } from "@/data/mockData";

export default function ExamSimulator() {
  const [started, setStarted] = useState(false);
  const [timeLeft, setTimeLeft] = useState(45 * 60);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [done, setDone] = useState(false);

  const questions = [...mockQuizQuestions, ...mockQuizQuestions].map((q, i) => ({ ...q, id: i + 1 }));

  const score = questions.filter(q => answers[q.id] === q.correct_answer).length;
  const pct = Math.round((score / questions.length) * 100);

  if (done) return (
    <AppLayout title="Exam Simulator">
      <div className="max-w-xl mx-auto card p-10 flex flex-col items-center gap-6 text-center">
        <div className={`w-24 h-24 rounded-full flex items-center justify-center text-white text-3xl font-black ${ pct >= 60 ? "bg-gradient-to-br from-emerald-400 to-emerald-600" : "bg-gradient-to-br from-danger-400 to-danger-600" }`}>
          {pct}%
        </div>
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">{pct >= 60 ? "🎉 Passed!" : "📚 Keep Practicing"}</h2>
          <p className="text-slate-500 mt-1">{score}/{questions.length} correct</p>
        </div>
        <button onClick={() => { setDone(false); setStarted(false); setAnswers({}); setTimeLeft(45*60); }} className="btn-primary btn-lg">
          Try Again
        </button>
      </div>
    </AppLayout>
  );

  if (!started) return (
    <AppLayout title="Exam Simulator">
      <div className="max-w-xl mx-auto space-y-6">
        <div className="card p-8 flex flex-col items-center gap-6 text-center">
          <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center shadow-glow-primary">
            <Trophy className="w-10 h-10 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">DBMS Mock Exam</h2>
            <p className="text-slate-500 mt-2">Simulate real exam conditions. {questions.length} questions • 45 minutes</p>
          </div>
          <div className="grid grid-cols-3 gap-4 w-full">
            {[{ label: "Questions", value: questions.length, icon: BookOpen }, { label: "Time", value: "45 min", icon: Clock }, { label: "Pass Mark", value: "60%", icon: Trophy }].map(s => (
              <div key={s.label} className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-3 text-center">
                <s.icon className="w-5 h-5 text-primary-500 mx-auto mb-1" />
                <p className="font-bold text-slate-800 dark:text-slate-100">{s.value}</p>
                <p className="text-xs text-slate-400">{s.label}</p>
              </div>
            ))}
          </div>
          <div className="flex items-start gap-2 p-3 bg-warning-50 dark:bg-yellow-900/20 rounded-xl text-sm text-warning-700 dark:text-yellow-300 w-full">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            Do not refresh the page once the exam starts. Timer cannot be paused.
          </div>
          <button onClick={() => setStarted(true)} className="btn-primary btn-lg w-full">Start Exam</button>
        </div>
      </div>
    </AppLayout>
  );

  return (
    <AppLayout title="Exam Simulator">
      <div className="max-w-3xl mx-auto space-y-4">
        <div className="card p-4 flex items-center justify-between">
          <span className="font-medium text-slate-600 dark:text-slate-400">{Object.keys(answers).length}/{questions.length} answered</span>
          <div className="flex items-center gap-2 text-warning-600 font-mono font-bold">
            <Clock className="w-4 h-4" />
            {Math.floor(timeLeft/60).toString().padStart(2,"0")}:{(timeLeft%60).toString().padStart(2,"0")}
          </div>
          <button onClick={() => setDone(true)} className="btn-primary btn-sm">Submit Exam</button>
        </div>
        <div className="space-y-4">
          {questions.map((q, i) => (
            <div key={q.id} className="card p-5">
              <p className="font-semibold text-slate-800 dark:text-slate-100 mb-4">{i+1}. {q.question_text}</p>
              <div className="space-y-2">
                {q.options?.map((opt: string) => (
                  <button key={opt} onClick={() => setAnswers({...answers, [q.id]: opt})}
                    className={`w-full text-left p-3 rounded-xl border text-sm transition-all ${
                      answers[q.id]===opt ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300" : "border-slate-200 dark:border-slate-600 hover:border-primary-300"
                    }`}>{opt}</button>
                ))}
              </div>
            </div>
          ))}
        </div>
        <button onClick={() => setDone(true)} className="btn-primary btn-lg w-full">Submit Exam</button>
      </div>
    </AppLayout>
  );
}
