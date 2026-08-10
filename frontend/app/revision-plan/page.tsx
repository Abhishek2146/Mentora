import DashboardLayout from "@/components/layout/DashboardLayout";
import apiClient from "@/lib/api";
import { useEffect, useState } from "react";
import { Syllabus } from "@/types";

export default function RevisionPlanPage() {
  const [syllabuses, setSyllabuses] = useState<Syllabus[]>([]);
  const [selectedSyllabus, setSelectedSyllabus] = useState<Syllabus | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [schedule, setSchedule] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSyllabuses();
  }, []);

  const fetchSyllabuses = async () => {
    try {
      const response = await apiClient.get("/api/v1/syllabus/");
      setSyllabuses(response.data);
    } catch (error) {
      console.error("Failed to fetch syllabuses:", error);
    }
  };

  const generateSchedule = async () => {
    if (!selectedSyllabus || !startDate) return;
    setLoading(true);
    try {
      const response = await apiClient.post(
        `/api/v1/revision/schedule?syllabus_id=${selectedSyllabus.id}&start_date=${startDate}${endDate ? `&end_date=${endDate}` : ""}`
      );
      setSchedule(response.data);
    } catch (error) {
      console.error("Failed to generate schedule:", error);
    } finally {
      setLoading(false);
    }
  };

  const today = new Date().toISOString().split("T")[0];

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900">Revision Plan</h1>
        <p className="text-gray-600">Create an AI-powered spaced-repetition revision schedule.</p>

        {!schedule ? (
          <div className="bg-white rounded-lg shadow p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Select Syllabus</label>
              <select
                value={selectedSyllabus?.id || ""}
                onChange={(e) => setSelectedSyllabus(syllabuses.find((s) => s.id === parseInt(e.target.value)) || null)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500"
              >
                <option value="">Choose a syllabus...</option>
                {syllabuses.map((s) => (
                  <option key={s.id} value={s.id}>{s.title}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  min={today}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">End Date (Optional)</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>

            <button
              onClick={generateSchedule}
              disabled={loading || !selectedSyllabus || !startDate}
              className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
            >
              {loading ? "Generating..." : "Generate Revision Schedule"}
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow p-6">
            <button onClick={() => setSchedule(null)} className="text-primary-600 hover:text-primary-700 mb-4">
              ← New Schedule
            </button>
            <h2 className="text-xl font-semibold">{schedule.schedule?.title}</h2>
            {schedule.schedule_data?.items && (
              <div className="mt-4 space-y-2">
                {schedule.schedule_data.items.map((item: any, i: number) => (
                  <div key={i} className="p-3 border border-gray-200 rounded-lg">
                    <h4 className="font-medium">{item.topic || item.name}</h4>
                    <p className="text-sm text-gray-500">
                      Scheduled: {item.scheduled_date || "TBD"}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
