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
    <div className="min-h-screen bg-[#F8F7F4] dark:bg-[#1A1918] text-[#252525] dark:text-[#F8F7F4] relative selection:bg-[#6F4FB1]/20">
      {/* Soft background grid (matches the global grid from index.css) */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              "linear-gradient(to right, rgba(111,79,177,0.07) 1px, transparent 1px), linear-gradient(to bottom, rgba(111,79,177,0.07) 1px, transparent 1px)",
            backgroundSize: "40px 40px",
            filter: "blur(0.4px)",
          }}
        />
        {/* Soft ambient background glow in Calm Lavender and Soft Sage */}
        <div className="absolute -top-32 right-1/4 w-96 h-96 rounded-full bg-[#6F4FB1]/5 blur-3xl" />
        <div className="absolute top-1/3 -left-20 w-80 h-80 rounded-full bg-[#8FAF9A]/5 blur-3xl" />
      </div>

      <Sidebar />
      <main
        className={cn(
          "flex flex-col min-h-screen min-w-0 transition-all duration-300 ease-in-out",
          "ml-0",
          sidebarOpen ? "lg:ml-64" : "lg:ml-16"
        )}
      >
        <Header title={title} />
        <div className="flex-1 w-full max-w-full p-4 sm:p-6 lg:p-8 animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  );
}
