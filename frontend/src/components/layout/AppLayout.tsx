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
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <Sidebar />
      <main
        className={cn(
          "flex flex-col min-h-screen min-w-0 transition-all duration-300",
          "ml-0",
          sidebarOpen ? "lg:ml-64" : "lg:ml-16"
        )}
      >
        <Header title={title} />
        <div className="flex-1 w-full max-w-full p-4 sm:p-6 animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  );
}
