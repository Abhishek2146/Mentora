import { Link } from "react-router-dom";

export default function Hero() {
  return (
    <section className="hero">
      <div className="wrap">
        <div>
          <p className="eyebrow-note">For exams, not just for now</p>
          <h1>Turn your syllabus into a study plan</h1>
          <p className="lede">
            Upload the document your teacher already gave you. Recall reads it, builds your flashcards and quizzes, and tells you what to review before you forget it.
          </p>
          <div className="hero-actions">
            <Link to="/register" className="btn btn-solid">
              Get started
            </Link>
            <Link to="/login" className="btn btn-ghost">
              Sign in
            </Link>
          </div>
          <p className="hero-note">
            No syllabus yet? Paste in your class notes instead — same result.
          </p>
        </div>

        <div className="card-stack" id="card-stack">
          <div className="note-card" aria-hidden="true" />
          <div className="note-card" aria-hidden="true" />
          <div
            className="note-card"
            id="demo-card"
            role="button"
            tabindex="0"
            aria-label="Sample flashcard, press to flip"
          >
            <p className="flash-label" id="flash-label">Question</p>
            <p className="flash-body" id="flash-body">
              What happens to a memory the first time you're tested on it?
            </p>
            <p className="flash-hint">Tap the card to flip it</p>
          </div>
        </div>
      </div>
    </section>
  );
}