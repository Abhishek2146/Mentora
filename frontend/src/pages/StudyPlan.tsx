import { useState, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import {
  Calendar,
  CheckCircle2,
  Loader2,
  Plus,
  Trash2,
  AlarmClock,
  Pencil,
  X,
  Save,
} from "lucide-react";
import { studyPlanService, StudyPlan, StudyTask } from "@/services/studyPlanService";
import { syllabusService } from "@/services/syllabusService";

// ------------------------------------------------------------------ helpers

function calcDaysRemaining(examDate: string | null): number | null {
  if (!examDate) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const exam = new Date(examDate + "T00:00:00");
  return Math.round((exam.getTime() - today.getTime()) / 86_400_000);
}

function formatExamDate(examDate: string): string {
  return new Date(examDate + "T00:00:00").toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function DaysRemaining({ days }: { days: number | null }) {
  if (days === null) return null;
  if (days > 0)
    return (
      <span className="text-sm font-semibold text-primary-600 dark:text-primary-400">
        {days} day{days !== 1 ? "s" : ""} remaining
      </span>
    );
  if (days === 0)
    return (
      <span className="text-sm font-semibold text-warning-600 dark:text-warning-400">
        Exam is today
      </span>
    );
  return (
    <span className="text-sm font-semibold text-danger-600 dark:text-danger-400">
      Exam was {Math.abs(days)} day{Math.abs(days) !== 1 ? "s" : ""} ago
    </span>
  );
}

// ------------------------------------------------------------------ ExamDateSection

interface ExamDateSectionProps {
  plan: StudyPlan;
  onUpdated: (updated: StudyPlan) => void;
}

function ExamDateSection({ plan, onUpdated }: ExamDateSectionProps) {
  const [editing, setEditing] = useState(false);
  const [inputDate, setInputDate] = useState(plan.exam_date || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Keep local state in sync when a different plan is selected
  useEffect(() => {
    setInputDate(plan.exam_date || "");
    setEditing(false);
    setError(null);
  }, [plan.id, plan.exam_date]);

  const days = calcDaysRemaining(plan.exam_date);

  async function handleSave() {
    setError(null);
    if (!inputDate) {
      setError("Please select a valid exam date.");
      return;
    }
    // Validate: exam_date must be >= start_date
    if (inputDate < plan.start_date) {
      setError("Exam date cannot be before the plan start date.");
      return;
    }
    setSaving(true);
    try {
      const updated = await studyPlanService.updatePlan(plan.id, {
        exam_date: inputDate,
      });
      onUpdated(updated);
      setEditing(false);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to save exam date.");
    } finally {
      setSaving(false);
    }
  }

  async function handleClear() {
    setSaving(true);
    setError(null);
    try {
      const updated = await studyPlanService.updatePlan(plan.id, {
        exam_date: null,
      });
      onUpdated(updated);
      setInputDate("");
      setEditing(false);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to clear exam date.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card p-4 sm:p-5 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <AlarmClock className="w-4 h-4 text-primary-500 flex-shrink-0" />
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
            Exam Date
          </span>
        </div>
        {!editing && (
          <button
            onClick={() => { setEditing(true); setInputDate(plan.exam_date || ""); }}
            className="btn-ghost btn-sm"
            aria-label="Edit exam date"
          >
            <Pencil className="w-3.5 h-3.5" />
            {plan.exam_date ? "Edit" : "Set date"}
          </button>
        )}
      </div>

      {/* Display mode */}
      {!editing && plan.exam_date && (
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide">Exam Date</p>
            <p className="text-base font-bold text-slate-800 dark:text-slate-100 mt-0.5">
              {formatExamDate(plan.exam_date)}
            </p>
          </div>
          <div className="border-l border-slate-200 dark:border-slate-700 pl-3">
            <DaysRemaining days={days} />
          </div>
        </div>
      )}

      {!editing && !plan.exam_date && (
        <p className="text-sm text-slate-400 italic">
          No exam date set. Click "Set date" to add one.
        </p>
      )}

      {/* Edit mode */}
      {editing && (
        <div className="space-y-2">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">
              Select Exam Date
            </label>
            <input
              type="date"
              value={inputDate}
              min={plan.start_date}
              onChange={(e) => { setInputDate(e.target.value); setError(null); }}
              className="input w-full sm:w-64"
            />
          </div>
          {inputDate && (
            <DaysRemaining days={calcDaysRemaining(inputDate)} />
          )}
          {error && (
            <p className="text-xs text-danger-600 dark:text-danger-400">{error}</p>
          )}
          <div className="flex flex-wrap gap-2 pt-1">
            <button
              onClick={handleSave}
              disabled={saving || !inputDate}
              className="btn-primary btn-sm"
            >
              {saving ? (
                <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Saving…</>
              ) : (
                <><Save className="w-3.5 h-3.5" /> Save</>
              )}
            </button>
            {plan.exam_date && (
              <button
                onClick={handleClear}
                disabled={saving}
                className="btn-ghost btn-sm text-danger-500 hover:text-danger-700"
              >
                <X className="w-3.5 h-3.5" /> Clear
              </button>
            )}
            <button
              onClick={() => { setEditing(false); setError(null); }}
              disabled={saving}
              className="btn-ghost btn-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ Main page

export default function StudyPlanPage() {
  const [plans, setPlans] = useState<StudyPlan[]>([]);
  const [syllabi, setSyllabi] = useState<any[]>([]);
  const [activePlan, setActivePlan] = useState<StudyPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedSyllabusId, setSelectedSyllabusId] = useState<number | "">("");
  const [startDate, setStartDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [endDate, setEndDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    return d.toISOString().split("T")[0];
  });
  const [examDate, setExamDate] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [taskError, setTaskError] = useState<string | null>(null);

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
    if (examDate && examDate < startDate) {
      setError("Exam date cannot be before the start date.");
      return;
    }
    if (endDate && examDate && endDate > examDate) {
      setError("End date cannot be after the exam date.");
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      // If exam date is set, it is the hard deadline.
      // Send end_date = min(endDate, examDate) so the backend
      // never generates tasks past the exam.
      let effectiveEnd = endDate || undefined;
      if (examDate) {
        effectiveEnd = (!endDate || examDate < endDate) ? examDate : endDate;
      }
      const plan = await studyPlanService.generatePlan(
        selectedSyllabusId as number,
        startDate,
        effectiveEnd,
        examDate || undefined
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
    setTaskError(null);
    try {
      await studyPlanService.toggleTask(task.id, !task.completed);
      setActivePlan({
        ...activePlan,
        tasks: activePlan.tasks.map((t) =>
          t.id === task.id ? { ...t, completed: !t.completed } : t
        ),
      });
    } catch (e: any) {
      setTaskError(e?.response?.data?.detail || "Failed to update task.");
    }
  }

  async function handleDeletePlan(planId: number) {
    setTaskError(null);
    try {
      await studyPlanService.deletePlan(planId);
      const remaining = plans.filter((p) => p.id !== planId);
      setPlans(remaining);
      if (activePlan?.id === planId) {
        setActivePlan(remaining.length > 0 ? remaining[0] : null);
      }
    } catch (e: any) {
      setTaskError(e?.response?.data?.detail || "Failed to delete plan.");
    }
  }

  function handlePlanUpdated(updated: StudyPlan) {
    setActivePlan(updated);
    setPlans((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
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
                <p className="text-slate-500">
                  No study plans yet. Generate one from your syllabus.
                </p>
                <button onClick={() => setShowForm(true)} className="btn-primary btn-md">
                  <Plus className="w-4 h-4" /> Generate Study Plan
                </button>
              </div>
            )}

            {showForm && (
              <div className="card p-6 space-y-4">
                <h3 className="font-bold text-slate-800 dark:text-slate-100">
                  Generate AI Study Plan
                </h3>
                {error && <p className="text-sm text-danger-600">{error}</p>}

                <div>
                  <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">
                    Syllabus
                  </label>
                  <select
                    value={selectedSyllabusId}
                    onChange={(e) => setSelectedSyllabusId(Number(e.target.value) || "")}
                    className="input"
                  >
                    <option value="">Select a syllabus...</option>
                    {syllabi.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.title} ({s.subjects?.length || 0} subjects)
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">
                      Start Date
                    </label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">
                      End Date{" "}
                      <span className="text-slate-400 font-normal">(optional if exam date set)</span>
                    </label>
                    <input
                      type="date"
                      value={endDate}
                      min={startDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="input"
                    />
                  </div>
                </div>

                {/* Exam Date field */}
                <div>
                  <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">
                    <AlarmClock className="w-3.5 h-3.5 inline mr-1 text-primary-500" />
                    Exam Date{" "}
                    <span className="text-slate-400 font-normal">(optional)</span>
                  </label>
                  <input
                    type="date"
                    value={examDate}
                    min={startDate}
                    onChange={(e) => { setExamDate(e.target.value); setError(null); }}
                    className="input sm:w-64"
                  />
                  {examDate && (
                    <p className="mt-1.5 text-xs">
                      <DaysRemaining days={calcDaysRemaining(examDate)} />
                    </p>
                  )}
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={handleGenerate}
                    disabled={!selectedSyllabusId || generating}
                    className="btn-primary btn-md flex-1"
                  >
                    {generating ? (
                      <><Loader2 className="w-4 h-4 animate-spin" /> Generating…</>
                    ) : (
                      "Generate Plan"
                    )}
                  </button>
                  <button onClick={() => { setShowForm(false); setError(null); }} className="btn-ghost btn-md">
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {activePlan && (
              <>
                {/* Summary card */}
                <div className="card p-6 bg-gradient-to-r from-secondary-600 to-primary-600 text-white border-0">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-secondary-100 text-sm">Study Plan</p>
                      <h2 className="text-2xl font-bold">{activePlan.title}</h2>
                      <p className="text-secondary-100 mt-1 text-sm">
                        {activePlan.start_date} → {activePlan.end_date || (activePlan.exam_date ? `Exam: ${activePlan.exam_date}` : "Ongoing")}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-4xl font-black">
                        {totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0}%
                      </p>
                      <p className="text-secondary-100 text-sm">
                        {completedCount}/{totalCount} tasks
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 w-full bg-white/20 rounded-full h-2">
                    <div
                      className="bg-white rounded-full h-2 transition-all"
                      style={{
                        width: `${totalCount > 0 ? (completedCount / totalCount) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </div>

                {/* Exam Date section */}
                <ExamDateSection plan={activePlan} onUpdated={handlePlanUpdated} />

                {/* Actions */}
                <div className="flex gap-3">
                  <button
                    onClick={() => { setShowForm(true); setError(null); }}
                    className="btn-ghost btn-sm"
                  >
                    <Plus className="w-4 h-4" /> New Plan
                  </button>
                  <button
                    onClick={() => handleDeletePlan(activePlan.id)}
                    className="btn-ghost btn-sm text-danger-500 hover:text-danger-700"
                  >
                    <Trash2 className="w-4 h-4" /> Delete
                  </button>
                </div>

                {taskError && (
                  <p className="text-sm text-danger-600 dark:text-danger-400">{taskError}</p>
                )}

                {/* Plan switcher */}
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

                {/* Tasks */}
                <div className="space-y-4">
                  {groupTasksByDate(activePlan.tasks).map(([date, tasks]) => (
                    <div key={date} className="card p-5">
                      <h3 className="font-bold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-primary-500" />
                        {date === "No date"
                          ? "Scheduled"
                          : new Date(date + "T00:00:00").toLocaleDateString("en-US", {
                              weekday: "long",
                              month: "short",
                              day: "numeric",
                            })}
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
                              <p
                                className={`text-sm font-medium ${
                                  task.completed
                                    ? "line-through text-slate-400"
                                    : "text-slate-700 dark:text-slate-200"
                                }`}
                              >
                                {task.title}
                              </p>
                              {task.description && (() => {
                                // Extract [Unit › Chapter] prefix added by the backend
                                const bracketMatch = task.description.match(/^\[([^\]]+)\]\s*([\s\S]*)/);
                                const unitTag = bracketMatch?.[1] || null;
                                const rest = bracketMatch?.[2]?.trim() || (!bracketMatch ? task.description : "");
                                return (
                                  <div className="mt-1 space-y-0.5">
                                    {unitTag && (
                                      <span className="inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded bg-secondary-100 dark:bg-secondary-900/40 text-secondary-700 dark:text-secondary-300 truncate max-w-full">
                                        {unitTag}
                                      </span>
                                    )}
                                    {rest && (
                                      <p className="text-xs text-slate-500 truncate">{rest}</p>
                                    )}
                                  </div>
                                );
                              })()}
                            </div>
                            <span
                              className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                                task.task_type === "weak_topic_review"
                                  ? "bg-amber-100 text-amber-700"
                                  : task.task_type === "quiz"
                                  ? "bg-warning-100 text-warning-700"
                                  : "bg-primary-100 text-primary-700"
                              }`}
                            >
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
