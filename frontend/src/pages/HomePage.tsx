import { Link } from "react-router-dom";
import {
  Brain, Zap, BarChart3, BookOpen, CreditCard, CalendarDays,
  Upload, ArrowRight, CheckCircle2, Star, GraduationCap,
  TrendingUp, Target, Users, Sparkles, ChevronRight,
} from "lucide-react";

const features = [
  { icon: Brain,       color: "from-violet-500 to-purple-600", bg: "bg-violet-50 dark:bg-violet-900/20",  title: "AI Tutor",        desc: "Get instant explanations tailored to your syllabus. Ask anything, anytime." },
  { icon: CreditCard,  color: "from-blue-500 to-cyan-500",     bg: "bg-blue-50 dark:bg-blue-900/20",      title: "Smart Flashcards", desc: "Auto-generated cards with spaced-repetition scheduling so you never forget." },
  { icon: BarChart3,   color: "from-emerald-500 to-teal-500",  bg: "bg-emerald-50 dark:bg-emerald-900/20",title: "Analytics",        desc: "Track your progress weekly and spot the exact topics that need more attention." },
  { icon: CalendarDays,color: "from-orange-500 to-amber-500",  bg: "bg-orange-50 dark:bg-orange-900/20",  title: "Study Plans",      desc: "Personalised daily routines built around your exam date." },
  { icon: BookOpen,    color: "from-pink-500 to-rose-500",     bg: "bg-pink-50 dark:bg-pink-900/20",      title: "MCQ and Quizzes",  desc: "Topic-matched questions generated straight from your syllabus content." },
  { icon: Zap,         color: "from-yellow-500 to-orange-500", bg: "bg-yellow-50 dark:bg-yellow-900/20",  title: "Exam Simulator",   desc: "Timed full-length mock exams to build confidence and stamina." },
];

const steps = [
  { number: "01", icon: Upload,      title: "Upload your syllabus", desc: "PDF, photo, or scanned notes. Mentora reads it all and extracts every topic." },
  { number: "02", icon: Sparkles,    title: "AI builds your plan",   desc: "We generate flashcards, quizzes, and a daily study schedule tailored to your exam date." },
  { number: "03", icon: Target,      title: "Practice every day",    desc: "Short, focused sessions guided by spaced-repetition and performance data." },
  { number: "04", icon: TrendingUp,  title: "Watch scores rise",     desc: "Mentora highlights weak spots and adjusts your plan so you improve fast." },
];

const stats = [
  { value: "50k+",  label: "Students" },
  { value: "3.2M+", label: "Flashcards created" },
  { value: "94%",   label: "Pass-rate improvement" },
  { value: "4.9",   label: "Average rating" },
];

