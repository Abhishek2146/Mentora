import { Link } from "react-router-dom";
import logo from "@/assets/logo.png";
import dipeshImg from "../../assets/dipesh.png";
import sarojImg from "../../assets/Saroj.jpeg";
import abhishekImg from "../../assets/abhishek.jpeg";
import {
  GraduationCap, Sparkles, Target, ArrowRight, Github, Linkedin, Heart,
} from "lucide-react";

const contributors = [
  {
    name: "Dipesh",
    role: "Frontend Developer",
    image: dipeshImg,
    bio: "Crafts the clean, distraction-free interface you use every day, turning complex study workflows into effortless flows.",
    tags: ["React", "UI / UX", "Accessibility"],
  },
  {
    name: "Abhishek",
    role: "Backend Developer",
    image: abhishekImg,
    bio: "Builds the robust APIs and services that power everything behind the scenes from auth to the study-engine pipelines.",
    tags: ["FastAPI", "APIs", "Database"],
  },
  {
    name: "Saroj",
    role: "AI Engineer",
    image: sarojImg,
    bio: "Designs the AI tutor and weak-topic detection models that help students spot gaps and learn smarter every day.",
    tags: ["AI / ML", "LLMs", "ChromaDB"],
  },
];

const values = [
  { icon: Sparkles, title: "Student-first", desc: "Every feature starts with a real study problem, not a shiny gimmick." },
  { icon: Target, title: "Evidence-based", desc: "We lean on spaced repetition and active recall the methods proven to stick." },
  { icon: Heart, title: "Free to learn", desc: "Great education shouldn't be paywalled. Our core tools stay free, forever." },
];

