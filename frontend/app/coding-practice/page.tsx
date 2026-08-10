import DashboardLayout from "@/components/layout/DashboardLayout";
import apiClient from "@/lib/api";
import { useEffect, useState } from "react";
import { CodingProblem } from "@/types";

export default function CodingPracticePage() {
  const [problems, setProblems] = useState<CodingProblem[]>([]);
  const [selectedProblem, setSelectedProblem] = useState<CodingProblem | null>(null);
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("python");
  const [submissionResult, setSubmissionResult] = useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchProblems();
  }, []);

  const fetchProblems = async () => {
    try {
      const response = await apiClient.get("/api/v1/coding/problems");
      setProblems(response.data);
      if (response.data.length > 0) {
        setSelectedProblem(response.data[0]);
      }
    } catch (error) {
      console.error("Failed to fetch problems:", error);
    }
  };

  const handleCodeSubmit = async () => {
    if (!selectedProblem || !code.trim()) return;

    setIsSubmitting(true);
    try {
      const response = await apiClient.post(
        `/api/v1/coding/submissions/${selectedProblem.id}`,
        { code, language }
      );
      setSubmissionResult(response.data);
    } catch (error: any) {
      setSubmissionResult({ status: "error", output: error.response?.data?.detail || "Error", passed: false });
    } finally {
      setIsSubmitting(false);
    }
  };

  const languages = [
    { value: "python", label: "Python" },
    { value: "javascript", label: "JavaScript" },
    { value: "java", label: "Java" },
    { value: "cpp", label: "C++" },
    { value: "c", label: "C" },
    { value: "go", label: "Go" },
    { value: "rust", label: "Rust" },
  ];

  if (!selectedProblem) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <h1 className="text-3xl font-bold text-gray-900">Coding Practice</h1>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {problems.map((problem) => (
              <div
                key={problem.id}
                className="bg-white rounded-lg shadow p-6 cursor-pointer hover:shadow-md"
                onClick={() => setSelectedProblem(problem)}
              >
                <h3 className="font-bold text-lg text-gray-900">{problem.title}</h3>
                <p className="text-gray-600 mt-2 text-sm line-clamp-3">
                  {problem.description}
                </p>
                <span
                  className={`text-xs px-2 py-1 rounded-full mt-2 inline-block ${
                    problem.difficulty === "easy"
                      ? "bg-green-100 text-green-800"
                      : problem.difficulty === "medium"
                      ? "bg-yellow-100 text-yellow-800"
                      : "bg-red-100 text-red-800"
                  }`}
                >
                  {problem.difficulty}
                </span>
              </div>
            ))}
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-200px)]">
        <div className="lg:col-span-1 space-y-4 overflow-y-auto">
          <button
            onClick={() => setSelectedProblem(null)}
            className="text-primary-600 hover:text-primary-700"
          >
            ← Back to Problems
          </button>
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900">{selectedProblem.title}</h2>
            <span
              className={`text-xs px-2 py-1 rounded-full mt-2 inline-block ${
                selectedProblem.difficulty === "easy"
                  ? "bg-green-100 text-green-800"
                  : selectedProblem.difficulty === "medium"
                  ? "bg-yellow-100 text-yellow-800"
                  : "bg-red-100 text-red-800"
              }`}
            >
              {selectedProblem.difficulty}
            </span>
            <p className="text-gray-600 mt-3 text-sm whitespace-pre-line">
              {selectedProblem.description}
            </p>
            {selectedProblem.starter_code && (
              <>
                <h3 className="font-semibold mt-3 mb-1">Starter Code:</h3>
                <pre className="bg-gray-900 text-gray-100 p-3 rounded-md text-xs overflow-x-auto">
                  {selectedProblem.starter_code}
                </pre>
              </>
            )}
          </div>

          {submissionResult && (
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-semibold mb-2">Result</h3>
              <p className={`text-sm ${submissionResult.passed ? "text-green-600" : "text-red-600"}`}>
                Status: {submissionResult.status} {submissionResult.passed ? "✓" : "✗"}
              </p>
              {submissionResult.output && (
                <pre className="bg-gray-100 p-2 rounded text-xs mt-2 overflow-x-auto">
                  {submissionResult.output}
                </pre>
              )}
            </div>
          )}
        </div>

        <div className="lg:col-span-2 flex flex-col">
          <div className="mb-2">
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm"
            >
              {languages.map((lang) => (
                <option key={lang.value} value={lang.value}>
                  {lang.label}
                </option>
              ))}
            </select>
          </div>

          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder={selectedProblem.starter_code || "// Write your code here..."}
            className="flex-1 w-full p-4 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-primary-500 resize-none"
          />

          <button
            onClick={handleCodeSubmit}
            disabled={isSubmitting || !code.trim()}
            className="mt-2 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
          >
            {isSubmitting ? "Running..." : "Run Code"}
          </button>
        </div>
      </div>
    </DashboardLayout>
  );
}
