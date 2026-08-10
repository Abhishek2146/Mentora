import DashboardLayout from "@/components/layout/DashboardLayout";
import { useState, useEffect } from "react";
import { useAuthStore } from "@/store/authStore";

export default function SettingsPage() {
  const { user } = useAuthStore();
  const [settings, setSettings] = useState({
    notifications: true,
    email_updates: false,
    push_notifications: true,
    dark_mode: false,
    timezone: "UTC",
    language: "en",
  });
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    setTimeout(() => {
      setIsSaving(false);
      alert("Settings saved successfully!");
    }, 1000);
  };

  const toggleSetting = (key: string) => {
    setSettings({ ...settings, [key]: !settings[key as keyof typeof settings] });
  };

  return (
    <DashboardLayout>
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>

        <div className="bg-white rounded-lg shadow p-6 space-y-6">
          <h2 className="text-xl font-semibold text-gray-900">Preferences</h2>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="font-medium text-gray-700">Dark Mode</label>
                <p className="text-sm text-gray-500">Use dark theme for the application</p>
              </div>
              <button
                onClick={() => toggleSetting("dark_mode")}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.dark_mode ? "bg-primary-600" : "bg-gray-300"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.dark_mode ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="font-medium text-gray-700">Email Notifications</label>
                <p className="text-sm text-gray-500">Receive study reminders via email</p>
              </div>
              <button
                onClick={() => toggleSetting("email_updates")}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.email_updates ? "bg-primary-600" : "bg-gray-300"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.email_updates ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="font-medium text-gray-700">Push Notifications</label>
                <p className="text-sm text-gray-500">Receive real-time notifications</p>
              </div>
              <button
                onClick={() => toggleSetting("push_notifications")}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.push_notifications ? "bg-primary-600" : "bg-gray-300"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-colors ${
                    settings.push_notifications ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Account</h2>
          <div className="space-y-4">
            <button className="text-left px-4 py-2 text-gray-700 hover:bg-gray-50 rounded-md">
              Change Password
            </button>
            <button className="text-left px-4 py-2 text-gray-700 hover:bg-gray-50 rounded-md">
              Delete Account
            </button>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
          >
            {isSaving ? "Saving..." : "Save Settings"}
          </button>
        </div>
      </div>
    </DashboardLayout>
  );
}
