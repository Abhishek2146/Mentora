import { useState, useEffect, useMemo } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { useAuthStore } from "@/store/authStore";
import { apiClient } from "@/lib/api";
import { cn, formatDate, formatTime } from "@/lib/utils";

interface CalendarDay {
  date: string;
  dayOfWeek: string;
  studyMinutes: number;
  qualifying: boolean;
  heatmapLevel: number;
}

interface WeekColumn {
  weekStart: string;
  days: (CalendarDay | null)[];
}

const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

const DAY_LABELS = ["Mon", "", "Wed", "", "Fri", "", ""];

function getHeatmapColor(level: number): string {
  switch (level) {
    case 0: return "bg-slate-100 dark:bg-slate-700/50";
    case 1: return "bg-emerald-100 dark:bg-emerald-900/40";
    case 2: return "bg-emerald-300 dark:bg-emerald-700/60";
    case 3: return "bg-emerald-500 dark:bg-emerald-500/80";
    case 4: return "bg-emerald-700 dark:bg-emerald-400";
    default: return "bg-slate-100 dark:bg-slate-700/50";
  }
}

function buildWeekColumns(calendar: CalendarDay[]): WeekColumn[] {
  if (!calendar.length) return [];

  const dateMap = new Map<string, CalendarDay>();
  calendar.forEach((d) => dateMap.set(d.date, d));

  // Find the first Sunday on or before the first calendar date
  const firstDate = new Date(calendar[0].date + "T00:00:00");
  const firstDayOfWeek = firstDate.getDay(); // 0=Sun
  const gridStart = new Date(firstDate);
  gridStart.setDate(gridStart.getDate() - firstDayOfWeek);

  // Find the last Saturday on or after the last calendar date
  const lastDate = new Date(calendar[calendar.length - 1].date + "T00:00:00");
  const lastDayOfWeek = lastDate.getDay();
  const gridEnd = new Date(lastDate);
  gridEnd.setDate(gridEnd.getDate() + (6 - lastDayOfWeek));

  const weeks: WeekColumn[] = [];
  const current = new Date(gridStart);

  while (current <= gridEnd) {
    const weekStart = current.toISOString().slice(0, 10);
    const days: (CalendarDay | null)[] = [];

    for (let i = 0; i < 7; i++) {
      const dateStr = current.toISOString().slice(0, 10);
      days.push(dateMap.get(dateStr) ?? null);
      current.setDate(current.getDate() + 1);
    }

    weeks.push({ weekStart, days });
  }

  return weeks;
}

function getMonthLabels(weeks: WeekColumn[]): { label: string; index: number }[] {
  const labels: { label: string; index: number }[] = [];
  let lastMonth = -1;

  weeks.forEach((week, i) => {
    const month = new Date(week.weekStart + "T00:00:00").getMonth();
    if (month !== lastMonth) {
      labels.push({ label: MONTH_NAMES[month], index: i });
      lastMonth = month;
    }
  });

  return labels;
}

