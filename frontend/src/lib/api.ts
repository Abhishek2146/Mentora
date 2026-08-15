import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { Token } from "@/types";

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
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
    return tokens ? JSON.parse(tokens).access_token : null;
  }

  private getRefreshToken(): string | null {
    const tokens = localStorage.getItem("mentora_tokens");
    return tokens ? JSON.parse(tokens).refresh_token : null;
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
