import DashboardLayout from "@/components/layout/DashboardLayout";
import { useState, useEffect } from "react";
import { PlayIcon, PauseIcon, CheckCircleIcon, XCircleIcon } from "@heroicons/react/24/outline";

interface Question {
  id: number;
  question_text: string;
  options?: string[];
  correct_answer: string;
}

export default function ExamSimulatorPage() {
  const [isStarted, setIsStarted] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [timeLeft, setTimeLeft] = useState(3600);
  const [showResults, setShowResults] = useState(false);

  const mockQuestions: Question[] = Array.from({ length: 50 }, (_, i) => ({
    id: i + 1,
    question_text: `Sample exam question ${i + 1}. What is the primary concept being tested here?`,
    options: ["Option A", "Option B", "Option C", "Option D"],
    correct_answer: "B",
  }));

  useEffect(() => {
    if (isStarted && timeLeft > 0 && !showResults) {
      const timer = setTimeout(() => setTimeLeft(timeLeft - 1), 1000);
      return () => clearTimeout(timer);
    } else if (timeLeft === 0 && isStarted) {
      setShowResults(true);
      setIsStarted(false);
    }
  }, [isStarted, timeLeft, showResults]);

  const handleSelectAnswer = (answer: string) => {
    setSelectedAnswer(answer);
    setAnswers({ ...answers, [currentQuestion]: answer });
  };

  const handleNext = () => {
    setSelectedAnswer(null);
    setCurrentQuestion(currentQuestion + 1);
  };

  const handlePrev = () => {
    setSelectedAnswer(null);
    setCurrentQuestion(currentQuestion - 1);
  };

  const handleSubmit = () => {
    setShowResults(true);
    setIsStarted(false);
  };

  const calculateScore = () => {
    let correct = 0;
    Object.entries(answers).forEach(([qIndex, answer]) => {
      const question = mockQuestions[parseInt(qIndex)];
      if (question && question.correct_answer === answer) {
        correct++;
      }
    });
    return { correct, total: mockQuestions.length, percentage: Math.round((correct / mockQuestions.length) * 100) };
  };

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  if (!isStarted) {
    if (showResults) {
      const score = calculateScore();
      return (
        <DashboardLayout>
          <div className="max-w-3xl mx-auto text-center py-12">
            <h1 className="text-3xl font-bold text-gray-900 mb-6">Exam Results</h1>
            <div className="bg-white rounded-lg shadow p-8">
              <div className="text-6xl font-bold text-primary-600 mb-4">{score.percentage}%</div>
              <p className="text-gray-600 mb-6">
                You scored {score.correct} out of {score.total} questions correct
              </p>
              <button
                onClick={() => { setIsStarted(true); setShowResults(false); setAnswers({}); setCurrentQuestion(0); setSelectedAnswer(null); setTimeLeft(3600); }}
                className="px-6 py-3 bg-primary-600 text-white rounded-md hover:bg-primary-700"
              >
                Retake Exam
              </button>
            </div>
          </div>
        </DashboardLayout>
      );
    }

    return (
      <DashboardLayout>
        <div className="max-w-3xl mx-auto py-12">
          <h1 className="text-3xl font-bold text-gray-900 mb-6 text-center">Exam Simulator</h1>
          <div className="bg-white rounded-lg shadow p-8">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Time Limit</label>
                <select className="w-full px-3 py-2 border border-gray-300 rounded-md">
                  <option>60 minutes (3600s)</option>
                  <option>90 minutes (5400s)</option>
                  <option>120 minutes (7200s)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Number of Questions</label>
                <select className="w-full px-3 py-2 border border-gray-300 rounded-md">
                  <option>50 Questions</option>
                  <option>100 Questions</option>
                </select>
              </div>
              <button
                onClick={() => { setIsStarted(true); setTimeLeft(3600); }}
                className="w-full px-4 py-3 bg-primary-600 text-white rounded-md hover:bg-primary-700"
              >
                Start Exam
              </button>
            </div>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  const question = mockQuestions[currentQuestion];

  return (
    <DashboardLayout>
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold">Question {currentQuestion + 1} of {mockQuestions.length}</h2>
          <div className={`text-2xl font-bold ${timeLeft < 300 ? "text-red-600" : "text-gray-900"}`}>
            {formatTime(timeLeft)}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">{question.question_text}</h3>

          <div className="space-y-3">
            {question.options?.map((option, i) => {
              const optionLabel = String.fromCharCode(65 + i);
              return (
                <label
                  key={i}
                  className={`flex items-center p-3 border rounded-lg cursor-pointer transition-colors ${
                    selectedAnswer === optionLabel
                      ? "border-primary-500 bg-primary-50"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <input
                    type="radio"
                    name="answer"
                    value={optionLabel}
                    checked={selectedAnswer === optionLabel}
                    onChange={() => handleSelectAnswer(optionLabel)}
                    className="mr-3"
                  />
                  <span className="font-medium mr-2">{optionLabel}.</span>
                  <span>{option}</span>
                </label>
              );
            })}
          </div>
        </div>

        <div className="flex justify-between mt-6">
          <button
            onClick={handlePrev}
            disabled={currentQuestion === 0}
            className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
          >
            Previous
          </button>
          <div className="flex space-x-3">
            <button
              onClick={handleSubmit}
              className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600"
            >
              Submit Exam
            </button>
            <button
              onClick={handleNext}
              disabled={currentQuestion === mockQuestions.length - 1}
              className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