const testimonials = [
  { name: "Priya S.", role: "Medical student",      avatar: "PS", color: "from-pink-500 to-rose-500",    quote: "I uploaded my anatomy syllabus and had 200 flashcards ready in minutes. My marks went from 62 to 84 in one semester." },
  { name: "Aryan K.", role: "Engineering student",  avatar: "AK", color: "from-blue-500 to-indigo-600",  quote: "The exam simulator exposed every gap in my understanding before the actual test, not during it." },
  { name: "Sita M.",  role: "Law student",           avatar: "SM", color: "from-emerald-500 to-teal-500", quote: "I used to spend hours re-reading notes. Mentora replaced that with 20-minute daily sessions that actually stick." },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 overflow-x-hidden">

      {/* Navbar */}
      <nav className="sticky top-0 z-50 bg-white/80 dark:bg-slate-950/80 backdrop-blur-xl border-b border-slate-200/70 dark:border-slate-800/70">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-2.5 flex-shrink-0">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center shadow-md">
              <GraduationCap className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">Mentora</span>
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600 dark:text-slate-400">
            <a href="#features" className="hover:text-primary-600 transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-primary-600 transition-colors">How it works</a>
            <a href="#testimonials" className="hover:text-primary-600 transition-colors">Reviews</a>
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
      <section className="relative pt-24 pb-28 overflow-hidden">
        <div className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-gradient-to-br from-primary-200/50 to-secondary-200/30 dark:from-primary-900/30 dark:to-secondary-900/20 blur-3xl" />
          <div className="absolute -bottom-20 -right-40 w-[500px] h-[500px] rounded-full bg-gradient-to-tr from-secondary-200/40 to-primary-200/30 dark:from-secondary-900/20 dark:to-primary-900/15 blur-3xl" />
        </div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 mb-8 rounded-full bg-primary-50 dark:bg-primary-900/30 border border-primary-200 dark:border-primary-700/50 text-primary-700 dark:text-primary-300 text-sm font-semibold">
            <Sparkles className="w-3.5 h-3.5" /> AI-powered learning for every student
          </div>
          <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold text-slate-900 dark:text-white leading-tight tracking-tight mb-6">
            Turn your syllabus<br />
            <span className="bg-gradient-to-r from-primary-500 via-secondary-500 to-primary-600 bg-clip-text text-transparent">into exam success</span>
          </h1>
          <p className="text-lg sm:text-xl text-slate-600 dark:text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Upload your syllabus, and Mentora builds personalised flashcards, quizzes, and a daily study plan so you study smarter, not harder.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-10">
            <Link to="/register" className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3.5 rounded-xl font-semibold text-base bg-gradient-to-r from-primary-500 to-secondary-500 text-white shadow-lg hover:shadow-xl hover:scale-105 active:scale-95 transition-all">
              Start for free <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/login" className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3.5 rounded-xl font-semibold text-base border-2 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-primary-400 hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-all">
              Already a member? Sign in
            </Link>
          </div>
          <p className="text-sm text-slate-400 mb-14">No credit card required &middot; Free forever plan</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-3xl mx-auto">
            {stats.map((s) => (
              <div key={s.label} className="bg-white dark:bg-slate-800/60 rounded-2xl border border-slate-200 dark:border-slate-700 px-4 py-5 shadow-sm hover:shadow-md transition-shadow">
                <div className="text-2xl sm:text-3xl font-extrabold bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">{s.value}</div>
                <div className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1 font-medium">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 bg-slate-50 dark:bg-slate-900/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <p className="text-sm font-semibold text-primary-600 dark:text-primary-400 uppercase tracking-widest mb-3">Everything you need</p>
            <h2 className="text-4xl sm:text-5xl font-extrabold text-slate-900 dark:text-white mb-4">All your study tools in one place</h2>
            <p className="text-lg text-slate-600 dark:text-slate-400 max-w-xl mx-auto">From flashcards to mock exams, every tool is powered by your own syllabus.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f) => (
              <div key={f.title} className="group bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
                <div className={f.bg + " w-12 h-12 rounded-xl flex items-center justify-center mb-4"}>
                  <div className={"w-6 h-6 bg-gradient-to-br " + f.color + " rounded-lg flex items-center justify-center"}>
                    <f.icon className="w-3.5 h-3.5 text-white" />
                  </div>
                </div>
                <h3 className="font-bold text-lg text-slate-900 dark:text-white mb-2">{f.title}</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{f.desc}</p>
                <div className="mt-4 flex items-center gap-1 text-sm font-semibold text-primary-600 dark:text-primary-400 opacity-0 group-hover:opacity-100 transition-opacity">
                  Explore <ChevronRight className="w-4 h-4" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <p className="text-sm font-semibold text-secondary-600 dark:text-secondary-400 uppercase tracking-widest mb-3">Simple by design</p>
            <h2 className="text-4xl sm:text-5xl font-extrabold text-slate-900 dark:text-white mb-4">From PDF to top marks in 4 steps</h2>
            <p className="text-lg text-slate-600 dark:text-slate-400 max-w-xl mx-auto">The whole setup takes under two minutes. Everything after that runs on autopilot.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map((step) => (
              <div key={step.number} className="relative flex flex-col items-center text-center group">
                <div className="w-28 h-28 rounded-2xl bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 shadow-md group-hover:shadow-xl group-hover:border-primary-300 dark:group-hover:border-primary-600 transition-all duration-300 flex flex-col items-center justify-center mb-5">
                  <span className="text-xs font-bold text-slate-400 dark:text-slate-500 mb-1">{step.number}</span>
                  <step.icon className="w-7 h-7 text-primary-500" />
                </div>
                <h3 className="font-bold text-base text-slate-900 dark:text-white mb-2">{step.title}</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Recall highlight */}
      <section className="py-24 bg-gradient-to-br from-primary-600 via-secondary-600 to-primary-700 relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute top-0 left-0 w-96 h-96 rounded-full bg-white/5 blur-3xl" />
          <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full bg-black/10 blur-3xl" />
        </div>
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="text-white">
              <p className="text-sm font-semibold text-white/60 uppercase tracking-widest mb-4">Spaced repetition</p>
              <h2 className="text-4xl sm:text-5xl font-extrabold leading-tight mb-6">Stop rereading.<br />Start recalling.</h2>
              <p className="text-lg text-white/80 leading-relaxed mb-8">Being tested on something encodes it far better than reading it again. Every Mentora session is built around active recall.</p>
              <ul className="space-y-3 mb-10">
                {["Auto-generated from your exact syllabus", "Spaced-repetition scheduling built in", "Review sessions under 20 minutes a day"].map((item) => (
                  <li key={item} className="flex items-start gap-3 text-white/90 text-sm">
                    <CheckCircle2 className="w-5 h-5 text-white mt-0.5 flex-shrink-0" />{item}
                  </li>
                ))}
              </ul>
              <Link to="/register" className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl font-semibold bg-white text-primary-600 shadow-lg hover:shadow-xl hover:scale-105 active:scale-95 transition-all">
                Try it free <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
            <div className="flex items-center justify-center">
              <div className="relative w-72 h-48">
                <div className="absolute inset-0 rounded-2xl bg-white/10 border border-white/20 rotate-6 scale-95" />
                <div className="absolute inset-0 rounded-2xl bg-white/15 border border-white/20 rotate-3" />
                <div className="absolute inset-0 rounded-2xl bg-white shadow-2xl p-6 flex flex-col justify-between">
                  <div>
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Flashcard</p>
                    <p className="text-slate-800 font-semibold text-base leading-snug">What is the primary function of the hippocampus in memory formation?</p>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex gap-1">{[1,2,3,4,5].map((s) => (<Star key={s} className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />))}</div>
                    <span className="text-xs text-slate-400">Tap to flip</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section id="testimonials" className="py-24 bg-slate-50 dark:bg-slate-900/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <p className="text-sm font-semibold text-primary-600 dark:text-primary-400 uppercase tracking-widest mb-3">Student stories</p>
            <h2 className="text-4xl sm:text-5xl font-extrabold text-slate-900 dark:text-white mb-4">Real results, real students</h2>
          </div>
          <div className="grid sm:grid-cols-3 gap-6">
            {testimonials.map((t) => (
              <div key={t.name} className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm hover:shadow-lg transition-shadow">
                <div className="flex gap-1 mb-4">{[1,2,3,4,5].map((s) => (<Star key={s} className="w-4 h-4 text-amber-400 fill-amber-400" />))}</div>
                <p className="text-slate-700 dark:text-slate-300 text-sm leading-relaxed mb-6">{t.quote}</p>
                <div className="flex items-center gap-3">
                  <div className={"w-10 h-10 rounded-xl bg-gradient-to-br " + t.color + " flex items-center justify-center text-white text-sm font-bold flex-shrink-0"}>{t.avatar}</div>
                  <div>
                    <p className="font-semibold text-sm text-slate-900 dark:text-white">{t.name}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{t.role}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <div className="relative rounded-3xl overflow-hidden bg-gradient-to-br from-slate-900 via-primary-900 to-slate-900 px-8 py-16 shadow-2xl">
            <div className="pointer-events-none absolute -top-20 -left-20 w-72 h-72 rounded-full bg-primary-500/20 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-20 -right-20 w-72 h-72 rounded-full bg-secondary-500/20 blur-3xl" />
            <div className="relative z-10">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 mb-6 rounded-full bg-white/10 border border-white/20 text-white/80 text-sm font-medium">
                <Users className="w-3.5 h-3.5" /> Join 50,000+ students already learning smarter
              </div>
              <h2 className="text-4xl sm:text-5xl font-extrabold text-white mb-4">Ready to ace your exams?</h2>
              <p className="text-lg text-white/70 mb-8 max-w-xl mx-auto">Upload your syllabus and get your first study plan in under 2 minutes.</p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                <Link to="/register" className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3.5 rounded-xl font-semibold text-base bg-gradient-to-r from-primary-400 to-secondary-400 text-white shadow-lg hover:shadow-xl hover:scale-105 active:scale-95 transition-all">
                  Get started, its free <ArrowRight className="w-4 h-4" />
                </Link>
                <Link to="/login" className="w-full sm:w-auto inline-flex items-center justify-center px-8 py-3.5 rounded-xl font-semibold text-base border border-white/20 text-white/80 hover:bg-white/10 transition-colors">
                  Sign in
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-10 border-t border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center">
              <GraduationCap className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-slate-800 dark:text-white">Mentora</span>
          </div>
          <p className="text-sm text-slate-500">Built for students, by students.</p>
          <div className="flex items-center gap-4 text-sm text-slate-500">
            <a href="mailto:hello@mentora.ai" className="hover:text-primary-600 transition-colors">Contact</a>
            <a href="#" className="hover:text-primary-600 transition-colors">Privacy</a>
            <a href="#" className="hover:text-primary-600 transition-colors">Terms</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
