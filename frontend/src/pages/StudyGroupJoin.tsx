import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Loader2, Users, Check, X } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { apiClient } from "@/lib/api";

export default function StudyGroupJoin() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState("");
  const [groupInfo, setGroupInfo] = useState<any>(null);

  useEffect(() => {
    if (token) {
      loadGroupPreview();
    }
  }, [token]);

  const loadGroupPreview = async () => {
    try {
      setLoading(true);
      // Try to join directly - if successful, we redirect to the group
      const response = await apiClient.get(`/api/v1/study-groups/join/${token}`);
      setGroupInfo(response.data);
      setLoading(false);
    } catch (err: any) {
      setLoading(false);
      if (err?.response?.status === 404) {
        setError("Invalid or expired invitation link.");
      } else if (err?.response?.status === 401) {
        navigate("/login");
      } else if (err?.response?.status === 400) {
        // Already a member
        setError(err?.response?.data?.detail || "Cannot join group.");
      } else {
        setError("Failed to load group information.");
      }
    }
  };

  const handleJoin = async () => {
    if (!token) return;
    setJoining(true);
    try {
      await apiClient.get(`/api/v1/study-groups/join/${token}`);
      navigate("/study-groups");
    } catch (err: any) {
      setJoining(false);
      setError(err?.response?.data?.detail || "Failed to join group.");
    }
  };

  if (loading) {
    return (
      <AppLayout title="Join Study Group">
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
        </div>
      </AppLayout>
    );
  }

  if (error) {
    return (
      <AppLayout title="Join Study Group">
        <div className="max-w-md mx-auto mt-10">
          <div className="border rounded-lg p-6 bg-white dark:bg-slate-800 text-center">
            <X className="w-12 h-12 mx-auto mb-3 text-red-500" />
            <p className="text-slate-800 dark:text-slate-100 font-medium">{error}</p>
            <button
              onClick={() => navigate("/study-groups")}
              className="mt-4 px-4 py-2 rounded-md bg-primary-600 text-white hover:bg-primary-500"
            >
              Go to Study Groups
            </button>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Join Study Group">
      <div className="max-w-md mx-auto mt-10">
        <div className="border rounded-lg p-6 bg-white dark:bg-slate-800 text-center">
          <div className="w-16 h-16 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center mx-auto mb-4">
            <Users className="w-8 h-8 text-primary-600 dark:text-primary-400" />
          </div>
          <h2 className="text-xl font-semibold text-slate-800 dark:text-slate-100">
            {groupInfo?.name || "Study Group"}
          </h2>
          {groupInfo?.description && (
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              {groupInfo.description}
            </p>
          )}
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
            Created by {groupInfo?.owner_id ? `User #${groupInfo.owner_id}` : "Unknown"}
          </p>
          <button
            onClick={handleJoin}
            disabled={joining}
            className="mt-6 w-full py-2.5 rounded-md text-sm font-medium bg-primary-600 text-white hover:bg-primary-500 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {joining ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Joining...
              </>
            ) : (
              <>
                <Check className="w-4 h-4" />
                Join Group
              </>
            )}
          </button>
        </div>
      </div>
    </AppLayout>
  );
}
