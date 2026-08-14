import AppLayout from "@/components/layout/AppLayout";
import { RotateCcw, Clock, AlertTriangle } from "lucide-react";
import { mockRevisionPlan } from "@/data/mockData";

const statusColor = (s: string) => s === "Overdue" ? "badge-red" : s === "Due" ? "badge-yellow" : "badge-blue";

export default function RevisionPlan() {
  return (
    <AppLayout title="Revision Plan">
      <div className="max-w-4xl mx-auto space-y-4">
        <div className="card p-4 flex items-center gap-3 bg-primary-50 dark:bg-primary-900/20 border-primary-200">
          <RotateCcw className="w-5 h-5 text-primary-600" />
          <p className="text-sm font-medium text-primary-700 dark:text-primary-300">
            Spaced repetition schedule — items sorted by urgency
          </p>
        </div>

        {mockRevisionPlan.map(item => (
          <div key={item.id} className={`card p-5 hover:shadow-soft transition-all ${ item.status === "Overdue" ? "border-danger-200 dark:border-red-700" : "" }`}>
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                {item.status === "Overdue" && <AlertTriangle className="w-5 h-5 text-danger-500 flex-shrink-0" />}
                <div>
                  <h3 className="font-bold text-slate-800 dark:text-slate-100">{item.topic}</h3>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-slate-500">{item.type}</span>
                    <span className="text-xs flex items-center gap-1 text-slate-500"><Clock className="w-3 h-3" />{item.estimatedMinutes}m</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`badge ${statusColor(item.status)}`}>{item.dueLabel}</span>
                <button className="btn-primary btn-sm">Start</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </AppLayout>
  );
}
