import apiClient from "@/lib/api";
import type { Notification, NotificationListResponse, NotificationStats, BulkNotificationAction } from "@/types/api";

export const notificationService = {
  async getNotifications(params: {
    page?: number;
    per_page?: number;
    unread_only?: boolean;
    archived_only?: boolean;
    notification_type?: string;
  } = {}): Promise<NotificationListResponse> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.append("page", params.page.toString());
    if (params.per_page) searchParams.append("per_page", params.per_page.toString());
    if (params.unread_only) searchParams.append("unread_only", "true");
    if (params.archived_only) searchParams.append("archived_only", "true");
    if (params.notification_type) searchParams.append("notification_type", params.notification_type);

    const res = await apiClient.get(`/api/v1/notifications?${searchParams.toString()}`);
    return res.data;
  },

  async getNotification(notificationId: number): Promise<Notification> {
    const res = await apiClient.get(`/api/v1/notifications/${notificationId}`);
    return res.data;
  },

  async getUnreadCount(): Promise<{ unread_count: number }> {
    const res = await apiClient.get("/api/v1/notifications/unread-count");
    return res.data;
  },

  async getStats(): Promise<NotificationStats> {
    const res = await apiClient.get("/api/v1/notifications/stats");
    return res.data;
  },

  async markAsRead(notificationId: number): Promise<Notification> {
    const res = await apiClient.post(`/api/v1/notifications/${notificationId}/read`);
    return res.data;
  },

  async markAsUnread(notificationId: number): Promise<Notification> {
    const res = await apiClient.post(`/api/v1/notifications/${notificationId}/unread`);
    return res.data;
  },

  async archive(notificationId: number): Promise<Notification> {
    const res = await apiClient.post(`/api/v1/notifications/${notificationId}/archive`);
    return res.data;
  },

  async unarchive(notificationId: number): Promise<Notification> {
    const res = await apiClient.post(`/api/v1/notifications/${notificationId}/unarchive`);
    return res.data;
  },

  async delete(notificationId: number): Promise<void> {
    await apiClient.delete(`/api/v1/notifications/${notificationId}`);
  },

  async bulkAction(action: BulkNotificationAction): Promise<{ message: string; affected: number; total: number }> {
    const res = await apiClient.post("/api/v1/notifications/bulk-action", action);
    return res.data;
  },

  async markAllAsRead(): Promise<{ message: string; count: number }> {
    const res = await apiClient.post("/api/v1/notifications/mark-all-read");
    return res.data;
  },
};