export default function StudyStreak() {
  const { user } = useAuthStore();
  const [streak, setStreak] = useState<any>(null);
  const [activity, setActivity] = useState<any>(null);
  const [calendar, setCalendar] = useState<CalendarDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [customMinutes, setCustomMinutes] = useState("");
  const [recordingSession, setRecordingSession] = useState(false);
  const [hoveredDay, setHoveredDay] = useState<CalendarDay | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    fetchStreakData();
  }, []);

  const fetchStreakData = async () => {
    setLoading(true);
    try {
      const [streakRes, activityRes, calendarRes] = await Promise.all([
        apiClient.get("/api/v1/study-streak/streak"),
        apiClient.get("/api/v1/study-streak/activity"),
        apiClient.get("/api/v1/study-streak/calendar"),
      ]);
      setStreak(streakRes.data);
      setActivity(activityRes.data);
      setCalendar(calendarRes.data);
    } catch (error) {
      console.error("Failed to fetch streak data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleRecordSession = async (minutes: number) => {
    setRecordingSession(true);
    try {
      const res = await apiClient.post("/api/v1/study-streak/session", {
        study_minutes: minutes,
      });
      if (res.data?.is_new_record && res.data?.message) {
        alert(res.data.message);
      }
      setCustomMinutes("");
      await fetchStreakData();
    } catch (error) {
      console.error("Failed to record session:", error);
    } finally {
      setRecordingSession(false);
    }
  };

  const handleCustomSubmit = () => {
    const mins = parseInt(customMinutes, 10);
    if (!isNaN(mins) && mins > 0 && mins <= 480) {
      handleRecordSession(mins);
    }
  };

  const weekColumns = useMemo(() => buildWeekColumns(calendar), [calendar]);
  const monthLabels = useMemo(() => getMonthLabels(weekColumns), [weekColumns]);

  const selectedDay = useMemo(() => {
    if (!selectedDate) return null;
    return calendar.find((d) => d.date === selectedDate) ?? null;
  }, [selectedDate, calendar]);

  return (
    <AppLayout title="Study Streak">
      <div className="space-y-6">
        {/* Dashboard Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {streak && (
            <div className="border rounded-lg p-4 bg-white dark:bg-slate-800">
              <div className="text-2xl font-bold text-primary-600 dark:text-primary-400">
                {streak.current_streak}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                day{streak.current_streak !== 1 ? "s" : ""} current
              </div>
            </div>
          )}
          {streak && (
            <div className="border rounded-lg p-4 bg-white dark:bg-slate-800">
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {streak.longest_streak}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                longest streak
              </div>
            </div>
          )}
          {streak && (
            <div className="border rounded-lg p-4 bg-white dark:bg-slate-800">
              <div className="text-2xl font-bold text-cyan-600 dark:text-cyan-400">
                {streak.total_study_days}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                study days
              </div>
            </div>
          )}
          {activity && (
            <div className="border rounded-lg p-4 bg-white dark:bg-slate-800">
              <div className="text-2xl font-bold text-slate-800 dark:text-slate-100">
                {formatTime(activity.today_study_minutes)}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                today{activity.today_qualifying ? " ✓" : ""}
              </div>
            </div>
          )}
        </div>

        {/* GitHub-style Heatmap */}
        {!loading && (
          <div className="border rounded-lg p-4 bg-white dark:bg-slate-800">
            <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-3">
              Study Activity
            </h2>

            <div className="overflow-x-auto">
              <div className="inline-flex flex-col gap-0.5">
                {/* Month labels row */}
                <div className="relative ml-7" style={{ height: "14px" }}>
                  {monthLabels.map((m, i) => (
                    <span
                      key={`${m.label}-${i}`}
                      className="absolute text-[10px] text-slate-500 dark:text-slate-400"
                      style={{ left: `${m.index * 12}px` }}
                    >
                      {m.label}
                    </span>
                  ))}
                </div>

                {/* Heatmap grid */}
                <div className="flex gap-0">
                  {/* Day labels column */}
                  <div className="flex flex-col gap-0.5 mr-1">
                    {DAY_LABELS.map((label, i) => (
                      <div
                        key={i}
                        className="text-[10px] text-slate-500 dark:text-slate-400 flex items-center"
                        style={{ height: "12px", width: "24px" }}
                      >
                        {label}
                      </div>
                    ))}
                  </div>

                {/* Week columns */}
                {weekColumns.map((week) => (
                    <div key={week.weekStart} className="flex flex-col gap-[2px]">
                      {week.days.map((day, dayIndex) => {
                        if (!day) {
                          return (
                            <div
                              key={dayIndex}
                              style={{ width: "12px", height: "12px" }}
                            />
                          );
                        }
                        return (
                          <div
                            key={day.date}
                            className={cn(
                              "rounded-sm cursor-pointer transition-all",
                              getHeatmapColor(day.heatmapLevel),
                              selectedDate === day.date && "ring-1 ring-slate-400 dark:ring-slate-500"
                            )}
                            style={{ width: "12px", height: "12px" }}
                            onClick={() => setSelectedDate(day.date === selectedDate ? null : day.date)}
                            onMouseEnter={(e) => {
                              setHoveredDay(day);
                              setTooltipPos({ x: e.clientX, y: e.clientY });
                            }}
                            onMouseLeave={() => setHoveredDay(null)}
                          />
                        );
                      })}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Legend */}
            <div className="flex items-center gap-1.5 mt-3 text-[10px] text-slate-500 dark:text-slate-400">
              <span>Less</span>
              <div className="w-3 h-3 rounded-sm bg-slate-100 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600" />
              <div className="w-3 h-3 rounded-sm bg-emerald-100 dark:bg-emerald-900/40" />
              <div className="w-3 h-3 rounded-sm bg-emerald-300 dark:bg-emerald-700/60" />
              <div className="w-3 h-3 rounded-sm bg-emerald-500 dark:bg-emerald-500/80" />
              <div className="w-3 h-3 rounded-sm bg-emerald-700 dark:bg-emerald-400" />
              <span>More</span>
            </div>
          </div>
        )}

        {/* Tooltip */}
        {hoveredDay && (
          <div
            className="fixed z-50 px-2.5 py-1.5 rounded-md bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 text-xs font-medium pointer-events-none shadow-lg"
            style={{ left: tooltipPos.x + 12, top: tooltipPos.y - 40 }}
          >
            {formatTime(hoveredDay.studyMinutes)} studied on {hoveredDay.date}
          </div>
        )}

        {/* Selected Day Details */}
        {selectedDate && selectedDay && (
          <div className="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
            <h3 className="text-sm font-medium text-slate-800 dark:text-slate-100 mb-2">
              {selectedDate}
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-slate-500 dark:text-slate-400">Study time</p>
                <p className="text-lg font-bold">{formatTime(selectedDay.studyMinutes)}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500 dark:text-slate-400">Qualifying</p>
                <p className={cn(
                  "text-lg font-bold",
                  selectedDay.qualifying ? "text-green-600" : "text-slate-400"
                )}>
                  {selectedDay.qualifying ? "Yes" : "No"}
                </p>
              </div>
            </div>
            <button
              onClick={() => setSelectedDate(null)}
              className="mt-3 py-1 px-3 rounded-md text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600"
            >
              Close
            </button>
          </div>
        )}

        {/* Record Study Session */}
        <div className="border rounded-lg p-4 bg-white dark:bg-slate-800">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-3">
            Record Study Session
          </h2>
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="1"
                max="480"
                value={customMinutes}
                onChange={(e) => setCustomMinutes(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleCustomSubmit(); }}
                placeholder="Minutes"
                className="w-24 rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <button
                onClick={handleCustomSubmit}
                disabled={recordingSession || !customMinutes || parseInt(customMinutes) <= 0}
                className="px-3 py-1.5 rounded-md text-sm font-medium bg-primary-600 text-white hover:bg-primary-500 disabled:opacity-50"
              >
                {recordingSession ? "Saving..." : "Save"}
              </button>
            </div>
            <div className="flex gap-1.5">
              {[15, 30, 45, 60].map((mins) => (
                <button
                  key={mins}
                  onClick={() => handleRecordSession(mins)}
                  disabled={recordingSession}
                  className="px-3 py-1.5 rounded-md text-sm font-medium bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors"
                >
                  {mins}m
                </button>
              ))}
            </div>
          </div>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-2">
            A day with 30+ minutes of study counts toward your streak.
          </p>
        </div>
      </div>
    </AppLayout>
  );
}
