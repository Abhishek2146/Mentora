import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import AppLayout from "@/components/layout/AppLayout";
import { syllabusService } from "@/services/syllabusService";
import { FileText, ChevronRight, Loader2, AlertCircle, Clock, BookOpen, Target } from "lucide-react";

interface UnitOut {
  unitNumber: number;
  title: string;
  description?: string;
  estimatedHours: number;
  topics?: string[];
}

interface SyllabusDetail {
  id: number;
  title: string;
  description?: string;
  status: string;
  is_processed: boolean;
  is_ai_processed: boolean;
  estimatedHours: number;
  units: UnitOut[];
}

export default function SyllabusDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [syllabus, setSyllabus] = useState<SyllabusDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "units" | "raw">("overview");

  useEffect(() => {
    if (!id) return;

    const fetchSyllabus = async () => {
      try {
        setLoading(true);
        const res = await syllabusService.getAllSyllabi();
        const found = res.find((s: any) => s.id === parseInt(id));
        if (found) {
          setSyllabus(found);
        } else {
          setError("Syllabus not found");
        }
      } catch (e: any) {
        setError(e?.response?.data?.detail || "Failed to load syllabus");
      } finally {
        setLoading(false);
      }
    };

    fetchSyllabus();
  }, [id]);

  if (loading) {
    return (
      <AppLayout title="Loading...">
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
        </div>
      </AppLayout>
    );
  }

  if (error || !syllabus) {
    return (
      <AppLayout title="Not Found">
        <div className="max-w-md mx-auto text-center py-12">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Syllabus Not Found</h2>
          <p className="text-slate-500 dark:text-slate-400 mt-2">{error || "The syllabus you're looking for doesn't exist."}</p>
          <Link to="/search" className="btn-primary mt-6 inline-block">Back to Search</Link>
        </div>
      </AppLayout>
    );
  }

  const totalTopics = syllabus.units?.reduce((acc: number, u: UnitOut) => acc + (u.topics?.length || 0), 0) || 0;

  return (
    <AppLayout title={syllabus.title}>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="card p-6 space-y-4">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-2xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
              <FileText className="w-8 h-8 text-primary-600 dark:text-primary-400" />
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 truncate">
                {syllabus.title}
              </h1>
              {syllabus.description && (
                <p className="text-slate-600 dark:text-slate-300 mt-1">{syllabus.description}</p>
              )}
              <div className="flex items-center gap-4 mt-3 flex-wrap text-sm text-slate-500 dark:text-slate-400">
                <span className="flex items-center gap-1.5">
                  <BookOpen className="w-4 h-4" />
                  {syllabus.units?.length || 0} Units
                </span>
                <span className="flex items-center gap-1.5">
                  <Target className="w-4 h-4" />
                  {totalTopics} Topics
                </span>
                <span className="flex items-center gap-1.5">
                  <Clock className="w-4 h-4" />
                  {syllabus.estimatedHours}h Est.
                </span>
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                  syllabus.status === "parsed" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" :
                  syllabus.status === "processing" ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" :
                  "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300"
                }`}>
                  {syllabus.status}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="card overflow-hidden">
          <div className="border-b border-slate-200 dark:border-slate-700">
            <nav className="flex -mb-px" aria-label="Tabs">
              {[
                { id: "overview", label: "Overview", icon: FileText },
                { id: "units", label: "Units & Topics", icon: BookOpen },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as "overview" | "units")}
                  className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? "border-primary-500 text-primary-600 dark:text-primary-400"
                      : "border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          <div className="p-6">
            {activeTab === "overview" && (
              <div className="space-y-6">
                {syllabus.description && (
                  <div>
                    <h3 className="font-semibold text-slate-800 dark:text-slate-100 mb-2">Description</h3>
                    <p className="text-slate-600 dark:text-slate-300 whitespace-pre-line">{syllabus.description}</p>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4 text-center">
                    <p className="text-3xl font-bold text-primary-600 dark:text-primary-400">{syllabus.units?.length || 0}</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">Units</p>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4 text-center">
                    <p className="text-3xl font-bold text-secondary-600 dark:text-secondary-400">{totalTopics}</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">Topics</p>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4 text-center">
                    <p className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">{syllabus.estimatedHours}h</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">Est. Hours</p>
                  </div>
                </div>

                {syllabus.units && syllabus.units.length > 0 && (
                  <div>
                    <h3 className="font-semibold text-slate-800 dark:text-slate-100 mb-3">Unit Summary</h3>
                    <div className="space-y-2">
                      {syllabus.units.map((unit: UnitOut) => (
                        <Link
                          key={unit.unitNumber}
                          to={`/syllabus/${syllabus.id}#unit-${unit.unitNumber}`}
                          className="block p-3 bg-slate-50 dark:bg-slate-700/50 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <span className="w-8 h-8 rounded-lg bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 text-sm font-bold flex items-center justify-center">
                              U{unit.unitNumber}
                            </span>
                            <div className="flex-1">
                              <p className="font-medium text-slate-800 dark:text-slate-100">{unit.title}</p>
                              <p className="text-xs text-slate-500 dark:text-slate-400">
                                {unit.topics?.length || 0} topics • {unit.estimatedHours}h
                              </p>
                            </div>
                            <ChevronRight className="w-4 h-4 text-slate-400" />
                          </div>
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "units" && (
              <div className="space-y-6">
                {syllabus.units && syllabus.units.length > 0 ? (
                  syllabus.units.map((unit: UnitOut) => (
                    <div key={unit.unitNumber} id={`unit-${unit.unitNumber}`} className="space-y-4">
                      <div className="flex items-center gap-3 p-4 bg-primary-50 dark:bg-primary-900/20 rounded-xl border border-primary-100 dark:border-primary-900/30">
                        <span className="w-10 h-10 rounded-xl bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 text-lg font-bold flex items-center justify-center">
                          U{unit.unitNumber}
                        </span>
                        <div>
                          <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">{unit.title}</h3>
                          {unit.description && (
                            <p className="text-sm text-slate-600 dark:text-slate-400 mt-0.5">{unit.description}</p>
                          )}
                        </div>
                        <div className="flex-1" />
                        <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
                          <span className="flex items-center gap-1.5">
                            <Target className="w-4 h-4" />
                            {unit.topics?.length || 0} topics
                          </span>
                          <span className="flex items-center gap-1.5">
                            <Clock className="w-4 h-4" />
                            {unit.estimatedHours}h
                          </span>
                        </div>
                      </div>

                      {unit.topics && unit.topics.length > 0 && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {unit.topics.map((topic: string, idx: number) => (
                            <div
                              key={idx}
                              className="flex items-center gap-2 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg border border-slate-200 dark:border-slate-600"
                            >
                              <span className="w-6 h-6 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-xs font-bold flex items-center justify-center flex-shrink-0">
                                {idx + 1}
                              </span>
                              <span className="text-sm text-slate-700 dark:text-slate-200">{topic}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="text-center py-12">
                    <BookOpen className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
                    <p className="text-slate-500 dark:text-slate-400">No units available for this syllabus</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 justify-end">
          <Link to="/search" className="btn-ghost">
            Back to Search
          </Link>
          <Link to="/ai-tutor" className="btn-primary">
            Study with AI Tutor
          </Link>
        </div>
      </div>
    </AppLayout>
  );
}