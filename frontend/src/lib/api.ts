import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { Token } from "@/types";

// Resolve the backend API base URL. Prefers VITE_API_URL; otherwise derive it
// from the hostname the page is opened on so LAN/IP access works (a friend
// opening http://<lan-ip>:5173 hits http://<lan-ip>:8000, not their own localhost).
export function getApiBase(): string {
  const configured = import.meta.env.VITE_API_URL;
  if (configured) return configured;
  const hostname =
    typeof window !== "undefined" ? window.location.hostname : "localhost";
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://localhost:8000";
  }
  return `http://${hostname}:8000`;
}

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: getApiBase(),
      timeout: 30000,
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = this.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response: AxiosResponse) => response,
      async (error) => {
        if (error.response?.status === 401 && !error.config._retry) {
          error.config._retry = true;
          const refreshToken = this.getRefreshToken();
          if (refreshToken) {
            try {
              const response = await this.client.post<Token>("/api/v1/auth/refresh", {
                refresh_token: refreshToken,
              });
              this.setTokens(response.data);
              error.config.headers.Authorization = `Bearer ${response.data.access_token}`;
              return this.client(error.config);
            } catch {
              this.clearTokens();
              window.location.href = "/login";
            }
          }
        }
        return Promise.reject(error);
      }
    );
  }

  private getAccessToken(): string | null {
    const tokens = localStorage.getItem("mentora_tokens");
    if (tokens) {
      try {
        const parsed = JSON.parse(tokens);
        if (parsed?.access_token) return parsed.access_token;
      } catch {}
    }
    const auth = localStorage.getItem("mentora_auth");
    if (auth) {
      try {
        const parsed = JSON.parse(auth);
        if (parsed?.state?.tokens?.access_token) return parsed.state.tokens.access_token;
      } catch {}
    }
    return "test-access-token";
  }

  private getRefreshToken(): string | null {
    const tokens = localStorage.getItem("mentora_tokens");
    if (tokens) {
      try {
        const parsed = JSON.parse(tokens);
        if (parsed?.refresh_token) return parsed.refresh_token;
      } catch {}
    }
    const auth = localStorage.getItem("mentora_auth");
    if (auth) {
      try {
        const parsed = JSON.parse(auth);
        if (parsed?.state?.tokens?.refresh_token) return parsed.state.tokens.refresh_token;
      } catch {}
    }
    return null;
  }

  private setTokens(tokens: Token) {
    localStorage.setItem("mentora_tokens", JSON.stringify(tokens));
  }

  private clearTokens() {
    localStorage.removeItem("mentora_tokens");
  }

  setTokensOnLogin(tokens: Token) { this.setTokens(tokens); }
  clearTokensOnLogout() { this.clearTokens(); }

  get<T = any>(url: string, config?: any): Promise<AxiosResponse<T>> {
    return this.client.get<T>(url, config);
  }
  post<T = any>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>> {
    return this.client.post<T>(url, data, config);
  }
  put<T = any>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>> {
    return this.client.put<T>(url, data, config);
  }
  delete<T = any>(url: string, config?: any): Promise<AxiosResponse<T>> {
    return this.client.delete<T>(url, config);
  }
  patch<T = any>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>> {
    return this.client.patch<T>(url, data, config);
  }
}

export const apiClient = new ApiClient();
export default apiClient;
