import { useState, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { Network, Plus, Loader2, FileText, Download, Target, Trash2 } from "lucide-react";
import { mindmapService, MindMap } from "@/services/mindmapService";
import { syllabusService, Syllabus } from "@/services/syllabusService";
import { notesService, Note } from "@/services/notesService";
import MindMapCanvas from "@/components/MindMapCanvas";

export default function MindMapPage() {
  const [mindmaps, setMindmaps] = useState<MindMap[]>([]);
  const [syllabi, setSyllabi] = useState<Syllabus[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedMindMap, setSelectedMindMap] = useState<MindMap | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Generate Modal state
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [genSourceType, setGenSourceType] = useState<"syllabus" | "note">("syllabus");
  const [genSourceId, setGenSourceId] = useState<number | "">("");
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [mmData, sylData, nData] = await Promise.all([
        mindmapService.getMindMaps(),
        syllabusService.getAllSyllabi().catch(() => []),
        notesService.getNotes().catch(() => []),
      ]);
      setMindmaps(mmData);
      setSyllabi(sylData);
      setNotes(nData);
      if (mmData.length > 0) {
        setSelectedMindMap(mmData[0]);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load mind maps.");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerate() {
    if (!genSourceId) {
      setGenError("Please select a source document.");
      return;
    }
    setGenerating(true);
    setGenError(null);
    try {
      const created = await mindmapService.generateMindMap(genSourceType, Number(genSourceId));
      
      // Update list
      setMindmaps((prev) => {
        const existing = prev.findIndex(m => m.id === created.id);
        if (existing >= 0) {
          const updated = [...prev];
          updated[existing] = created;
          return updated;
        }
        return [created, ...prev];
      });
      setSelectedMindMap(created);
      setShowGenerateModal(false);
      setGenSourceId("");
    } catch (e: any) {
      setGenError(e?.response?.data?.detail || "Failed to generate mind map.");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <AppLayout title="AI Mind Map">
      <div className="h-[calc(100vh-6rem)] flex flex-col space-y-4 max-w-7xl mx-auto">
        {/* Header action bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-800 card p-4 border border-slate-200 dark:border-slate-700">
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Network className="w-5 h-5 text-primary-500" /> AI Mind Map
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Visualize your learning material and understand how topics are connected.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => { setGenError(null); setShowGenerateModal(true); }}
              className="btn-primary btn-sm bg-gradient-to-r from-secondary-600 to-primary-600 hover:from-secondary-700 hover:to-primary-700 border-0"
            >
              <Network className="w-4 h-4" /> Generate Mind Map
            </button>
          </div>
        </div>

        {error && (
          <p className="text-xs text-danger-600 dark:text-danger-400 bg-danger-50 p-2 rounded">{error}</p>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 lg:gap-6 flex-1 min-h-0">
          {/* Sidebar */}
          <div className="lg:col-span-1 flex flex-col space-y-3 h-full overflow-hidden">
            <h3 className="font-semibold text-slate-800 dark:text-slate-200">Your Mind Maps</h3>
            
            {loading ? (
              <div className="card p-8 flex items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
              </div>
            ) : mindmaps.length === 0 ? (
              <div className="card p-6 text-center space-y-3 flex-1 flex flex-col items-center justify-center">
                <Network className="w-10 h-10 mx-auto text-slate-300" />
                <p className="text-sm text-slate-500">No mind maps yet.</p>
                <button
                  onClick={() => { setGenError(null); setShowGenerateModal(true); }}
                  className="btn-primary btn-sm mx-auto"
                >
                  Create Your First Map
                </button>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto pr-1 space-y-2">
                {mindmaps.map((mm) => (
                  <div
                    key={mm.id}
                    onClick={() => setSelectedMindMap(mm)}
                    className={`card p-3 cursor-pointer transition-all border ${
                      selectedMindMap?.id === mm.id
                        ? "border-primary-500 bg-primary-50/60 dark:bg-primary-900/20 shadow-sm"
                        : "hover:border-slate-300 dark:hover:border-slate-600"
                    }`}
                  >
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 line-clamp-2">
                      {mm.title}
                    </p>
                    <span className="inline-block text-[10px] font-medium px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 mt-1 uppercase">
                      {mm.source_type}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Canvas Area */}
          <div className="lg:col-span-3 card flex flex-col overflow-hidden relative min-h-[500px]">
            {selectedMindMap ? (
              <MindMapCanvas mindMapData={selectedMindMap} />
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-400 p-8 text-center space-y-4">
                <Target className="w-16 h-16 opacity-20" />
                <div>
                  <p className="text-lg font-medium text-slate-500 dark:text-slate-400">Select a Mind Map</p>
                  <p className="text-sm mt-1">Choose a map from the sidebar or generate a new one.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Generate Modal */}
      {showGenerateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-md overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">
            <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700/60 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/50">
              <h3 className="font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                <Network className="w-4 h-4 text-primary-500" />
                Generate AI Mind Map
              </h3>
              <button
                onClick={() => !generating && setShowGenerateModal(false)}
                className="text-slate-400 hover:text-slate-600 transition-colors"
                disabled={generating}
              >
                <Plus className="w-5 h-5 rotate-45" />
              </button>
            </div>
            
            <div className="p-5 space-y-4">
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Mentora AI will analyze your learning material and create a structured knowledge graph.
              </p>
              
              {genError && (
                <div className="p-3 bg-danger-50 dark:bg-danger-900/20 text-danger-600 dark:text-danger-400 text-xs rounded-lg border border-danger-100 dark:border-danger-800">
                  {genError}
                </div>
              )}
              
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 uppercase tracking-wider">
                  Source Type
                </label>
                <select
                  value={genSourceType}
                  onChange={(e) => {
                    setGenSourceType(e.target.value as "syllabus" | "note");
                    setGenSourceId("");
                  }}
                  className="input w-full bg-slate-50"
                  disabled={generating}
                >
                  <option value="syllabus">Uploaded Syllabus / Course</option>
                  <option value="note">Study Note</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 uppercase tracking-wider">
                  Select Document
                </label>
                <select
                  value={genSourceId}
                  onChange={(e) => setGenSourceId(Number(e.target.value))}
                  className="input w-full bg-slate-50"
                  disabled={generating}
                >
                  <option value="">-- Choose {genSourceType} --</option>
                  {genSourceType === "syllabus" ? (
                    syllabi.map(s => <option key={s.id} value={s.id}>{s.title}</option>)
                  ) : (
                    notes.map(n => <option key={n.id} value={n.id}>{n.title}</option>)
                  )}
                </select>
              </div>
            </div>
            
            <div className="px-5 py-4 border-t border-slate-100 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/50 flex justify-end gap-2">
              <button
                onClick={() => setShowGenerateModal(false)}
                className="btn-ghost btn-sm"
                disabled={generating}
              >
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={generating || !genSourceId}
                className="btn-primary btn-sm bg-gradient-to-r from-secondary-600 to-primary-600 hover:from-secondary-700 hover:to-primary-700 border-0 shadow-md"
              >
                {generating ? (
                  <><Loader2 className="w-4 h-4 animate-spin mr-1.5" /> Processing...</>
                ) : (
                  <><Network className="w-4 h-4 mr-1.5" /> Generate Map</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
