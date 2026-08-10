import DashboardLayout from "@/components/layout/DashboardLayout";
import apiClient from "@/lib/api";
import { useEffect, useState } from "react";
import { Quiz, Question } from "@/types";

export default function DailyQuizPage() {
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [currentQuiz, setCurrentQuiz] = useState<Quiz | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [timeLeft, setTimeLeft] = useState<number>(0);
  const [isSubmitted, setIsSubmitted] = useState(false);

  useEffect(() => {
    fetchQuizzes();
  }, []);

  const fetchQuizzes = async () => {
    try {
      const response = await apiClient.get("/api/v1/quizzes/");
      setQuizzes(response.data);
    } catch (error) {
      console.error("Failed to fetch quizzes:", error);
    }
  };

  const startQuiz = (quiz: Quiz) => {
    setCurrentQuiz(quiz);
    setTimeLeft((quiz.time_limit || 1800) * 60);
    setAnswers({});
    setIsSubmitted(false);
  };

  const handleAnswer = (questionId: number, answer: string) => {
    setAnswers({ ...answers, [questionId]: answer });
  };

  const handleSubmit = async () => {
    if (!currentQuiz) return;

    const attemptData = {
      quiz_id: currentQuiz.id,
      score: 0,
      total_questions: currentQuiz.questions.length,
      correct_answers: 0,
      time_taken: currentQuiz.time_limit || 0,
      answers: answers,
      is_passed: false,
    };

    try {
      await apiClient.post(`/api/v1/quizzes/${currentQuiz.id}/attempt`, attemptData);
      setIsSubmitted(true);
    } catch (error) {
      console.error("Failed to submit:", error);
    }
  };

  const retakeQuiz = () => {
    getCurrentQuiz().questions.forEach(q => {
      setAnswers(prev => ({ ...prev, [q.id]: "" }));
    });
    setIsSubmitted(false);
  };

  const getCurrentQuiz = () => {
    if (!currentQuiz) return null;
    return currentQuiz;
  };

  if (!currentQuiz) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <h1 className="text-3xl font-bold text-gray-900">Daily Quiz</h1>
          <p className="text-gray-600">Practice your knowledge with AI-generated quizzes.</p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {quizzes.map((quiz) => (
              <div key={quiz.id} className="bg-white rounded-lg shadow p-6 cursor-pointer hover:shadow-md transition-shadow" onClick={() => startQuiz(quiz)}>
                <h3 className="font-bold text-lg text-gray-900">{quiz.title}</h3>
                <p className="text-gray-600 mt-2 text-sm">{quiz.description}</p>
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-sm text-gray-500">{quiz.questions?.length || 0} Questions</span>
                  <span className="text-sm text-gray-500">
                    {quiz.time_limit ? `${quiz.time_limit}s` : "No time limit"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </DashboardLayout>
    );
  }

  const quiz = getCurrentQuiz();
  if (!quiz) return null;

  return (
    <DashboardLayout>
      <div className="max-w-3xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">{quiz.title}</h1>
          <p className="text-gray-600 mt-1">{quiz.description}</p>
        </div>

        {!isSubmitted ? (
          <div className="space-y-6">
            {quiz.questions?.map((q) => (
              <div key={q.id} className="bg-white rounded-lg shadow p-6">
                <h3 className="font-semibold text-lg mb-3">{q.question_text}</h3>
                <div className="space-y-2">
                  {q.options?.map((option, i) => {
                    const optionLabel = String.fromCharCode(65 + i);
                    return (
                      <label
                        key={i}
                        className={`flex items-center p-3 border rounded-lg cursor-pointer transition-colors ${
                          answers[q.id] === optionLabel
                            ? "border-primary-500 bg-primary-50"
                            : "border-gray-200 hover:border-gray-300"
                        }`}
                      >
                        <input
                          type="radio"
                          name={`q${q.id}`}
                          value={optionLabel}
                          checked={answers[q.id] === optionLabel}
                          onChange={() => handleAnswer(q.id, optionLabel)}
                          className="mr-3"
                        />
                        <span className="font-medium mr-2">{optionLabel}.</span>
                        <span>{option}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            ))}

            <button
              onClick={handleSubmit}
              disabled={Object.keys(answers).length < quiz.questions.length}
              className="w-full bg-primary-600 text-white py-3 rounded-md hover:bg-primary-700 disabled:opacity-50"
            >
              Submit Quiz
            </button>
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="text-6xl font-bold text-primary-600 mb-4">
              Quiz Submitted!
            </div>
            <p className="text-gray-600 mb-6">Results will be available in your progress section.</p>
            <button
              onClick={retakeQuiz}
              className="px-6 py-3 bg-primary-600 text-white rounded-md hover:bg-primary-700"
            >
              Retake Quiz
            </button>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
