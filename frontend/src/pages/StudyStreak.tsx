import { useState, useEffect, useMemo } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { apiClient } from "@/lib/api";
import { formatTime } from "@/lib/utils";
import {
  Flame,
  Trophy,
  CalendarDays,
  Clock,
  Target,
  Timer,
  Loader2,
  CheckCircle2,
  X,
  Zap,
  Plus,
} from "lucide-react";

interface CalendarDay {
  date: string;
  day_of_week: string;
  study_minutes: number;
  qualifying: boolean;
  heatmap_level: number;
}

interface WeekColumn {
  weekStart: string;
  days: (CalendarDay | null)[];
}

interface StreakInfo {
  current_streak: number;
  longest_streak: number;
  total_study_days: number;
  total_study_minutes: number;
  last_qualifying_date: string | null;
}

interface ActivitySummary {
  current_streak: number;
  longest_streak: number;
  total_study_days: number;
  total_study_minutes: number;
  today_study_minutes: number;
  today_qualifying: boolean;
  avg_qualifying_minutes: number;
}

function normalizeCalendarDay(raw: any): CalendarDay {
  return {
    date: raw.date,
    day_of_week: raw.dayOfWeek ?? raw.day_of_week ?? "",
    study_minutes: raw.studyMinutes ?? raw.study_minutes ?? 0,
    qualifying: raw.qualifying ?? false,
    heatmap_level: raw.heatmapLevel ?? raw.heatmap_level ?? 0,
  };
}

const MINUTE_STRIDES = [15, 30, 45, 60];
const WEEK_GOAL_MINUTES = 150;
const MILESTONES = [1, 3, 7, 14, 30, 60, 100];
const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function getHeatmapColor(level: number): string {
  switch (level) {
    case 0: return "bg-slate-200 dark:bg-slate-700/60";
    case 1: return "bg-emerald-200 dark:bg-emerald-900/60";
    case 2: return "bg-emerald-300 dark:bg-emerald-700";
    case 3: return "bg-emerald-500 dark:bg-emerald-500";
    case 4: return "bg-emerald-700 dark:bg-emerald-400";
    default: return "bg-slate-200 dark:bg-slate-700/60";
  }
}

function buildWeekColumns(calendar: CalendarDay[]): WeekColumn[] {
  const byDate = new Map(calendar.map((d) => [d.date, d]));
  if (calendar.length === 0) return [];

  const start = new Date(calendar[0].date);
  const end = new Date(calendar[calendar.length - 1].date);
  const first = new Date(start);
  first.setDate(start.getDate() - ((start.getDay() + 6) % 7));

  const columns: WeekColumn[] = [];
  const cursor = new Date(first);
  const last = new Date(end);
  while (cursor <= last) {
    const weekDays: (CalendarDay | null)[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(cursor);
      const key = d.toISOString().slice(0, 10);
      weekDays.push(byDate.get(key) ?? null);
      cursor.setDate(cursor.getDate() + 1);
    }
    columns.push({ weekStart: weekDays[0]?.date ?? "", days: weekDays });
  }
  return columns;
}

function getMonthGroups(columns: WeekColumn[]): { label: string; start: number; end: number }[] {
  const groups: { label: string; start: number; end: number }[] = [];
  columns.forEach((col, i) => {
    const d = col.days.find((day) => day !== null) ?? col.days[0];
    if (!d) return;
    const month = MONTH_NAMES[parseInt(d.date.slice(5, 7), 10) - 1];
    const last = groups[groups.length - 1];
    if (!last || last.label !== month) groups.push({ label: month, start: i, end: i + 1 });
    else last.end = i + 1;
  });
  return groups;
}

