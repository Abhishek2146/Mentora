import AppLayout from "@/components/layout/AppLayout";
import { Bell, Moon, Globe, LogOut } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { useState } from "react";

export default function Settings() {
  const { logout } = useAuthStore();
  const [dark, setDark] = useState(document.documentElement.classList.contains("dark"));
  const [notifs, setNotifs] = useState(true);

  const toggleDark = () => { document.documentElement.classList.toggle("dark"); setDark(d => !d); };

  const sections = [
    {
      title: "Appearance",
      items: [{ icon: Moon, label: "Dark Mode", sub: "Switch between light and dark theme", control: (
        <button onClick={toggleDark} className={`w-12 h-6 rounded-full transition-all ${ dark ? "bg-primary-500" : "bg-slate-200" }`}>
          <span className={`block w-5 h-5 bg-white rounded-full shadow transition-transform ${ dark ? "translate-x-6" : "translate-x-0.5" }`} />
        </button>
      ) }],
    },
    {
      title: "Notifications",
      items: [{ icon: Bell, label: "Study Reminders", sub: "Daily reminders to study", control: (
        <button onClick={() => setNotifs(n => !n)} className={`w-12 h-6 rounded-full transition-all ${ notifs ? "bg-primary-500" : "bg-slate-200" }`}>
          <span className={`block w-5 h-5 bg-white rounded-full shadow transition-transform ${ notifs ? "translate-x-6" : "translate-x-0.5" }`} />
        </button>
      ) }],
    },
    {
      title: "Language",
      items: [{ icon: Globe, label: "Display Language", sub: "Currently: English", control: (
        <select className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200">
          <option>English</option><option>Hindi</option><option>Nepali</option>
        </select>
      ) }],
    },
  ];

  return (
    <AppLayout title="Settings">
      <div className="max-w-xl mx-auto space-y-6">
        {sections.map(s => (
          <div key={s.title} className="card p-5">
            <h3 className="font-bold text-slate-700 dark:text-slate-200 mb-4">{s.title}</h3>
            {s.items.map(item => (
              <div key={item.label} className="flex items-center gap-4">
                <div className="w-9 h-9 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                  <item.icon className="w-4 h-4 text-slate-500" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{item.label}</p>
                  <p className="text-xs text-slate-400">{item.sub}</p>
                </div>
                {item.control}
              </div>
            ))}
          </div>
        ))}

        <div className="card p-5 border-danger-200 dark:border-red-700">
          <h3 className="font-bold text-danger-600 mb-4">Account</h3>
          <button onClick={logout} className="flex items-center gap-3 w-full p-3 rounded-xl hover:bg-danger-50 dark:hover:bg-red-900/20 text-danger-600 transition-colors">
            <LogOut className="w-4 h-4" />
            <span className="text-sm font-medium">Sign Out</span>
          </button>
        </div>
      </div>
    </AppLayout>
  );
}
