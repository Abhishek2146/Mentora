import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { RotateCcw, Clock, AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import apiClient from "@/lib/api";

interface RevisionItem {
  id: number;
  topic_name: string;
  scheduled_date: string;
  revision_method: string;
  priority: string;
  completed: boolean;
}

interface FlatItem extends RevisionItem {
  schedule_title: string;
}

const dueLabel = (dateStr: string) => {
  const today = new Date().setHours(0, 0, 0, 0);
  const due = new Date(dateStr).setHours(0, 0, 0, 0);
  if (due < today) return "Overdue";
  if (due === today) return "Due Today";
  return new Date(dateStr).toLocaleDateString(undefined, { month: "short", day: "numeric" });
};

const statusColor = (dateStr: string) => {
  const today = new Date().setHours(0, 0, 0, 0);
  const due = new Date(dateStr).setHours(0, 0, 0, 0);
  if (due < today) return "badge-red";
  if (due === today) return "badge-yellow";
  return "badge-blue";
};

export default function RevisionPlan() {
  const [items, setItems] = useState<FlatItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [completingId, setCompletingId] = useState<number | null>(null);
  const [generating, setGenerating] = useState(false);

  const loadItems = async () => {
    const schedulesRes = await apiClient.get("/api/v1/revision/schedules");
    const schedules = schedulesRes.data ?? [];

    const details = await Promise.all(
      schedules.map((s: { id: number; title: string }) =>
        apiClient
          .get(`/api/v1/revision/schedules/${s.id}`)
          .then(res => ({
            title: s.title,
            items: (res.data?.items ?? []) as RevisionItem[],
          }))
          .catch(() => ({ title: s.title, items: [] as RevisionItem[] }))
      )
    );

    setItems(
      details.flatMap((d: { title: string; items: RevisionItem[] }) =>
        d.items.map(item => ({ ...item, schedule_title: d.title }))
      )
    );
  };

  useEffect(() => {
    (async () => {
      try {
        await loadItems();
      } catch {
        setError("Could not load your revision plan. Please try again later.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const generatePlan = async () => {
    setGenerating(true);
    setError("");
    try {
      const syllabusRes = await apiClient.get("/api/v1/syllabus/");
      const syllabi = [...(syllabusRes.data ?? [])].sort(
        (a: any, b: any) =>
          new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime()
      );
      if (!syllabi.length) {
        setError("Upload a syllabus first to generate a revision plan.");
        return;
      }
      const start = new Date();
      const end = new Date();
      end.setDate(end.getDate() + 13);
      await apiClient.post("/api/v1/revision/schedule", null, {
        params: {
          syllabus_id: syllabi[0].id,
          start_date: start.toISOString().slice(0, 10),
          end_date: end.toISOString().slice(0, 10),
        },
        timeout: 300000,
      });
      await loadItems();
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      setError(
        typeof detail === "string" && detail
          ? detail
          : e?.message || "Failed to generate the revision plan"
      );
    } finally {
      setGenerating(false);
    }
  };

  const markComplete = async (id: number) => {
    setCompletingId(id);
    try {
      await apiClient.put(`/api/v1/revision/items/${id}?completed=true`);
      setItems(prev => prev.map(i => (i.id === id ? { ...i, completed: true } : i)));
    } catch {
      // leave state unchanged on failure
    } finally {
      setCompletingId(null);
    }
  };

  const sorted = [...items].sort((a, b) => {
    if (a.completed !== b.completed) return a.completed ? 1 : -1;
    return a.scheduled_date.localeCompare(b.scheduled_date);
  });

  return (
    <AppLayout title="Revision Plan">
      <div className="max-w-4xl mx-auto space-y-4">
        <div className="card p-4 flex items-center gap-3 bg-primary-50 dark:bg-primary-900/20 border-primary-200">
          <RotateCcw className="w-5 h-5 text-primary-600" />
          <p className="text-sm font-medium text-primary-700 dark:text-primary-300">
            Spaced repetition schedule — items sorted by urgency
          </p>
        </div>

        {loading && (
          <div className="flex justify-center py-10">
            <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
          </div>
        )}

        {!loading && error && (
          <div className="card p-5 text-sm text-danger-600 dark:text-danger-400">{error}</div>
        )}

        <div className="flex justify-end">
          <button className="btn-primary btn-sm" disabled={generating} onClick={generatePlan}>
            {generating ? "Generating..." : "Generate Plan"}
          </button>
        </div>

        {!loading && !error && sorted.length === 0 && (
          <div className="card p-8 text-center">
            <RotateCcw className="w-10 h-10 mx-auto text-primary-400 mb-3" />
            <p className="font-semibold text-slate-700 dark:text-slate-200">No revision schedule yet</p>
            <p className="text-sm text-slate-500 mt-1">Upload a syllabus to generate your spaced-repetition plan.</p>
          </div>
        )}

        {sorted.map(item => (
          <div key={item.id} className={`card p-4 sm:p-5 hover:shadow-soft transition-all ${ !item.completed && item.scheduled_date < new Date().toISOString().slice(0, 10) ? "border-danger-200 dark:border-danger-700" : "" } ${ item.completed ? "opacity-60" : "" }`}>
            <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
              <div className="flex items-center gap-2 sm:gap-4">
                {!item.completed && item.scheduled_date < new Date().toISOString().slice(0, 10) && (
                  <AlertTriangle className="w-5 h-5 text-danger-500 flex-shrink-0" />
                )}
                {item.completed && <CheckCircle2 className="w-5 h-5 text-success-500 flex-shrink-0" />}
                <div>
                  <h3 className={`font-bold text-slate-800 dark:text-slate-100 ${ item.completed ? "line-through" : "" }`}>{item.topic_name}</h3>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-slate-500">{item.revision_method}</span>
                    <span className="text-xs flex items-center gap-1 text-slate-500"><Clock className="w-3 h-3" />{new Date(item.scheduled_date).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 sm:gap-3">
                <span className={`badge ${item.priority === "high" ? "badge-red" : item.priority === "low" ? "badge-blue" : "badge-yellow"}`}>{item.priority}</span>
                <span className={`badge ${statusColor(item.scheduled_date)}`}>{dueLabel(item.scheduled_date)}</span>
                {!item.completed && (
                  <button
                    className="btn-primary btn-sm"
                    disabled={completingId === item.id}
                    onClick={() => markComplete(item.id)}
                  >
                    {completingId === item.id ? "..." : "Mark Done"}
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </AppLayout>
  );
}
