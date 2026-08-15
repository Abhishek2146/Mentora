// Mock data for DBMS (Database Management Systems) subject
export const mockUser = {
  id: 1,
  email: "student@mentora.ai",
  username: "dipeesh",
  full_name: "Dipeesh Kumar",
  role: "student" as const,
  is_active: true,
  is_verified: true,
  avatar_url: null,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: null,
};

export const mockFlashcards = [
  { id: 1, deck_id: 1, front: "What is DBMS?", back: "A Database Management System (DBMS) is software that manages databases. It provides an interface to perform CRUD operations and ensures data security, integrity, and consistency.", difficulty: "Easy", ease_factor: 2.5, interval: 1, repetitions: 0, next_review: null, last_reviewed: null },
  { id: 2, deck_id: 1, front: "What is BCNF?", back: "Boyce-Codd Normal Form (BCNF) is a stricter version of 3NF. A relation is in BCNF if for every functional dependency X→Y, X is a superkey.", difficulty: "Hard", ease_factor: 2.5, interval: 1, repetitions: 0, next_review: null, last_reviewed: null },
  { id: 3, deck_id: 1, front: "What is a Primary Key?", back: "A Primary Key is a column (or combination of columns) that uniquely identifies each row in a table. It cannot be NULL and must be unique.", difficulty: "Easy", ease_factor: 2.5, interval: 1, repetitions: 0, next_review: null, last_reviewed: null },
  { id: 4, deck_id: 1, front: "What is a Foreign Key?", back: "A Foreign Key is a column that creates a link between two tables. It references the Primary Key of another table, enforcing referential integrity.", difficulty: "Easy", ease_factor: 2.5, interval: 1, repetitions: 0, next_review: null, last_reviewed: null },
  { id: 5, deck_id: 1, front: "What are ACID properties?", back: "ACID stands for: Atomicity (all or nothing), Consistency (valid state), Isolation (concurrent transactions don't interfere), Durability (committed transactions persist).", difficulty: "Medium", ease_factor: 2.5, interval: 1, repetitions: 0, next_review: null, last_reviewed: null },
  { id: 6, deck_id: 1, front: "What is Normalization?", back: "Normalization is the process of organizing a database to reduce redundancy and improve data integrity. Normal forms: 1NF, 2NF, 3NF, BCNF, 4NF, 5NF.", difficulty: "Medium", ease_factor: 2.5, interval: 1, repetitions: 0, next_review: null, last_reviewed: null },
  { id: 7, deck_id: 1, front: "Difference between INNER JOIN and LEFT JOIN?", back: "INNER JOIN returns rows where there's a match in both tables. LEFT JOIN returns all rows from the left table and matched rows from the right (NULL if no match).", difficulty: "Medium", ease_factor: 2.5, interval: 1, repetitions: 0, next_review: null, last_reviewed: null },
  { id: 8, deck_id: 1, front: "What is an Index?", back: "An Index is a data structure that improves query speed. It creates a separate structure with pointers to the actual data rows. Trade-off: faster reads, slower writes.", difficulty: "Medium", ease_factor: 2.5, interval: 1, repetitions: 0, next_review: null, last_reviewed: null },
];

export const mockQuizQuestions = [
  {
    id: 1,
    question_type: "mcq",
    question_text: "Which normal form eliminates transitive functional dependencies?",
    options: ["1NF", "2NF", "3NF", "BCNF"],
    correct_answer: "3NF",
    explanation: "3NF (Third Normal Form) eliminates transitive dependencies — where a non-key attribute depends on another non-key attribute.",
    difficulty: "Medium",
    order: 1,
  },
  {
    id: 2,
    question_type: "mcq",
    question_text: "What does SQL stand for?",
    options: ["Structured Query Language", "Simple Query Language", "Sequential Query Logic", "Structured Question List"],
    correct_answer: "Structured Query Language",
    explanation: "SQL stands for Structured Query Language — the standard language for relational database management.",
    difficulty: "Easy",
    order: 2,
  },
  {
    id: 3,
    question_type: "mcq",
    question_text: "Which SQL clause is used to filter grouped results?",
    options: ["WHERE", "HAVING", "GROUP BY", "ORDER BY"],
    correct_answer: "HAVING",
    explanation: "HAVING filters groups after GROUP BY. WHERE filters individual rows before grouping.",
    difficulty: "Medium",
    order: 3,
  },
  {
    id: 4,
    question_type: "mcq",
    question_text: "What is a deadlock in DBMS?",
    options: ["A slow query", "A circular wait between transactions", "A corrupted index", "A failed backup"],
    correct_answer: "A circular wait between transactions",
    explanation: "Deadlock occurs when two or more transactions are waiting for each other to release locks, creating a circular dependency.",
    difficulty: "Hard",
    order: 4,
  },
  {
    id: 5,
    question_type: "mcq",
    question_text: "Which type of JOIN returns all rows when there is a match in either table?",
    options: ["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL OUTER JOIN"],
    correct_answer: "FULL OUTER JOIN",
    explanation: "FULL OUTER JOIN returns all rows from both tables, with NULL where there's no match on either side.",
    difficulty: "Medium",
    order: 5,
  },
];

