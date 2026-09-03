import { useState, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { Calendar, Clock, CheckCircle2, Loader2, Plus, Trash2, ChevronDown } from "lucide-react";
import { studyPlanService, StudyPlan, StudyTask } from "@/services/studyPlanService";
import { syllabusService } from "@/services/syllabusService";

export default function StudyPlanPage() {
  const [plans, setPlans] = useState<StudyPlan[]>([]);
  const [syllabi, setSyllabi] = useState<any[]>([]);
  const [activePlan, setActivePlan] = useState<StudyPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedSyllabusId, setSelectedSyllabusId] = useState<number | "">("");
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    return d.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    return d.toISOString().split("T")[0];
  });
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [plansData, syllabiData] = await Promise.all([
        studyPlanService.getAllPlans(),
        syllabusService.getAllSyllabi(),
      ]);
      setPlans(plansData);
      setSyllabi(syllabiData);
      if (plansData.length > 0 && !activePlan) {
        setActivePlan(plansData[0]);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerate() {
    if (!selectedSyllabusId) return;
    setGenerating(true);
    setError(null);
    try {
      const plan = await studyPlanService.generatePlan(
        selectedSyllabusId as number,
        startDate,
        endDate
      );
      setActivePlan(plan);
      setPlans((prev) => [plan, ...prev]);
      setShowForm(false);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to generate study plan");
    } finally {
      setGenerating(false);
    }
  }

  async function handleToggleTask(task: StudyTask) {
    if (!activePlan) return;
    try {
      await studyPlanService.toggleTask(task.id, !task.completed);
      setActivePlan({
        ...activePlan,
        tasks: activePlan.tasks.map((t) =>
          t.id === task.id ? { ...t, completed: !t.completed } : t
        ),
      });
    } catch {}
  }

  async function handleDeletePlan(planId: number) {
    try {
      await studyPlanService.deletePlan(planId);
      setPlans((prev) => prev.filter((p) => p.id !== planId));
      if (activePlan?.id === planId) {
        setActivePlan(plans.length > 1 ? plans.find((p) => p.id !== planId) || null : null);
      }
    } catch {}
  }

  function groupTasksByDate(tasks: StudyTask[]) {
    const grouped: Record<string, StudyTask[]> = {};
    tasks.forEach((t) => {
      const key = t.due_date || "No date";
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(t);
    });
    return Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b));
  }

  const completedCount = activePlan?.tasks.filter((t) => t.completed).length || 0;
  const totalCount = activePlan?.tasks.length || 0;

  return (
    <AppLayout title="Study Plan">
      <div className="max-w-4xl mx-auto space-y-6">
        {loading ? (
          <div className="card p-12 text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary-500" />
            <p className="mt-4 text-slate-500">Loading study plans...</p>
          </div>
        ) : (
          <>
            {!activePlan && !showForm && (
              <div className="card p-12 text-center space-y-4">
                <Calendar className="w-12 h-12 mx-auto text-slate-300" />
                <p className="text-slate-500">No study plans yet. Generate one from your syllabus.</p>
                <button onClick={() => setShowForm(true)} className="btn-primary">
                  <Plus className="w-4 h-4 inline mr-2" /> Generate Study Plan
                </button>
              </div>
            )}

            {showForm && (
              <div className="card p-6 space-y-4">
                <h3 className="font-bold text-slate-800 dark:text-slate-100">Generate AI Study Plan</h3>
                {error && <p className="text-sm text-red-500">{error}</p>}
                <div>
                  <label className="block text-sm font-medium text-slate-600 mb-1">Syllabus</label>
                  <select
                    value={selectedSyllabusId}
                    onChange={(e) => setSelectedSyllabusId(Number(e.target.value) || "")}
                    className="w-full border rounded-xl px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-600"
                  >
                    <option value="">Select a syllabus...</option>
                    {syllabi.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.title} ({s.subjects?.length || 0} subjects)
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-600 mb-1">Start Date</label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="w-full border rounded-xl px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-600"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-600 mb-1">End Date</label>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="w-full border rounded-xl px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-600"
                    />
                  </div>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={handleGenerate}
                    disabled={!selectedSyllabusId || generating}
                    className="btn-primary flex-1"
                  >
                    {generating ? (
                      <><Loader2 className="w-4 h-4 animate-spin inline mr-2" /> Generating...</>
                    ) : (
                      "Generate Plan"
                    )}
                  </button>
                  <button onClick={() => setShowForm(false)} className="btn-ghost">
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {activePlan && (
              <>
                <div className="card p-6 bg-gradient-to-r from-secondary-600 to-primary-600 text-white border-0">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-secondary-100 text-sm">Study Plan</p>
                      <h2 className="text-2xl font-bold">{activePlan.title}</h2>
                      <p className="text-secondary-100 mt-1 text-sm">
                        {activePlan.start_date} → {activePlan.end_date || "Ongoing"}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-4xl font-black">
                        {totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0}%
                      </p>
                      <p className="text-secondary-100 text-sm">{completedCount}/{totalCount} tasks</p>
                    </div>
                  </div>
                  <div className="mt-3 w-full bg-white/20 rounded-full h-2">
                    <div
                      className="bg-white rounded-full h-2 transition-all"
                      style={{ width: `${totalCount > 0 ? (completedCount / totalCount) * 100 : 0}%` }}
                    />
                  </div>
                </div>

                <div className="flex gap-3">
                  <button onClick={() => setShowForm(true)} className="btn-ghost btn-sm">
                    <Plus className="w-4 h-4 inline mr-1" /> New Plan
                  </button>
                  <button
                    onClick={() => handleDeletePlan(activePlan.id)}
                    className="btn-ghost btn-sm text-red-500 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4 inline mr-1" /> Delete
                  </button>
                </div>

                {plans.length > 1 && (
                  <div className="flex gap-2 overflow-x-auto pb-2">
                    {plans.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => setActivePlan(p)}
                        className={`px-3 py-1 rounded-lg text-xs whitespace-nowrap border transition ${
                          p.id === activePlan.id
                            ? "bg-primary-100 border-primary-300 text-primary-700"
                            : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600"
                        }`}
                      >
                        {p.title}
                      </button>
                    ))}
                  </div>
                )}

                <div className="space-y-4">
                  {groupTasksByDate(activePlan.tasks).map(([date, tasks]) => (
                    <div key={date} className="card p-5">
                      <h3 className="font-bold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-primary-500" />
                        {date === "No date" ? "Scheduled" : new Date(date + "T00:00:00").toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })}
                      </h3>
                      <div className="space-y-2">
                        {tasks.map((task) => (
                          <div
                            key={task.id}
                            onClick={() => handleToggleTask(task)}
                            className={`flex items-center gap-4 p-3 rounded-xl border cursor-pointer transition ${
                              task.completed
                                ? "bg-emerald-50 border-emerald-200 dark:bg-emerald-900/20"
                                : task.task_type === "weak_topic_review"
                                ? "bg-amber-50 border-amber-200 dark:bg-amber-900/20"
                                : "bg-primary-50 border-primary-200 dark:bg-primary-900/20"
                            }`}
                          >
                            <CheckCircle2
                              className={`w-5 h-5 flex-shrink-0 ${
                                task.completed ? "text-emerald-500" : "text-slate-300"
                              }`}
                            />
                            <div className="flex-1 min-w-0">
                              <p className={`text-sm font-medium ${task.completed ? "line-through text-slate-400" : "text-slate-700 dark:text-slate-200"}`}>
                                {task.title}
                              </p>
                              {task.description && (
                                <p className="text-xs text-slate-500 mt-0.5 truncate">{task.description}</p>
                              )}
                            </div>
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                              task.task_type === "weak_topic_review"
                                ? "bg-amber-100 text-amber-700"
                                : task.task_type === "quiz"
                                ? "bg-warning-100 text-warning-700"
                                : "bg-primary-100 text-primary-700"
                            }`}>
                              {task.task_type || "study"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                  {activePlan.tasks.length === 0 && (
                    <div className="card p-8 text-center text-slate-400">
                      No tasks generated yet.
                    </div>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </AppLayout>
  );
}
