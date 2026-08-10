"use client";

import { useEffect, useRef } from "react";
import { useUIStore, Notification } from "@/store/uiStore";
import { X } from "@heroicons/react/24/outline";

export function ToastContainer() {
  const { notifications, removeNotification } = useUIStore();

  useEffect(() => {
    notifications.forEach((notification) => {
      if (notification.duration) {
        const timer = setTimeout(() => {
          removeNotification(notification.id);
        }, notification.duration);
        return () => clearTimeout(timer);
      }
    });
  }, [notifications, removeNotification]);

  if (!notifications.length) return null;

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 w-80">
      {notifications.map((notification) => (
        <ToastNotification
          key={notification.id}
          notification={notification}
          onClose={() => removeNotification(notification.id)}
        />
      ))}
    </div>
  );
}

function ToastNotification({
  notification,
  onClose,
}: {
  notification: Notification;
  onClose: () => void;
}) {
  const typeColors = {
    info: "bg-blue-50 border-blue-200 text-blue-800",
    success: "bg-green-50 border-green-200 text-green-800",
    warning: "bg-yellow-50 border-yellow-200 text-yellow-800",
    error: "bg-red-50 border-red-200 text-red-800",
  };

  const iconColors = {
    info: "text-blue-500",
    success: "text-green-500",
    warning: "text-yellow-500",
    error: "text-red-500",
  };

  const icons = {
    info: "ℹ",
    success: "✓",
    warning: "⚠",
    error: "✕",
  };

  return (
    <div
      className={`p-4 rounded-lg border shadow-lg flex items-start ${typeColors[notification.type]}`}
    >
      <div className={`mr-3 ${iconColors[notification.type]}`}>{icons[notification.type]}</div>
      <div className="flex-1">
        <h4 className="font-semibold">{notification.title}</h4>
        <p className="text-sm">{notification.message}</p>
      </div>
      <button
        onClick={onClose}
        className="ml-2 hover:opacity-70 transition-opacity"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