export default function About() {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 overflow-x-hidden">

      {/* Navbar */}
      <nav className="sticky top-0 z-50 bg-white/80 dark:bg-slate-950/80 backdrop-blur-xl border-b border-slate-200/70 dark:border-slate-800/70">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-2.5 flex-shrink-0">
            <img src={logo} alt="Mentora logo" className="w-8 h-8 object-contain" />
            <span className="font-bold text-xl bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">Mentora</span>
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600 dark:text-slate-400">
            <Link to="/" className="hover:text-primary-600 transition-colors">Home</Link>
            <Link to="/about" className="hover:text-primary-600 transition-colors">About</Link>
            <a href="#contributors" className="hover:text-primary-600 transition-colors">Contributors</a>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <Link to="/login" className="hidden sm:inline-flex items-center px-4 py-2 text-sm font-semibold text-slate-700 dark:text-slate-300 hover:text-primary-600 transition-colors">Sign in</Link>
            <Link to="/register" className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold bg-gradient-to-r from-primary-500 to-secondary-500 text-white shadow-md hover:shadow-lg hover:scale-105 transition-all">
              Get started <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-24 pb-20 overflow-hidden">
        <div className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-gradient-to-br from-primary-200/50 to-secondary-200/30 dark:from-primary-900/30 dark:to-secondary-900/20 blur-3xl" />
          <div className="absolute -bottom-20 -right-40 w-[500px] h-[500px] rounded-full bg-gradient-to-tr from-secondary-200/40 to-primary-200/30 dark:from-secondary-900/20 dark:to-primary-900/15 blur-3xl" />
        </div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 mb-8 rounded-full bg-primary-50 dark:bg-primary-900/30 border border-primary-200 dark:border-primary-700/50 text-primary-700 dark:text-primary-300 text-sm font-semibold">
            <Sparkles className="w-3.5 h-3.5" /> Built for students, by students
          </div>
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold text-slate-900 dark:text-white leading-tight tracking-tight mb-6">
            Meet the people behind<br />
            <span className="bg-gradient-to-r from-primary-500 via-secondary-500 to-primary-600 bg-clip-text text-transparent">Mentora</span>
          </h1>
          <p className="text-lg sm:text-xl text-slate-600 dark:text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            We're a small team of students and engineers who were tired of studying harder so we built something smarter.
            Mentora turns any syllabus into flashcards, quizzes, and a personalised study plan.
          </p>
        </div>
      </section>

      {/* Contributors */}
      <section id="contributors" className="py-20 bg-slate-50 dark:bg-slate-900/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <p className="text-sm font-semibold text-primary-600 dark:text-primary-400 uppercase tracking-widest mb-3">Our team</p>
            <h2 className="text-4xl sm:text-5xl font-extrabold text-slate-900 dark:text-white mb-4">The contributors</h2>
            <p className="text-lg text-slate-600 dark:text-slate-400 max-w-xl mx-auto">Three builders, one mission — making exam prep effortless for every student.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {contributors.map((c) => (
              <div key={c.name} className="group bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 flex flex-col items-center text-center">
                <div className="relative mb-5">
                  <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary-500 to-secondary-500 opacity-40 blur-lg group-hover:opacity-70 transition-opacity" />
                  <img
                    src={c.image}
                    alt={c.name}
                    className="relative w-28 h-28 rounded-full object-cover border-4 border-white dark:border-slate-800 shadow-lg ring-2 ring-primary-200 dark:ring-primary-700/60"
                  />
                </div>
                <h3 className="font-bold text-xl text-slate-900 dark:text-white mb-1">{c.name}</h3>
                <p className="text-sm font-semibold text-primary-600 dark:text-primary-400 mb-3">{c.role}</p>
                <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed mb-5">{c.bio}</p>
                <div className="flex flex-wrap items-center justify-center gap-2 mb-5">
                  {c.tags.map((t) => (
                    <span key={t} className="px-3 py-1 rounded-full bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-xs font-semibold">
                      {t}
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-3 mt-auto">
                  <a href="#" className="p-2 rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-300 hover:text-primary-600 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors" aria-label={c.name + " on GitHub"}>
                    <Github className="w-4 h-4" />
                  </a>
                  <a href="#" className="p-2 rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-300 hover:text-primary-600 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors" aria-label={c.name + " on LinkedIn"}>
                    <Linkedin className="w-4 h-4" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <p className="text-sm font-semibold text-secondary-600 dark:text-secondary-400 uppercase tracking-widest mb-3">What we believe</p>
            <h2 className="text-4xl sm:text-5xl font-extrabold text-slate-900 dark:text-white mb-4">Our values</h2>
          </div>
          <div className="grid sm:grid-cols-3 gap-6">
            {values.map((v) => (
              <div key={v.title} className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm hover:shadow-lg transition-shadow">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center mb-4">
                  <v.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-bold text-lg text-slate-900 dark:text-white mb-2">{v.title}</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{v.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <div className="relative rounded-3xl overflow-hidden bg-gradient-to-br from-slate-900 via-primary-900 to-slate-900 px-8 py-16 shadow-2xl">
            <div className="pointer-events-none absolute -top-20 -left-20 w-72 h-72 rounded-full bg-primary-500/20 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-20 -right-20 w-72 h-72 rounded-full bg-secondary-500/20 blur-3xl" />
            <div className="relative z-10">
              <h2 className="text-4xl sm:text-5xl font-extrabold text-white mb-4">Want to learn smarter?</h2>
              <p className="text-lg text-white/70 mb-8 max-w-xl mx-auto">Join the students already acing their exams with Mentora.</p>
              <Link to="/register" className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl font-semibold text-base bg-gradient-to-r from-primary-400 to-secondary-400 text-white shadow-lg hover:shadow-xl hover:scale-105 active:scale-95 transition-all">
                Start for free <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-10 border-t border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-slate-500">Built with love by 3 contributors.</p>
          <div className="flex items-center gap-4 text-sm text-slate-500">
            <Link to="/about" className="hover:text-primary-600 transition-colors">About us</Link>
            <a href="mailto:hello@mentora.ai" className="hover:text-primary-600 transition-colors">Contact</a>
            <a href="#" className="hover:text-primary-600 transition-colors">Privacy</a>
            <a href="#" className="hover:text-primary-600 transition-colors">Terms</a>
          </div>
        </div>
      </footer>
    </div>
  );
}