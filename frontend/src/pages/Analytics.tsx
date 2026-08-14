import AppLayout from "@/components/layout/AppLayout";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, RadarChart, PolarGrid, PolarAngleAxis, Radar, LineChart, Line, CartesianGrid } from "recharts";
import { TrendingUp, Clock, Trophy, Flame } from "lucide-react";

const weekly = [{day:"Mon",score:72},{day:"Tue",score:85},{day:"Wed",score:68},{day:"Thu",score:91},{day:"Fri",score:78},{day:"Sat",score:88},{day:"Sun",score:82}];
const mastery = [{topic:"SQL",mastery:88},{topic:"Normalization",mastery:75},{topic:"ER Diagrams",mastery:90},{topic:"Transactions",mastery:42},{topic:"Indexing",mastery:55},{topic:"Rel. Algebra",mastery:61}];
const daily = [{date:"W1",hours:3.5},{date:"W2",hours:4.2},{date:"W3",hours:3.8},{date:"W4",hours:5.1}];

export default function Analytics() {
  return (
    <AppLayout title="Analytics">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label:"Total Study Hours", value:"47.5h", icon:Clock, color:"text-primary-600", bg:"bg-primary-50 dark:bg-primary-900/30" },
            { label:"Quiz Average", value:"78%", icon:Trophy, color:"text-emerald-600", bg:"bg-emerald-50 dark:bg-emerald-900/30" },
            { label:"Current Streak", value:"12 days", icon:Flame, color:"text-orange-600", bg:"bg-orange-50 dark:bg-orange-900/30" },
            { label:"Topics Mastered", value:"9/18", icon:TrendingUp, color:"text-secondary-600", bg:"bg-secondary-50 dark:bg-secondary-900/30" },
          ].map(s => (
            <div key={s.label} className="stat-card">
              <div className={`w-10 h-10 rounded-xl ${s.bg} flex items-center justify-center`}><s.icon className={`w-5 h-5 ${s.color}`} /></div>
              <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">{s.value}</p>
              <p className="text-xs text-slate-500">{s.label}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card p-5">
            <h3 className="font-bold text-slate-800 dark:text-slate-100 mb-4">Weekly Quiz Scores</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={weekly} barSize={28}>
                <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{fontSize:12,fill:'#94a3b8'}} />
                <YAxis domain={[0,100]} axisLine={false} tickLine={false} tick={{fontSize:12,fill:'#94a3b8'}} />
                <Tooltip contentStyle={{borderRadius:12,border:'none'}} formatter={(v:any) => [`${v}%`, 'Score']} />
                <Bar dataKey="score" fill="#0ea5e9" radius={[6,6,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card p-5">
            <h3 className="font-bold text-slate-800 dark:text-slate-100 mb-4">Topic Mastery Radar</h3>
            <ResponsiveContainer width="100%" height={220}>
              <RadarChart data={mastery}>
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis dataKey="topic" tick={{fontSize:10,fill:'#94a3b8'}} />
                <Radar dataKey="mastery" fill="#8b5cf6" fillOpacity={0.25} stroke="#8b5cf6" strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          <div className="card p-5 lg:col-span-2">
            <h3 className="font-bold text-slate-800 dark:text-slate-100 mb-4">Study Hours Trend</h3>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={daily}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fontSize:12,fill:'#94a3b8'}} />
                <YAxis axisLine={false} tickLine={false} tick={{fontSize:12,fill:'#94a3b8'}} />
                <Tooltip contentStyle={{borderRadius:12,border:'none'}} formatter={(v:any) => [`${v}h`, 'Hours']} />
                <Line dataKey="hours" stroke="#0ea5e9" strokeWidth={3} dot={{r:5,fill:'#0ea5e9'}} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
