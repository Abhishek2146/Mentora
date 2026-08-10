import DashboardLayout from "@/components/layout/DashboardLayout";
import apiClient from "@/lib/api";
import { useEffect, useState } from "react";
import { Syllabus } from "@/types";

export default function StudyPlanPage() {
  const [syllabuses, setSyllabuses] = useState<Syllabus[]>([]);
  const [selectedSyllabus, setSelectedSyllabus] = useState<Syllabus | null>(null);
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

  const generatePlan = async () => {
    if (!selectedSyllabus) return;
    setLoading(true);
    try {
      await apiClient.post("/api/v1/study-plan/generate", {
        syllabus_id: selectedSyllabus.id,
        start_date: new Date().toISOString(),
      });
      alert("Plan generated!");
      window.location.reload();
    } catch (error) {
      console.error("Failed to generate plan:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900">Study Plan</h1>
        <p className="text-gray-600">Your personalized AI-generated study plan.</p>

        {!selectedSyllabus ? (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Select a Syllabus</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {syllabuses.map((s) => (
                <div
                  key={s.id}
                  className="border border-gray-200 rounded-lg p-4 cursor-pointer hover:border-primary-500 hover:bg-primary-50"
                  onClick={() => setSelectedSyllabus(s)}
                >
                  <h3 className="font-semibold text-lg">{s.title}</h3>
                  <p className="text-sm text-gray-600 mt-1">{s.description}</p>
                  <span className={`text-xs px-2 py-1 rounded-full mt-2 inline-block ${
                    s.status === "parsed" ? "bg-green-100 text-green-800" :
                    s.status === "processing" ? "bg-yellow-100 text-yellow-800" :
                    "bg-gray-100 text-gray-800"
                  }`}>
                    {s.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow p-6">
            <button
              onClick={() => setSelectedSyllabus(null)}
              className="text-primary-600 hover:text-primary-700 mb-4"
            >
              ← Back to Syllabi
            </button>
            <h2 className="text-xl font-semibold mb-2">{selectedSyllabus.title}</h2>
            <button
              onClick={generatePlan}
              disabled={loading || selectedSyllabus.status !== "parsed"}
              className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
            >
              {loading ? "Generating..." : "Generate AI Study Plan"}
            </button>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
