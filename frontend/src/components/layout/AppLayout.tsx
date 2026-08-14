import { ReactNode } from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";
import { useUIStore } from "@/store/uiStore";
import { cn } from "@/lib/utils";

interface AppLayoutProps {
  children: ReactNode;
  title?: string;
}

export default function AppLayout({ children, title }: AppLayoutProps) {
  const { sidebarOpen } = useUIStore();

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex">
      <Sidebar />
      <main
        className={cn(
          "flex-1 flex flex-col min-h-screen transition-all duration-300",
          sidebarOpen ? "ml-64" : "ml-16"
        )}
      >
        <Header title={title} />
        <div className="flex-1 p-6 animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  );
}