export const mockWeakTopics = [
  { id: 1, topic_name: "Transaction Management", accuracy: 42, confidence_level: 35, total_attempts: 18, recommended_action: "Review ACID properties and 2PL protocol", subject: "DBMS" },
  { id: 2, topic_name: "B+ Tree Indexing", accuracy: 55, confidence_level: 48, total_attempts: 12, recommended_action: "Practice insertion and deletion in B+ Trees", subject: "DBMS" },
  { id: 3, topic_name: "Relational Algebra", accuracy: 61, confidence_level: 52, total_attempts: 22, recommended_action: "Solve more relational algebra expressions", subject: "DBMS" },
];

export const mockStudyPlan = {
  examDate: "2024-05-15",
  dailyGoalHours: 4,
  schedule: [
    { day: "Monday", sessions: [{ time: "09:00", topic: "Normalization (1NF-BCNF)", duration: 90, type: "study" }, { time: "15:00", topic: "SQL Joins Quiz", duration: 30, type: "quiz" }] },
    { day: "Tuesday", sessions: [{ time: "09:00", topic: "Transaction Management", duration: 120, type: "study" }, { time: "16:00", topic: "ACID Properties Flashcards", duration: 20, type: "revision" }] },
    { day: "Wednesday", sessions: [{ time: "10:00", topic: "Indexing & B+ Trees", duration: 90, type: "study" }] },
    { day: "Thursday", sessions: [{ time: "09:00", topic: "Relational Algebra", duration: 60, type: "study" }, { time: "14:00", topic: "Mock Test", duration: 60, type: "quiz" }] },
    { day: "Friday", sessions: [{ time: "09:00", topic: "Full Revision", duration: 120, type: "revision" }] },
  ],
};

export const mockAnalytics = {
  total_study_hours: 47.5,
  quiz_average: 78,
  streak_days: 12,
  tasks_completed: 34,
  weekly_scores: [
    { day: "Mon", score: 72 },
    { day: "Tue", score: 85 },
    { day: "Wed", score: 68 },
    { day: "Thu", score: 91 },
    { day: "Fri", score: 78 },
    { day: "Sat", score: 88 },
    { day: "Sun", score: 82 },
  ],
  topic_mastery: [
    { topic: "SQL", mastery: 88 },
    { topic: "Normalization", mastery: 75 },
    { topic: "ER Diagrams", mastery: 90 },
    { topic: "Transactions", mastery: 42 },
    { topic: "Indexing", mastery: 55 },
    { topic: "Relational Algebra", mastery: 61 },
  ],
};

export const mockRevisionPlan = [
  { id: 1, topic: "SQL Joins", dueLabel: "Today", type: "Flashcards", estimatedMinutes: 20, status: "Due" },
  { id: 2, topic: "Normalization", dueLabel: "Tomorrow", type: "Quiz", estimatedMinutes: 30, status: "Upcoming" },
  { id: 3, topic: "ACID Properties", dueLabel: "In 3 days", type: "Video + Notes", estimatedMinutes: 45, status: "Upcoming" },
  { id: 4, topic: "B+ Tree", dueLabel: "Overdue by 2d", type: "Practice Problems", estimatedMinutes: 60, status: "Overdue" },
];

export const mockCodingProblems = [
  {
    id: 1,
    title: "Find Employees With High Salary",
    description: "Write a SQL query to find all employees with salary greater than 50000. Return name and salary columns.",
    difficulty: "easy" as const,
    category: "SQL",
    tags: ["SQL", "SELECT", "WHERE"],
    starter_code: "SELECT name, salary\nFROM employees\nWHERE -- your condition here;",
    test_cases: [{ input: "", expected: "Alice, 60000\nBob, 75000" }],
    constraints: "Table: employees (id, name, salary, department)",
    user_id: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: null,
  },
  {
    id: 2,
    title: "Count Students Per Department",
    description: "Write a SQL query to count the number of students in each department. Return department name and student count.",
    difficulty: "medium" as const,
    category: "SQL",
    tags: ["SQL", "GROUP BY", "COUNT"],
    starter_code: "SELECT department, COUNT(*) as student_count\nFROM students\n-- complete the query;",
    test_cases: [{ input: "", expected: "CS, 45\nECE, 38\nME, 32" }],
    constraints: "Table: students (id, name, department, year)",
    user_id: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: null,
  },
];
