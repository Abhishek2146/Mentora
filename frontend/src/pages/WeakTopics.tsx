import AppLayout from "@/components/layout/AppLayout";
import { AlertTriangle, TrendingUp, BookOpen } from "lucide-react";
import { mockWeakTopics } from "@/data/mockData";
import { Link } from "react-router-dom";

export default function WeakTopics() {
  return (
    <AppLayout title="Weak Topics">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="card p-5 bg-gradient-to-r from-warning-50 to-danger-50 dark:from-yellow-900/20 dark:to-red-900/20 border-warning-200 dark:border-yellow-700">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-warning-600" />
            <div>
              <h2 className="font-bold text-slate-800 dark:text-slate-100">Topics Needing Attention</h2>
              <p className="text-sm text-slate-500">Based on your quiz performance — focus here first</p>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          {mockWeakTopics.map(topic => (
            <div key={topic.id} className="card p-5 hover:shadow-soft transition-all">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-bold text-slate-800 dark:text-slate-100">{topic.topic_name}</h3>
                    <span className={`badge ${ topic.accuracy < 50 ? "badge-red" : "badge-yellow" }`}>
                      {topic.accuracy < 50 ? "High Priority" : "Medium Priority"}
                    </span>
                  </div>
                  <p className="text-sm text-slate-500 mb-3">{topic.recommended_action}</p>

                  <div className="grid grid-cols-3 gap-3 mb-3">
                    {[
                      { label: "Accuracy", value: `${topic.accuracy}%` },
                      { label: "Confidence", value: `${topic.confidence_level}%` },
                      { label: "Attempts", value: topic.total_attempts },
                    ].map(s => (
                      <div key={s.label} className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-2 text-center">
                        <p className="text-lg font-bold text-slate-700 dark:text-slate-200">{s.value}</p>
                        <p className="text-xs text-slate-400">{s.label}</p>
                      </div>
                    ))}
                  </div>

                  <div className="progress-bar">
                    <div className="progress-fill bg-gradient-to-r from-warning-500 to-danger-500" style={{ width: `${topic.accuracy}%` }} />
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <Link to="/ai-tutor" className="btn-primary btn-sm">
                    <BookOpen className="w-4 h-4" /> Study
                  </Link>
                  <Link to="/mcq" className="btn-outline btn-sm">
                    <TrendingUp className="w-4 h-4" /> Practice
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
