import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(date: string | Date): string {
  return new Date(date).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h > 0 ? `${h}h ` : ""}${m}m ${s}s`;
}

export function getScoreColor(score: number): string {
  if (score >= 80) return "text-success-600";
  if (score >= 60) return "text-warning-600";
  return "text-danger-600";
}

export function getProgressColor(progress: number): string {
  if (progress >= 80) return "bg-success-500";
  if (progress >= 60) return "bg-warning-500";
  return "bg-danger-500";
}

export function truncateText(text: string, maxLength: number = 100): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}

export function getFileIcon(fileType: string): string {
  const type = fileType.toLowerCase();
  if (type === "pdf") return "📄";
  if (["png", "jpg", "jpeg", "gif"].includes(type)) return "🖼️";
  if (type === "mp3" || type === "wav") return "🎵";
  return "📎";
}

export function calculateStreak(dates: string[]): number {
  if (!dates.length) return 0;
  const sorted = dates.map(d => new Date(d).setHours(0, 0, 0, 0)).sort((a, b) => b - a);
  const today = new Date().setHours(0, 0, 0, 0);
  let streak = 0;
  let current = today;

  for (const date of sorted) {
    const diff = Math.floor((current - date) / (1000 * 60 * 60 * 24));
    if (diff === 0 || diff === 1) {
      streak++;
      current = date;
    } else if (diff > 1) {
      break;
    }
  }

  return streak;
}

export function debounce<T extends (...args: any[]) => void>(fn: T, delay: number): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}
