import apiClient from "@/lib/api";
import type { AdminDashboardStats, User, UserWithSubscription, AdminSubscription, BillingCycle } from "@/types";

export const adminService = {
  async getDashboard(): Promise<AdminDashboardStats> {
    const res = await apiClient.get<AdminDashboardStats>("/api/v1/admin/dashboard");
    return res.data;
  },

  async listUsers(params?: {
    role?: string;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<User[]> {
    const res = await apiClient.get<User[]>("/api/v1/admin/users", { params });
    return res.data;
  },

  async getUserWithMembership(userId: number): Promise<UserWithSubscription> {
    const res = await apiClient.get<UserWithSubscription>(`/api/v1/admin/users/${userId}`);
    return res.data;
  },

  async updateUser(
    userId: number,
    data: { role?: string; is_active?: boolean; is_verified?: boolean; full_name?: string }
  ): Promise<User> {
    const res = await apiClient.patch<User>(`/api/v1/admin/users/${userId}`, data);
    return res.data;
  },

  async deleteUser(userId: number): Promise<void> {
    await apiClient.delete(`/api/v1/admin/users/${userId}`);
  },

  async grantMembership(
    userId: number,
    billingCycle: BillingCycle = "MONTHLY",
    autoRenew: boolean = false
  ): Promise<AdminSubscription> {
    const res = await apiClient.post<AdminSubscription>(
      `/api/v1/admin/users/${userId}/grant-membership`,
      { billing_cycle: billingCycle, auto_renew: autoRenew }
    );
    return res.data;
  },

  async revokeMembership(userId: number): Promise<AdminSubscription> {
    const res = await apiClient.post<AdminSubscription>(
      `/api/v1/admin/users/${userId}/revoke-membership`
    );
    return res.data;
  },
};