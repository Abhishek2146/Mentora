import { useState, useCallback } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { Upload, FileText, CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { syllabusService } from "@/services/syllabusService";

export default function UploadSyllabus() {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  }, []);

  const upload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const res = await syllabusService.uploadSyllabus(file, file.name);
      setResult(res);
    } catch (e: any) {
      const msg =
        e?.response?.data?.detail ||
        "Upload failed. Please try again.";
      setError(msg);
    } finally {
      setUploading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  const handleRetry = () => {
    setFile(null);
    setError(null);
    setResult(null);
  };

  return (
    <AppLayout title="Upload Syllabus">
      <div className="max-w-2xl mx-auto space-y-6">
        <div
          onDrop={onDrop}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          className={`card p-12 flex flex-col items-center gap-4 border-2 border-dashed transition-all cursor-pointer ${
            dragging ? "border-primary-400 bg-primary-50 dark:bg-primary-900/20" : "border-slate-300 dark:border-slate-600 hover:border-primary-300"
          }`}
          onClick={() => document.getElementById("file-input")?.click()}
        >
          <div className="w-16 h-16 rounded-2xl bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center">
            <Upload className="w-8 h-8 text-primary-500" />
          </div>
          <div className="text-center">
            <p className="font-bold text-slate-700 dark:text-slate-200">Drop your syllabus here</p>
            <p className="text-sm text-slate-400 mt-1">PDF, DOCX, PNG, JPG supported</p>
          </div>
          {file && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300">
              <FileText className="w-4 h-4" />
              <span className="text-sm font-medium">{file.name}</span>
            </div>
          )}
          <input
            id="file-input"
            type="file"
            className="hidden"
            accept=".pdf,.docx,.png,.jpg,.jpeg"
            onChange={handleFileChange}
          />
        </div>

        {file && !result && !error && (
          <button onClick={upload} disabled={uploading} className="btn-primary btn-lg w-full">
            {uploading ? <><Loader2 className="w-5 h-5 animate-spin" /> Analyzing…</> : <>Analyze Syllabus</>}
          </button>
        )}

        {error && (
          <div className="card p-6 space-y-4">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-6 h-6 text-red-500" />
              <h3 className="font-bold text-slate-800 dark:text-slate-100">Upload Failed</h3>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-300">{error}</p>
            <button onClick={handleRetry} className="btn-ghost btn-sm">
              Try Again
            </button>
          </div>
        )}

        {result && (
          <div className="card p-6 space-y-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-6 h-6 text-emerald-500" />
              <h3 className="font-bold text-slate-800 dark:text-slate-100">{result.subject}</h3>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-3 text-center">
                <p className="text-xl font-bold text-primary-600">{result.units?.length}</p>
                <p className="text-xs text-slate-500">Units</p>
              </div>
              <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-3 text-center">
                <p className="text-xl font-bold text-secondary-600">{result.totalTopics}</p>
                <p className="text-xs text-slate-500">Topics</p>
              </div>
              <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-3 text-center">
                <p className="text-xl font-bold text-emerald-600">{result.estimatedHours}h</p>
                <p className="text-xs text-slate-500">Est. Hours</p>
              </div>
            </div>
            <div className="space-y-2">
              {result.units?.map((u: any) => (
                <div key={u.unitNumber} className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-xl">
                  <span className="w-7 h-7 rounded-lg bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 text-xs font-bold flex items-center justify-center">U{u.unitNumber}</span>
                  <span className="flex-1 text-sm font-medium text-slate-700 dark:text-slate-200">{u.title}</span>
                  <span className="text-xs text-slate-400">{u.estimatedHours}h</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
