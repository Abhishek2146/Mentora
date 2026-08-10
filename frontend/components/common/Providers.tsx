"use client";

import { ReactNode, useEffect } from "react";
import { useAuthStore } from "@/store/authStore";
import { ToastContainer } from "@/components/common/ToastContainer";

export function Providers({ children }: { children: React.ReactNode }) {
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <>
      {children}
      <ToastContainer />
    </>
  );
}