function todayKey(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function StudyStreak() {
  const [streak, setStreak] = useState<StreakInfo | null>(null);
  const [activity, setActivity] = useState<ActivitySummary | null>(null);
  const [calendar, setCalendar] = useState<CalendarDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [minutesInput, setMinutesInput] = useState("30");
  const [recording, setRecording] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [streakResp, activityResp, calendarResp] = await Promise.all([
        apiClient.get("/api/v1/study-streak/streak"),
        apiClient.get("/api/v1/study-streak/activity"),
        apiClient.get("/api/v1/study-streak/calendar"),
      ]);
      setStreak(streakResp.data);
      setActivity(activityResp.data);
      setCalendar((calendarResp.data ?? []).map(normalizeCalendarDay));
      setLoadError(false);
    } catch (e) {
      console.error("Failed to load study streak:", e);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  const weeks = useMemo(() => buildWeekColumns(calendar), [calendar]);
  const monthGroups = useMemo(() => getMonthGroups(weeks), [weeks]);

  const currentStreak = streak?.current_streak ?? 0;
  const todayStudied = activity?.today_study_minutes ?? 0;
  const todayQualifying = activity?.today_qualifying ?? false;
  const today = todayKey();

  const weekMinutes = useMemo(() => {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const dow = (now.getDay() + 6) % 7;
    now.setDate(now.getDate() - dow);
    return calendar
      .filter((d) => new Date(d.date) >= now)
      .reduce((sum, d) => sum + (d.study_minutes || 0), 0);
  }, [calendar]);

  const nextMilestone = MILESTONES.find((m) => m > currentStreak);
  const milestonePct = nextMilestone
    ? Math.min(100, Math.round((currentStreak / nextMilestone) * 100))
    : 100;
  const weekPct = Math.min(100, Math.round((weekMinutes / WEEK_GOAL_MINUTES) * 100));

  const selected = calendar.find((d) => d.date === selectedDate) ?? null;

  const recordSession = async (studyMinutes: number) => {
    if (studyMinutes <= 0) return;
    setRecording(true);
    try {
      await apiClient.post("/api/v1/study-streak/session", { study_minutes: studyMinutes });
      await loadData();
      setMinutesInput("30");
      setToast(`Logged ${formatTime(studyMinutes)} of study time. Keep it up!`);
    } catch (e) {
      console.error("Failed to record session:", e);
      setToast("Could not record session. Please try again.");
    } finally {
      setRecording(false);
    }
  };

  const selectedDay = (date: string) => {
    setSelectedDate((prev) => (prev === date ? null : date));
  };

  if (loading) {
    return (
      <AppLayout title="Study Streak">
        <div className="max-w-7xl mx-auto flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Study Streak">
      <div className="max-w-7xl mx-auto space-y-6">
        {loadError ? (
          <div className="card p-8 text-center">
            <Flame className="w-10 h-10 text-primary-400 mx-auto" />
            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mt-3">Could not load your streak</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Something went wrong while fetching your study data.</p>
            <button onClick={() => { setLoading(true); loadData(); }} className="btn btn-primary btn-md mt-4">
              <Loader2 className="w-4 h-4" /> Try again
            </button>
          </div>
        ) : (
          <>
            {/* Hero */}
            <div className="card p-5 sm:p-6 bg-gradient-to-r from-primary-600 via-primary-500 to-secondary-500 text-white border-0 shadow-glow-primary">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-white/20 flex items-center justify-center shrink-0">
                    <Flame className="w-8 h-8 sm:w-9 sm:h-9 text-warning-400" />
                  </div>
                  <div>
                    <p className="text-primary-100 text-sm font-medium">Current streak</p>
                    <h2 className="text-3xl sm:text-4xl font-bold mt-0.5">{currentStreak} day{currentStreak !== 1 ? "s" : ""}</h2>
                  </div>
                </div>
                <div className="flex flex-col sm:items-end gap-1.5 w-full sm:w-auto">
                  <div className={`inline-flex items-center gap-2 rounded-xl px-3 py-2 bg-white/20 w-fit`}>
                    <Timer className="w-4 h-4" />
                    <span className="text-sm font-semibold">
                      {todayQualifying
                        ? "Streak protected today"
                        : todayStudied > 0
                          ? `${formatTime(todayStudied)} studied today`
                          : "Study 30+ min today to keep it up"}
                    </span>
                  </div>
                  {!todayQualifying && (
                    <p className="text-primary-100 text-xs hidden sm:block">
                      {30 - todayStudied > 0 ? `${formatTime(30 - todayStudied)} more this session to qualify` : "Log a session to protect your streak"}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
              {[
                { label: "Current Streak", value: `${currentStreak}d`, icon: Flame, color: "text-warning-600", bg: "bg-warning-50 dark:bg-warning-900/30" },
                { label: "Longest Streak", value: `${streak?.longest_streak ?? 0}d`, icon: Trophy, color: "text-secondary-600", bg: "bg-secondary-50 dark:bg-secondary-900/30" },
                { label: "Study Days", value: `${streak?.total_study_days ?? 0}`, icon: CalendarDays, color: "text-primary-600", bg: "bg-primary-50 dark:bg-primary-900/30" },
                { label: "Total Time", value: formatTime(streak?.total_study_minutes ?? 0), icon: Clock, color: "text-success-600", bg: "bg-success-50 dark:bg-success-900/30" },
              ].map((s) => (
                <div key={s.label} className="stat-card">
                  <div className={`w-10 h-10 rounded-xl ${s.bg} flex items-center justify-center`}>
                    <s.icon className={`w-5 h-5 ${s.color}`} />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">{s.value}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{s.label}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Goals */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
              <div className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="flex items-center gap-2 font-bold text-slate-800 dark:text-slate-100">
                    <Target className="w-4 h-4 text-primary-500" /> Next Milestone
                  </h3>
                  {nextMilestone && (
                    <span className="badge-blue">{nextMilestone - currentStreak} day{nextMilestone - currentStreak !== 1 ? "s" : ""} to go</span>
                  )}
                </div>
                <div className="progress-bar">
                  <div className="progress-fill bg-gradient-to-r from-primary-500 to-secondary-500" style={{ width: `${milestonePct}%` }} />
                </div>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-3">
                  {nextMilestone
                    ? `You're ${milestonePct}% of the way to a ${nextMilestone}-day streak.`
                    : "You've reached the top milestone. Keep the fire burning!"}
                </p>
              </div>

              <div className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="flex items-center gap-2 font-bold text-slate-800 dark:text-slate-100">
                    <Zap className="w-4 h-4 text-warning-500" /> Weekly Goal
                  </h3>
                  <span className="badge-green">{formatTime(weekMinutes)} / {formatTime(WEEK_GOAL_MINUTES)}</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-fill bg-gradient-to-r from-success-500 to-emerald-500" style={{ width: `${weekPct}%` }} />
                </div>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-3">
                  {weekMinutes >= WEEK_GOAL_MINUTES
                    ? "Goal hit! Add a little extra to build momentum."
                    : `${formatTime(Math.max(0, WEEK_GOAL_MINUTES - weekMinutes))} more this week to hit your goal.`}
                </p>
              </div>
            </div>

            {/* Heatmap */}
            <div className="card p-5 sm:p-6">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
                <div className="flex items-center gap-2">
                  <Flame className="w-5 h-5 text-warning-500" />
                  <h3 className="font-bold text-slate-800 dark:text-slate-100">Last 12 months</h3>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-slate-400">
                  <span>Less</span>
                  {[0, 1, 2, 3, 4].map((l) => (
                    <span key={l} className={`w-3 h-3 rounded-sm ${getHeatmapColor(l)}`} />
                  ))}
                  <span>More</span>
                </div>
              </div>

              {weeks.length > 0 ? (
                <div className="overflow-x-auto no-scrollbar -mx-1 px-1">
                  <div
                    className="grid gap-1 w-max"
                    style={{
                      gridTemplateColumns: `auto repeat(${weeks.length}, 12px)`,
                      gridTemplateRows: `auto repeat(7, 12px)`,
                    }}
                  >
                    {monthGroups.map((g) => (
                      <span
                        key={`${g.label}-${g.start}`}
                        className="text-[10px] text-slate-400 font-medium leading-none self-end truncate"
                        style={{ gridColumn: `${g.start + 2} / ${g.end + 2}`, gridRow: 1 }}
                      >
                        {g.label}
                      </span>
                    ))}
                    <span className="text-[10px] text-slate-400 leading-none" style={{ gridColumn: 1, gridRow: 2 }}>Mon</span>
                    <span className="text-[10px] text-slate-400 leading-none" style={{ gridColumn: 1, gridRow: 4 }}>Wed</span>
                    <span className="text-[10px] text-slate-400 leading-none" style={{ gridColumn: 1, gridRow: 6 }}>Fri</span>

                    {weeks.map((col, ci) =>
                      col.days.map((d, di) => (
                        <button
                          key={`${ci}-${di}`}
                          onClick={() => d && selectedDay(d.date)}
                          title={d ? `${d.date}: ${formatTime(d.study_minutes)} ${d.qualifying ? "(qualifying)" : ""}` : "No data"}
                          className={`w-3 h-3 rounded-sm ${d ? getHeatmapColor(d.heatmap_level ?? 0) : "bg-transparent"} transition-transform hover:scale-125 ${
                            d?.date === today ? "ring-2 ring-primary-500 ring-offset-1 ring-offset-white dark:ring-offset-slate-800" : ""
                          }`}
                          style={{ gridColumn: ci + 2, gridRow: di + 2 }}
                        />
                      ))
                    )}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-400 text-center py-8">No activity yet. Start studying to light up your calendar!</p>
              )}

              {selected && (
                <div className="mt-4 rounded-xl border border-primary-200 dark:border-primary-800/60 bg-primary-50/60 dark:bg-primary-950/30 p-4 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-bold text-slate-800 dark:text-slate-100 capitalize">
                      {new Date(`${selected.date}T00:00:00`).toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
                    </p>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                      {selected.study_minutes > 0 ? formatTime(selected.study_minutes) + " studied" : "No study logged"}
                    </p>
                  </div>
                  <span className={selected.qualifying ? "badge-green" : "badge"}>
                    {selected.qualifying ? "Qualifying day" : "Below 30 minutes"}
                  </span>
                  <button onClick={() => setSelectedDate(null)} className="btn btn-ghost btn-sm">
                    <X className="w-4 h-4" /> Close
                  </button>
                </div>
              )}
            </div>

            {/* Record session */}
            <div className="card p-5 sm:p-6">
              <h3 className="font-bold text-slate-800 dark:text-slate-100">Log Study Session</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">A day with 30+ minutes of study counts toward your streak.</p>
              <div className="flex flex-wrap gap-3 mt-4">
                {MINUTE_STRIDES.map((m) => (
                  <button
                    key={m}
                    onClick={() => recordSession(m)}
                    disabled={recording}
                    className="btn btn-outline btn-md"
                  >
                    {formatTime(m)}
                  </button>
                ))}
              </div>
              <div className="flex flex-col sm:flex-row gap-3 mt-4">
                <div className="relative flex-1 max-w-[160px]">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm">+</span>
                  <input
                    type="number"
                    min={1}
                    step={5}
                    value={minutesInput}
                    onChange={(e) => setMinutesInput(e.target.value)}
                    className="input !pl-9"
                    placeholder="Minutes"
                  />
                </div>
                <button
                  onClick={() => recordSession(parseInt(minutesInput, 10) || 0)}
                  disabled={recording}
                  className="btn btn-primary btn-md"
                >
                  {recording ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  {recording ? "Logging..." : "Log custom time"}
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div className="toast bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 border-slate-200 dark:border-slate-700">
          <CheckCircle2 className="w-5 h-5 text-success-500 shrink-0" />
          {toast}
          <button onClick={() => setToast(null)} className="ml-1 text-slate-400 hover:text-slate-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </AppLayout>
  );
}