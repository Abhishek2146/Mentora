import { useState, useEffect, useCallback } from "react";
import apiClient from "@/lib/api";

export function useApi<T>(url: string, deps: any[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get(url);
      setData(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  }, [url]);

  useEffect(() => {
    fetchData();
  }, deps);

  return { data, loading, error, refetch: fetchData };
}

export function useAuth() {
  const { isAuthenticated, user, isLoading } = require("@/store/authStore").useAuthStore();

  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return {
    isAuthenticated: mounted && isAuthenticated,
    user,
    isLoading,
  };
}

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === "undefined") return initialValue;
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      return initialValue;
    }
  });

  const setValue = (value: T | ((prev: T) => T)) => {
    setStoredValue((prev) => {
      const newValue = value instanceof Function ? (value as (prev: T) => T)(prev) : value;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(key, JSON.stringify(newValue));
      }
      return newValue;
    });
  };

  return [storedValue, setValue] as const;
}

export function useTimer(initialTime: number) {
  const [time, setTime] = useState(initialTime);
  const [isActive, setIsActive] = useState(false);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isActive && time > 0) {
      interval = setInterval(() => {
        setTime((t) => t - 1);
      }, 1000);
    } else if (time === 0) {
      setIsActive(false);
    }
    return () => clearInterval(interval);
  }, [isActive, time]);

  return {
    time,
    isActive,
    start: () => setIsActive(true),
    pause: () => setIsActive(false),
    reset: (newTime?: number) => setTime(newTime || initialTime),
  };
}
