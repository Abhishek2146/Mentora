import { create } from "zustand";
import { persist } from "zustand/middleware";
import { User, Token } from "@/types";
import apiClient from "@/lib/api";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  tokens: Token | null;
  setUser: (user: User | null) => void;
  setTokens: (tokens: Token) => void;
  login: (emailOrUsername: string, password: string) => Promise<void>;
  register: (userData: { email: string; username: string; password: string; full_name?: string; role?: string }) => Promise<void>;
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

          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/login`, {
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

          const userResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${tokens.access_token}` },
          });
          const user: User = await userResponse.json();

          set({ user, isAuthenticated: true, isLoading: false });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      register: async (userData) => {
        set({ isLoading: true });
        try {
          await apiClient.post("/api/v1/auth/register", userData);

          await get().login(userData.email, userData.password);
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: () => {
        apiClient.clearTokensOnLogout();
        set({ user: null, isAuthenticated: false, tokens: null });
        window.location.href = "/login";
      },

      checkAuth: async () => {
        const tokens = get().tokens;
        if (!tokens) {
          set({ isAuthenticated: false, user: null });
          return;
        }

        try {
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${tokens.access_token}` },
          });

          if (response.ok) {
            const user: User = await response.json();
            set({ user, isAuthenticated: true });
          } else {
            set({ user: null, isAuthenticated: false, tokens: null });
          }
        } catch (error) {
          set({ user: null, isAuthenticated: false, tokens: null });
        }
      },

      updateUser: async (data: Partial<User>) => {
        const tokens = get().tokens;
        if (!tokens) throw new Error("Not authenticated");

        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/users/me`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${tokens.access_token}`,
          },
          body: JSON.stringify(data),
        });

        if (response.ok) {
          const updatedUser: User = await response.json();
          set({ user: updatedUser });
        }
      },
    }),
    {
      name: "mentora_auth",
    }
  )
);

export default useAuthStore;
