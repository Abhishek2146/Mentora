import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/store/authStore";
import {
  HomeIcon,
  BookOpenIcon,
  ClipboardDocumentListIcon,
  QuestionMarkCircleIcon,
  RectangleStackIcon,
  CodeBracketIcon,
  ChatBubbleLeftIcon,
  ChartBarIcon,
  MicrophoneIcon,
  AcademicCapIcon,
  ClockIcon,
  BellIcon,
  UserIcon,
  Cog87Icon as CogIcon,
} from "@heroicons/react/24/outline";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: HomeIcon },
  { name: "Upload Syllabus", href: "/upload-syllabus", icon: BookOpenIcon },
  { name: "Study Plan", href: "/study-plan", icon: ClipboardDocumentListIcon },
  { name: "Daily Quiz", href: "/daily-quiz", icon: QuestionMarkCircleIcon },
  { name: "Flashcards", href: "/flashcards", icon: RectangleStackIcon },
  { name: "MCQ Practice", href: "/mcqs", icon: RectangleStackIcon },
  { name: "Coding Practice", href: "/coding-practice", icon: CodeBracketIcon },
  { name: "AI Tutor", href: "/ai-tutor", icon: ChatBubbleLeftIcon },
  { name: "Progress", href: "/progress", icon: ChartBarIcon },
  { name: "Weak Topics", href: "/weak-topics", icon: BellIcon },
  { name: "Revision Plan", href: "/revision-plan", icon: ClockIcon },
  { name: "Exam Simulator", href: "/exam-simulator", icon: AcademicCapIcon },
  { name: "Analytics", href: "/analytics", icon: ChartBarIcon },
  { name: "Voice Learning", href: "/voice-learning", icon: MicrophoneIcon },
  { name: "Profile", href: "/profile", icon: UserIcon },
  { name: "Settings", href: "/settings", icon: CogIcon },
];

export default function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-gray-100 w-64 overflow-y-auto">
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold">M</span>
          </div>
          <span className="text-xl font-bold text-white">Mentora</span>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary-600 text-white"
                  : "text-gray-300 hover:bg-gray-800 hover:text-white"
              }`}
            >
              <item.icon className="w-5 h-5" />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-800">
        {user && (
          <div className="flex items-center space-x-3 mb-3">
            <div className="w-8 h-8 bg-gray-700 rounded-full flex items-center justify-center">
              <span className="text-sm font-medium text-white">
                {user.full_name?.charAt(0) || user.username.charAt(0)}
              </span>
            </div>
            <div>
              <p className="text-sm font-medium">{user.full_name || user.username}</p>
              <p className="text-xs text-gray-400">{user.role}</p>
            </div>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="w-full text-left px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}
