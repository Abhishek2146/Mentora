import AppLayout from "@/components/layout/AppLayout";
import { TrendingUp } from "lucide-react";

const topics = [
  { name: "SQL Fundamentals", pct: 88, unit: "Unit 2" },
  { name: "ER Diagrams", pct: 90, unit: "Unit 1" },
  { name: "Normalization", pct: 75, unit: "Unit 3" },
  { name: "Relational Algebra", pct: 61, unit: "Unit 1" },
  { name: "Indexing & B+ Trees", pct: 55, unit: "Unit 5" },
  { name: "Transaction Management", pct: 42, unit: "Unit 4" },
];

export default function Progress() {
  return (
    <AppLayout title="Progress">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="card p-5 sm:p-6 bg-gradient-to-r from-primary-600 to-secondary-600 text-white border-0">
          <div className="flex items-center gap-4">
            <TrendingUp className="w-10 h-10 flex-shrink-0" />
            <div>
              <p className="text-primary-100">Overall Progress</p>
              <p className="text-3xl sm:text-4xl font-black">69%</p>
              <p className="text-primary-100 text-sm">9 of 18 topics mastered</p>
            </div>
          </div>
        </div>
        <div className="card p-5 sm:p-6 space-y-4">
          <h3 className="font-bold text-slate-800 dark:text-slate-100">Topic-wise Mastery</h3>
          {topics.map(t => (
            <div key={t.name}>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium text-slate-700 dark:text-slate-300">{t.name}</span>
                <span className="text-slate-500">{t.pct}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width:`${t.pct}%`, background: t.pct>=80?'linear-gradient(90deg,#22c55e,#16a34a)':t.pct>=60?'linear-gradient(90deg,#0ea5e9,#0284c7)':'linear-gradient(90deg,#f59e0b,#d97706)' }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
