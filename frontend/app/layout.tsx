import type { Metadata } from "next";
import { Inter, Roboto Slab } from "next/font/google";
import "./styles/globals.css";
import { Providers } from "@/components/common/Providers";
import { cn } from "@/lib/utils";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const robotoSlab = Roboto Slab({
  subsets: ["latin"],
  variable: "--font-roboto-slab",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Mentora - AI Learning Companion",
  description: "Your personalized AI-powered learning companion for mastering any subject.",
  keywords: "AI learning, personalized study, quiz generator, flashcards, coding practice, AI tutor",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={cn(
          inter.variable,
          robotoSlab.variable,
          "min-h-screen bg-gray-50 font-sans antialiased"
        )}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
