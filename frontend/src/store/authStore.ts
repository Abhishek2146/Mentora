import { create } from "zustand";
import { persist } from "zustand/middleware";
import axios from "axios";
import { User, Token, UserRole } from "@/types";
import apiClient from "@/lib/api";

// Marker for frontend-only test sessions (no backend involved).
export const TEST_ACCESS_TOKEN = "test-access-token";

function createTestUser(role: UserRole): User {
  const now = new Date().toISOString();
  return {
    id: role === "admin" ? -2 : -1,
    email:
      role === "admin"
        ? "test-admin@mentora.local"
        : "test-student@mentora.local",
    username: role === "admin" ? "test_admin" : "test_student",
    full_name: role === "admin" ? "Test Admin" : "Test Student",
    role,
    is_active: true,
    is_verified: true,
    avatar_url: null,
    created_at: now,
    updated_at: now,
  };
}

function getApiError(error: unknown): Error {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return new Error(detail);
    if (Array.isArray(detail)) {
      return new Error(detail.map((d) => d.msg ?? JSON.stringify(d)).join("; "));
    }
  }
  return error instanceof Error ? error : new Error("Something went wrong. Please try again.");
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  tokens: Token | null;
  setUser: (user: User | null) => void;
  setTokens: (tokens: Token) => void;
  login: (emailOrUsername: string, password: string) => Promise<void>;
  testLogin: (role: UserRole) => void;
  register: (userData: { email: string; username: string; password: string; full_name?: string }) => Promise<void>;
  registerAdmin: (userData: { email: string; username: string; password: string; full_name?: string; admin_secret: string }) => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  resetPassword: (token: string, password: string) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
  updateUser: (data: Partial<User>) => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      tokens: null,

      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setTokens: (tokens) => set({ tokens }),

      login: async (emailOrUsername, password) => {
        set({ isLoading: true });
        try {
          const formData = new FormData();
          formData.append("username", emailOrUsername);
          formData.append("password", password);

          const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
          const response = await fetch(`${apiUrl}/api/v1/auth/login`, {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Login failed");
          }

          const tokens: Token = await response.json();
          apiClient.setTokensOnLogin(tokens);
          set({ tokens });

          const userResponse = await fetch(`${apiUrl}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${tokens.access_token}` },
          });
          const user: User = await userResponse.json();

          set({ user, isAuthenticated: true, isLoading: false });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      testLogin: (role) => {
        const tokens: Token = {
          access_token: TEST_ACCESS_TOKEN,
          refresh_token: TEST_ACCESS_TOKEN,
          token_type: "bearer",
        };
        set({
          user: createTestUser(role),
          tokens,
          isAuthenticated: true,
          isLoading: false,
        });
      },

      register: async (userData) => {
        set({ isLoading: true });
        try {
          await apiClient.post("/api/v1/auth/register", userData);
        } catch (error) {
          set({ isLoading: false });
          throw getApiError(error);
        }
        try {
          await get().login(userData.email, userData.password);
        } catch {
          // Account created; let the user sign in with their new credentials.
        } finally {
          set({ isLoading: false });
        }
      },

      registerAdmin: async (userData) => {
        set({ isLoading: true });
        try {
          await apiClient.post("/api/v1/auth/register-admin", userData);
        } catch (error) {
          set({ isLoading: false });
          throw getApiError(error);
        }
        try {
          await get().login(userData.email, userData.password);
        } catch {
          // Admin account created; let the user sign in with their new credentials.
        } finally {
          set({ isLoading: false });
        }
      },

      logout: () => {
        apiClient.clearTokensOnLogout();
        set({ user: null, isAuthenticated: false, tokens: null, isLoading: false });
        window.location.href = "/login";
      },

      checkAuth: async () => {
        const tokens = get().tokens;
        if (!tokens) {
          set({ isAuthenticated: false, user: null });
          return;
        }
        if (tokens.access_token === TEST_ACCESS_TOKEN) {
          set({ isAuthenticated: true });
          return;
        }
        try {
          const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
          const response = await fetch(`${apiUrl}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${tokens.access_token}` },
          });
          if (response.ok) {
            const user: User = await response.json();
            set({ user, isAuthenticated: true });
          } else {
            set({ user: null, isAuthenticated: false, tokens: null });
          }
        } catch {
          set({ user: null, isAuthenticated: false, tokens: null });
        }
      },

      updateUser: async (data: Partial<User>) => {
        const tokens = get().tokens;
        if (!tokens) throw new Error("Not authenticated");
        try {
          const res = await apiClient.put("/api/v1/users/me", data);
          set({ user: res.data });
        } catch (error) {
          throw getApiError(error);
        }
      },

      forgotPassword: async (email: string) => {
        set({ isLoading: true });
        try {
          await apiClient.post("/api/v1/auth/forgot-password", { email });
        } catch (error) {
          set({ isLoading: false });
          throw getApiError(error);
        }
        set({ isLoading: false });
      },

      resetPassword: async (token: string, password: string) => {
        set({ isLoading: true });
        try {
          await apiClient.post("/api/v1/auth/reset-password", { token, password });
        } catch (error) {
          set({ isLoading: false });
          throw getApiError(error);
        }
        set({ isLoading: false });
      },

      changePassword: async (currentPassword: string, newPassword: string) => {
        set({ isLoading: true });
        try {
          const tokens = get().tokens;
          if (!tokens) throw new Error("Not authenticated");
          const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
          const response = await fetch(`${apiUrl}/api/v1/auth/change-password`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${tokens.access_token}`,
            },
            body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
          });
          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to change password");
          }
        } catch (error) {
          set({ isLoading: false });
          throw getApiError(error);
        }
        set({ isLoading: false });
      },
    }),
    { 
      name: "mentora_auth",
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        tokens: state.tokens,
      })
    }
  )
);

export default useAuthStore;
