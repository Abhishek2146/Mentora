import { useState, useEffect, useRef } from "react";
import AppLayout from "@/components/layout/AppLayout";
import {
  FileText,
  Plus,
  Trash2,
  Pencil,
  Save,
  X,
  Sparkles,
  Loader2,
  BookOpen,
  Download,
  Search,
  Printer,
  FileCode,
  GraduationCap,
  CheckCircle2,
} from "lucide-react";
import { notesService, Note } from "@/services/notesService";
import { syllabusService, Syllabus } from "@/services/syllabusService";

// ------------------------------------------------------------------ Markdown Stripper

export function stripMarkdown(text: string | null | undefined): string {
  if (!text) return "";
  let clean = text;
  clean = clean.replace(/```[a-zA-Z]*\n?([\s\S]*?)\n?```/g, "$1");
  clean = clean.replace(/`([^`]+)`/g, "$1");
  clean = clean.replace(/^#{1,6}\s+/gm, "");
  clean = clean.replace(/\*\*([^*]+)\*\*/g, "$1");
  clean = clean.replace(/\*([^*]+)\*/g, "$1");
  clean = clean.replace(/__([^_]+)__/g, "$1");
  clean = clean.replace(/_([^_]+)_/g, "$1");
  clean = clean.replace(/^\s*[-*]\s+/gm, "• ");
  clean = clean.replace(/^\s*>\s+/gm, "");
  return clean.trim();
}

// ------------------------------------------------------------------ AI Summary section

interface SummarySectionProps {
  note: Note;
  onSummaryChange: (summary: string | null) => void;
}

function SummarySection({ note, onSummaryChange }: SummarySectionProps) {
  const [generating, setGenerating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editText, setEditText] = useState(note.ai_summary || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Keep edit text in sync when note changes
  useEffect(() => {
    setEditText(note.ai_summary || "");
    setEditMode(false);
    setError(null);
  }, [note.id, note.ai_summary]);

  async function handleGenerate() {
    if (!note.content?.trim()) {
      setError("Note content is empty. Add some content before generating a summary.");
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const result = await notesService.generateSummary(note.id);
      onSummaryChange(result.ai_summary);
      setEditText(result.ai_summary);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      setError(
        typeof detail === "string" && detail
          ? detail
          : e?.message || "Failed to generate summary. Please try again."
      );
    } finally {
      setGenerating(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await notesService.deleteSummary(note.id);
      onSummaryChange(null);
      setEditText("");
      setEditMode(false);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to delete summary.");
    } finally {
      setDeleting(false);
    }
  }

  async function handleSaveEdit() {
    if (!editText.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await notesService.updateNote(note.id, {
        ai_summary: editText.trim(),
      });
      onSummaryChange(updated.ai_summary);
      setEditMode(false);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to save edited summary.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-secondary-100 dark:bg-secondary-900/40 text-secondary-600 dark:text-secondary-300">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">
              AI Study Summary
            </h3>
            <p className="text-xs text-slate-500">Key takeaways & core concepts</p>
          </div>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating || !note.content?.trim()}
          title={!note.content?.trim() ? "Add note content first" : "Generate AI summary"}
          className="btn-primary btn-sm bg-gradient-to-r from-secondary-600 to-primary-600 hover:from-secondary-700 hover:to-primary-700 border-0"
        >
          {generating ? (
            <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Summarizing…</>
          ) : (
            <><Sparkles className="w-3.5 h-3.5" /> {note.ai_summary ? "Regenerate" : "Generate Summary"}</>
          )}
        </button>
      </div>

      {error && (
        <p className="text-xs text-danger-600 dark:text-danger-400 bg-danger-50 dark:bg-danger-900/20 p-2 rounded-lg">{error}</p>
      )}

      {!note.ai_summary && !generating && (
        <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 p-6 text-sm text-slate-400 text-center space-y-2">
          <Sparkles className="w-8 h-8 mx-auto text-secondary-400 opacity-60" />
          <p>No summary generated yet.</p>
          <p className="text-xs text-slate-400">Click "Generate Summary" to condense this note into key study points.</p>
        </div>
      )}

      {note.ai_summary && !editMode && (
        <div className="rounded-xl bg-gradient-to-br from-secondary-50 to-primary-50/30 dark:from-secondary-900/20 dark:to-primary-900/10 border border-secondary-200/80 dark:border-secondary-800/50 p-4 space-y-3">
          <pre className="whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-200 font-sans leading-relaxed">
            {stripMarkdown(note.ai_summary)}
          </pre>
          <div className="flex items-center justify-between pt-2 border-t border-secondary-200/60 dark:border-secondary-800/40">
            <span className="text-[11px] text-slate-400">
              {note.summary_generated_at ? `Updated ${new Date(note.summary_generated_at).toLocaleDateString()}` : "AI Generated"}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => { setEditText(note.ai_summary || ""); setEditMode(true); }}
                className="btn-ghost btn-sm text-xs"
              >
                <Pencil className="w-3.5 h-3.5" /> Edit
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="btn-ghost btn-sm text-xs text-danger-500 hover:text-danger-700"
              >
                {deleting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5" />
                )}
                Clear
              </button>
            </div>
          </div>
        </div>
      )}

      {editMode && (
        <div className="space-y-2">
          <textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            rows={6}
            className="input font-sans resize-none w-full"
            placeholder="Edit summary bullet points…"
          />
          <div className="flex gap-2 justify-end">
            <button
              onClick={handleSaveEdit}
              disabled={saving || !editText.trim()}
              className="btn-primary btn-sm"
            >
              {saving ? (
                <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Saving…</>
              ) : (
                <><Save className="w-3.5 h-3.5" /> Save Summary</>
              )}
            </button>
            <button
              onClick={() => { setEditMode(false); setEditText(note.ai_summary || ""); }}
              className="btn-ghost btn-sm"
            >
              <X className="w-3.5 h-3.5" /> Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ Main page

export default function Notes() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [syllabi, setSyllabi] = useState<Syllabus[]>([]);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Create / Edit manual note state
  const [showForm, setShowForm] = useState(false);
  const [formTitle, setFormTitle] = useState("");
  const [formContent, setFormContent] = useState("");
  const [formSyllabusId, setFormSyllabusId] = useState<number | "">("");
  const [formError, setFormError] = useState<string | null>(null);
  const [formSaving, setFormSaving] = useState(false);
  const [editingNote, setEditingNote] = useState<Note | null>(null);

  // Generate Notes from Syllabus Modal state
  const [showSyllabusModal, setShowSyllabusModal] = useState(false);
  const [genSyllabusId, setGenSyllabusId] = useState<number | "">("");
  const [genTopicFocus, setGenTopicFocus] = useState("");
  const [genGenerating, setGenGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  // Inline note content editing
  const [editingContent, setEditingContent] = useState(false);
  const [contentDraft, setContentDraft] = useState("");
  const [contentSaving, setContentSaving] = useState(false);
  const contentRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [notesData, syllabiData] = await Promise.all([
        notesService.getNotes(),
        syllabusService.getAllSyllabi().catch(() => []),
      ]);
      setNotes(notesData);
      setSyllabi(syllabiData);
      if (notesData.length > 0 && !selectedNote) {
        setSelectedNote(notesData[0]);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load data.");
    } finally {
      setLoading(false);
    }
  }

  function openCreate() {
    setEditingNote(null);
    setFormTitle("");
    setFormContent("");
    setFormSyllabusId("");
    setFormError(null);
    setShowForm(true);
  }

  function openEdit(note: Note) {
    setEditingNote(note);
    setFormTitle(note.title);
    setFormContent(note.content);
    setFormSyllabusId(note.syllabus_id || "");
    setFormError(null);
    setShowForm(true);
  }

  async function handleFormSubmit() {
    if (!formTitle.trim()) {
      setFormError("Title is required.");
      return;
    }
    setFormSaving(true);
    setFormError(null);
    try {
      if (editingNote) {
        const updated = await notesService.updateNote(editingNote.id, {
          title: formTitle.trim(),
          content: formContent,
          syllabus_id: Number(formSyllabusId) || null,
        });
        setNotes((prev) => prev.map((n) => (n.id === updated.id ? updated : n)));
        if (selectedNote?.id === updated.id) setSelectedNote(updated);
      } else {
        const created = await notesService.createNote({
          title: formTitle.trim(),
          content: formContent,
          syllabus_id: Number(formSyllabusId) || null,
        });
        setNotes((prev) => [created, ...prev]);
        setSelectedNote(created);
      }
      setShowForm(false);
      setEditingNote(null);
    } catch (e: any) {
      setFormError(e?.response?.data?.detail || "Failed to save note.");
    } finally {
      setFormSaving(false);
    }
  }

  async function handleGenerateFromSyllabus() {
    if (!genSyllabusId) {
      setGenError("Please select a syllabus.");
      return;
    }
    setGenGenerating(true);
    setGenError(null);
    try {
      const created = await notesService.generateFromSyllabus(
        Number(genSyllabusId),
        genTopicFocus.trim() || undefined
      );
      setNotes((prev) => [created, ...prev]);
      setSelectedNote(created);
      setShowSyllabusModal(false);
      setGenTopicFocus("");
      setGenSyllabusId("");
    } catch (e: any) {
      setGenError(e?.response?.data?.detail || "Failed to generate AI notes.");
    } finally {
      setGenGenerating(false);
    }
  }

  async function handleDelete(noteId: number) {
    if (!confirm("Are you sure you want to delete this note?")) return;
    try {
      await notesService.deleteNote(noteId);
      const remaining = notes.filter((n) => n.id !== noteId);
      setNotes(remaining);
      if (selectedNote?.id === noteId) {
        setSelectedNote(remaining.length > 0 ? remaining[0] : null);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to delete note.");
    }
  }

  async function handleSaveContent() {
    if (!selectedNote) return;
    setContentSaving(true);
    try {
      const updated = await notesService.updateNote(selectedNote.id, {
        content: contentDraft,
      });
      setSelectedNote(updated);
      setNotes((prev) => prev.map((n) => (n.id === updated.id ? updated : n)));
      setEditingContent(false);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to save content.");
    } finally {
      setContentSaving(false);
    }
  }

  function handleSummaryChange(summary: string | null) {
    if (!selectedNote) return;
    const updated = { ...selectedNote, ai_summary: summary };
    setSelectedNote(updated);
    setNotes((prev) => prev.map((n) => (n.id === updated.id ? updated : n)));
  }

  function handleExportPDF(note: Note) {
    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      alert("Please allow popups to export PDF.");
      return;
    }

    const syllabusName = syllabi.find((s) => s.id === note.syllabus_id)?.title || "General";
    const dateStr = note.created_at ? new Date(note.created_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }) : new Date().toLocaleDateString();

    const htmlContent = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>${note.title} - Mentora Study Notes</title>
          <style>
            body {
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
              color: #1e293b;
              margin: 40px;
              line-height: 1.6;
            }
            .header {
              border-bottom: 2px solid #6366f1;
              padding-bottom: 16px;
              margin-bottom: 24px;
              display: flex;
              justify-content: space-between;
              align-items: flex-end;
            }
            .brand {
              font-size: 24px;
              font-weight: 800;
              color: #4f46e5;
            }
            .meta {
              font-size: 12px;
              color: #64748b;
              text-align: right;
            }
            .title {
              font-size: 22px;
              font-weight: 700;
              color: #0f172a;
              margin-bottom: 8px;
            }
            .tag {
              display: inline-block;
              background-color: #e0e7ff;
              color: #3730a3;
              font-size: 11px;
              font-weight: 600;
              padding: 3px 8px;
              border-radius: 4px;
              margin-bottom: 20px;
            }
            .summary-box {
              background-color: #f5f3ff;
              border: 1px solid #ddd6fe;
              border-radius: 8px;
              padding: 16px;
              margin-bottom: 24px;
            }
            .summary-title {
              font-size: 13px;
              font-weight: 700;
              color: #6d28d9;
              margin-bottom: 8px;
              text-transform: uppercase;
              letter-spacing: 0.5px;
            }
            .summary-content {
              font-size: 13px;
              color: #4c1d95;
              white-space: pre-wrap;
            }
            .content {
              font-size: 14px;
              white-space: pre-wrap;
              color: #334155;
            }
            @media print {
              body { margin: 20px; }
            }
          </style>
        </head>
        <body>
          <div class="header">
            <div>
              <div class="brand">Mentora</div>
              <div style="font-size: 12px; color: #64748b;">AI Academic Study Notes</div>
            </div>
            <div class="meta">
              <div><strong>Course/Syllabus:</strong> ${syllabusName}</div>
              <div><strong>Date:</strong> ${dateStr}</div>
            </div>
          </div>

          <div class="title">${note.title}</div>
          <div class="tag">Syllabus: ${syllabusName}</div>

          ${note.ai_summary ? `
            <div class="summary-box">
              <div class="summary-title">★ AI Study Summary</div>
              <div class="summary-content">${stripMarkdown(note.ai_summary)}</div>
            </div>
          ` : ""}

          <div class="content">${stripMarkdown(note.content) || "No content."}</div>

          <script>
            window.onload = function() {
              window.print();
            };
          </script>
        </body>
      </html>
    `;

    printWindow.document.write(htmlContent);
    printWindow.document.close();
  }

  const filteredNotes = notes.filter((n) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return n.title.toLowerCase().includes(q) || (n.content && n.content.toLowerCase().includes(q));
  });

  return (
    <AppLayout title="Notes & Summaries">
      <div className="max-w-6xl mx-auto space-y-4">

        {/* Header action bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-800 card p-4 border border-slate-200 dark:border-slate-700">
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary-500" /> Study Notes & AI Summaries
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Generate comprehensive notes from uploaded syllabi, summarize key concepts, and export to PDF.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => { setGenError(null); setShowSyllabusModal(true); }}
              className="btn-primary btn-sm bg-gradient-to-r from-secondary-600 to-primary-600 hover:from-secondary-700 hover:to-primary-700 border-0"
            >
              <Sparkles className="w-4 h-4" /> Generate Notes from Syllabus
            </button>
            <button onClick={openCreate} className="btn-secondary btn-sm">
              <Plus className="w-4 h-4" /> New Blank Note
            </button>
          </div>
        </div>

        {loading ? (
          <div className="card p-12 flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
            <span className="ml-3 text-slate-500">Loading notes…</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6">

            {/* ---- Sidebar: note list ---- */}
            <div className="lg:col-span-1 space-y-3">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search notes…"
                  className="input pl-9 text-xs"
                />
              </div>

              {error && (
                <p className="text-xs text-danger-600 dark:text-danger-400 bg-danger-50 p-2 rounded">{error}</p>
              )}

              {filteredNotes.length === 0 ? (
                <div className="card p-8 text-center space-y-3">
                  <BookOpen className="w-10 h-10 mx-auto text-slate-300" />
                  <p className="text-sm text-slate-500">
                    {searchQuery ? "No matching notes found." : "No notes yet."}
                  </p>
                  <button
                    onClick={() => { setGenError(null); setShowSyllabusModal(true); }}
                    className="btn-primary btn-sm mx-auto"
                  >
                    <Sparkles className="w-4 h-4" /> Generate from Syllabus
                  </button>
                </div>
              ) : (
                <div className="space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
                  {filteredNotes.map((note) => {
                    const matchedSyllabus = syllabi.find((s) => s.id === note.syllabus_id);
                    return (
                      <div
                        key={note.id}
                        onClick={() => {
                          setSelectedNote(note);
                          setEditingContent(false);
                          setError(null);
                        }}
                        className={`card p-3.5 cursor-pointer transition-all border ${
                          selectedNote?.id === note.id
                            ? "border-primary-500 bg-primary-50/60 dark:bg-primary-900/20 shadow-sm"
                            : "hover:border-slate-300 dark:hover:border-slate-600"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
                              {note.title}
                            </p>
                            {matchedSyllabus && (
                              <span className="inline-block text-[10px] font-medium px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 mt-1">
                                {matchedSyllabus.title}
                              </span>
                            )}
                            {note.content && (
                              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                                {note.content}
                              </p>
                            )}
                          </div>
                          <div className="flex flex-col items-end gap-1 flex-shrink-0">
                            {note.ai_summary && (
                              <span className="p-1 rounded bg-secondary-100 dark:bg-secondary-900/30 text-secondary-600" title="Has AI summary">
                                <Sparkles className="w-3.5 h-3.5" />
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* ---- Main content area ---- */}
            <div className="lg:col-span-2 space-y-4">

              {/* Manual Note Create/Edit Form */}
              {showForm ? (
                <div className="card p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-slate-800 dark:text-slate-100">
                      {editingNote ? "Edit Note Details" : "Create New Note"}
                    </h3>
                    <button onClick={() => { setShowForm(false); setFormError(null); }} className="btn-ghost btn-sm">
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  {formError && (
                    <p className="text-xs text-danger-600 bg-danger-50 p-2 rounded">{formError}</p>
                  )}

                  <div>
                    <label className="block text-xs font-medium text-slate-500 mb-1">Note Title *</label>
                    <input
                      type="text"
                      value={formTitle}
                      onChange={(e) => { setFormTitle(e.target.value); setFormError(null); }}
                      placeholder="e.g. Unit 1: Relational Model Notes"
                      className="input"
                      autoFocus
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-500 mb-1">Associated Syllabus (Optional)</label>
                    <select
                      value={formSyllabusId}
                      onChange={(e) => setFormSyllabusId(Number(e.target.value) || "")}
                      className="input"
                    >
                      <option value="">None (General Note)</option>
                      {syllabi.map((s) => (
                        <option key={s.id} value={s.id}>{s.title}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-500 mb-1">Content</label>
                    <textarea
                      value={formContent}
                      onChange={(e) => setFormContent(e.target.value)}
                      placeholder="Write your study notes here…"
                      rows={8}
                      className="input resize-none font-sans"
                    />
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={handleFormSubmit}
                      disabled={formSaving || !formTitle.trim()}
                      className="btn-primary btn-md flex-1"
                    >
                      {formSaving ? (
                        <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</>
                      ) : (
                        <><Save className="w-4 h-4" /> {editingNote ? "Update Note" : "Create Note"}</>
                      )}
                    </button>
                    <button onClick={() => { setShowForm(false); setFormError(null); }} className="btn-ghost btn-md">
                      Cancel
                    </button>
                  </div>
                </div>
              ) : selectedNote ? (
                <>
                  {/* Selected Note Header Card */}
                  <div className="card p-5 space-y-4">
                    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 dark:border-slate-700/60 pb-4">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <FileText className="w-5 h-5 text-primary-500 flex-shrink-0" />
                          <h2 className="font-bold text-lg text-slate-800 dark:text-slate-100 truncate">
                            {selectedNote.title}
                          </h2>
                        </div>
                        {selectedNote.syllabus_id && (
                          <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                            <GraduationCap className="w-3.5 h-3.5 text-primary-500" />
                            Syllabus: {syllabi.find((s) => s.id === selectedNote.syllabus_id)?.title || "Attached"}
                          </p>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => handleExportPDF(selectedNote)}
                          className="btn-secondary btn-sm text-xs"
                          title="Export note as formatted PDF"
                        >
                          <Printer className="w-3.5 h-3.5" /> Export PDF
                        </button>
                        <button
                          onClick={() => openEdit(selectedNote)}
                          className="btn-ghost btn-sm text-xs"
                          title="Edit note title and linkage"
                        >
                          <Pencil className="w-3.5 h-3.5" /> Edit
                        </button>
                        <button
                          onClick={() => handleDelete(selectedNote.id)}
                          className="btn-ghost btn-sm text-xs text-danger-500 hover:text-danger-700"
                          title="Delete note"
                        >
                          <Trash2 className="w-3.5 h-3.5" /> Delete
                        </button>
                      </div>
                    </div>

                    {/* Note Content Area */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          Note Content
                        </span>
                        {!editingContent && (
                          <button
                            onClick={() => {
                              setContentDraft(selectedNote.content || "");
                              setEditingContent(true);
                              setTimeout(() => contentRef.current?.focus(), 50);
                            }}
                            className="text-xs text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1"
                          >
                            <Pencil className="w-3 h-3" /> Edit content
                          </button>
                        )}
                      </div>

                      {editingContent ? (
                        <div className="space-y-2">
                          <textarea
                            ref={contentRef}
                            value={contentDraft}
                            onChange={(e) => setContentDraft(e.target.value)}
                            rows={12}
                            className="input resize-none font-sans w-full leading-relaxed"
                            autoFocus
                          />
                          <div className="flex gap-2 justify-end">
                            <button
                              onClick={handleSaveContent}
                              disabled={contentSaving}
                              className="btn-primary btn-sm"
                            >
                              {contentSaving ? (
                                <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Saving…</>
                              ) : (
                                <><Save className="w-3.5 h-3.5" /> Save Content</>
                              )}
                            </button>
                            <button
                              onClick={() => setEditingContent(false)}
                              className="btn-ghost btn-sm"
                            >
                              <X className="w-3.5 h-3.5" /> Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div
                          onClick={() => {
                            setContentDraft(selectedNote.content || "");
                            setEditingContent(true);
                            setTimeout(() => contentRef.current?.focus(), 50);
                          }}
                          className={`min-h-[140px] rounded-xl p-4 cursor-text border transition ${
                            selectedNote.content
                              ? "bg-slate-50/50 dark:bg-slate-900/30 border-slate-200/60 dark:border-slate-700/60 hover:border-primary-300"
                              : "border-dashed border-slate-300 dark:border-slate-700 text-slate-400"
                          }`}
                        >
                          {selectedNote.content ? (
                            <pre className="whitespace-pre-wrap text-sm font-sans text-slate-700 dark:text-slate-200 leading-relaxed">
                              {stripMarkdown(selectedNote.content)}
                            </pre>
                          ) : (
                            <p className="text-sm text-slate-400 italic">
                              Click here to add notes content…
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* AI Summary Card */}
                  <div className="card p-5">
                    <SummarySection
                      note={selectedNote}
                      onSummaryChange={handleSummaryChange}
                    />
                  </div>
                </>
              ) : (
                <div className="card p-12 text-center space-y-4">
                  <BookOpen className="w-12 h-12 mx-auto text-slate-300" />
                  <div>
                    <p className="font-semibold text-slate-700 dark:text-slate-200">No note selected</p>
                    <p className="text-xs text-slate-400 mt-1">Select a note from the sidebar or generate one from a syllabus.</p>
                  </div>
                  <button
                    onClick={() => { setGenError(null); setShowSyllabusModal(true); }}
                    className="btn-primary btn-sm mx-auto bg-gradient-to-r from-secondary-600 to-primary-600"
                  >
                    <Sparkles className="w-4 h-4" /> Generate Notes from Syllabus
                  </button>
                </div>
              )}

            </div>
          </div>
        )}

        {/* ---- Generate from Syllabus Modal ---- */}
        {showSyllabusModal && (
          <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="card p-6 max-w-lg w-full space-y-4 shadow-xl border-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-xl bg-primary-100 text-primary-600 dark:bg-primary-900/30">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-lg text-slate-800 dark:text-slate-100">
                      Generate AI Notes from Syllabus
                    </h3>
                    <p className="text-xs text-slate-500">AI will build structured study notes & summary</p>
                  </div>
                </div>
                <button
                  onClick={() => setShowSyllabusModal(false)}
                  className="btn-ghost btn-sm"
                  disabled={genGenerating}
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {genError && (
                <p className="text-xs text-danger-600 bg-danger-50 p-2.5 rounded-lg">{genError}</p>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Select Syllabus *
                </label>
                <select
                  value={genSyllabusId}
                  onChange={(e) => setGenSyllabusId(Number(e.target.value) || "")}
                  className="input"
                  disabled={genGenerating}
                >
                  <option value="">Select an uploaded syllabus…</option>
                  {syllabi.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.title}
                    </option>
                  ))}
                </select>
                {syllabi.length === 0 && (
                  <p className="text-xs text-amber-600 mt-1">
                    No syllabi found. Please upload a syllabus first from the Upload Syllabus page.
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Topic / Unit Focus <span className="text-slate-400 font-normal">(Optional)</span>
                </label>
                <input
                  type="text"
                  value={genTopicFocus}
                  onChange={(e) => setGenTopicFocus(e.target.value)}
                  placeholder="e.g. Unit 1: Database Normalization or Leave blank for full course"
                  className="input"
                  disabled={genGenerating}
                />
              </div>

              <div className="pt-2 flex gap-3">
                <button
                  onClick={handleGenerateFromSyllabus}
                  disabled={!genSyllabusId || genGenerating}
                  className="btn-primary btn-md flex-1 bg-gradient-to-r from-secondary-600 to-primary-600 hover:from-secondary-700 hover:to-primary-700 border-0"
                >
                  {genGenerating ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> AI is generating notes & summary…</>
                  ) : (
                    <><Sparkles className="w-4 h-4" /> Generate AI Notes</>
                  )}
                </button>
                <button
                  onClick={() => setShowSyllabusModal(false)}
                  disabled={genGenerating}
                  className="btn-ghost btn-md"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </AppLayout>
  );
}
