import AppLayout from "@/components/layout/AppLayout";
import { Calendar, Clock } from "lucide-react";

const schedule = [
  { day: "Monday", sessions: [{time:"09:00",topic:"Normalization (1NF–BCNF)",duration:90,type:"study"},{time:"15:00",topic:"SQL Joins Quiz",duration:30,type:"quiz"}] },
  { day: "Tuesday", sessions: [{time:"09:00",topic:"Transaction Management",duration:120,type:"study"},{time:"16:00",topic:"ACID Flashcards",duration:20,type:"revision"}] },
  { day: "Wednesday", sessions: [{time:"10:00",topic:"Indexing & B+ Trees",duration:90,type:"study"}] },
  { day: "Thursday", sessions: [{time:"09:00",topic:"Relational Algebra",duration:60,type:"study"},{time:"14:00",topic:"Mock Test",duration:60,type:"quiz"}] },
  { day: "Friday", sessions: [{time:"09:00",topic:"Full Revision",duration:120,type:"revision"}] },
];

const typeColor = (t: string) => t === "quiz" ? "bg-warning-50 text-warning-600 border-warning-200" : t === "revision" ? "bg-secondary-50 text-secondary-600 border-secondary-200" : "bg-primary-50 text-primary-600 border-primary-200";

export default function StudyPlan() {
  return (
    <AppLayout title="Study Plan">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="card p-6 bg-gradient-to-r from-secondary-600 to-primary-600 text-white border-0">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-secondary-100 text-sm">Exam Date</p>
              <h2 className="text-2xl font-bold">May 15, 2024</h2>
              <p className="text-secondary-100 mt-1 text-sm">43 days remaining • 4h/day target</p>
            </div>
            <div className="text-right">
              <p className="text-4xl font-black">43</p>
              <p className="text-secondary-100 text-sm">days left</p>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          {schedule.map((day) => (
            <div key={day.day} className="card p-5">
              <h3 className="font-bold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-2">
                <Calendar className="w-4 h-4 text-primary-500" />{day.day}
              </h3>
              <div className="space-y-2">
                {day.sessions.map((s, i) => (
                  <div key={i} className={`flex items-center gap-4 p-3 rounded-xl border ${typeColor(s.type)}`}>
                    <span className="text-xs font-mono font-bold w-12">{s.time}</span>
                    <span className="flex-1 text-sm font-medium">{s.topic}</span>
                    <span className="text-xs flex items-center gap-1">
                      <Clock className="w-3 h-3" />{s.duration}m
                    </span>
                    <span className="text-xs capitalize font-semibold">{s.type}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
