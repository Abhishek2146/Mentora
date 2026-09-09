import { useState, useEffect, useRef } from "react";
import AppLayout from "@/components/layout/AppLayout";
import {
  Users, MessageSquare, Trophy, Award, Send, Loader2, Bot, User,
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { apiClient } from "@/lib/api";
import { cn } from "@/lib/utils";

type Tab = "chat" | "members" | "leaderboard" | "achievements";

export default function StudyGroup() {
  const { user } = useAuthStore();

  // Group list state
  const [userGroups, setUserGroups] = useState<any[]>([]);
  const [currentGroup, setCurrentGroup] = useState<any>(null);
  const [currentGroupId, setCurrentGroupId] = useState("");

  // Create/Join state
  const [groupName, setGroupName] = useState("");
  const [groupDescription, setGroupDescription] = useState("");
  const [creatingGroup, setCreatingGroup] = useState(false);
  const [createError, setCreateError] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [joiningGroup, setJoiningGroup] = useState(false);
  const [joinError, setJoinError] = useState("");
  const [joinSuccess, setJoinSuccess] = useState("");
  const [deletingGroup, setDeletingGroup] = useState(false);

  // Tab state
  const [activeTab, setActiveTab] = useState<Tab>("chat");

  // Chat state
  const [messages, setMessages] = useState<any[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [sendingMessage, setSendingMessage] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Members state
  const [groupMembers, setGroupMembers] = useState<any[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);

  // Leaderboard state
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [loadingLeaderboard, setLoadingLeaderboard] = useState(false);

  // Achievements state
  const [achievements, setAchievements] = useState<any[]>([]);
  const [loadingAchievements, setLoadingAchievements] = useState(false);

  // Leave state
  const [leavingGroup, setLeavingGroup] = useState(false);

  // Group memory state
  const [groupMemory, setGroupMemory] = useState<any>(null);

  useEffect(() => {
    fetchUserGroups();
  }, []);

  useEffect(() => {
    if (activeTab === "chat" && currentGroupId) {
      fetchGroupMessages(currentGroupId);
    } else if (activeTab === "members" && currentGroupId) {
      fetchGroupMembers(currentGroupId);
    } else if (activeTab === "leaderboard" && currentGroupId) {
      fetchLeaderboard(currentGroupId);
    } else if (activeTab === "achievements" && currentGroupId) {
      fetchAchievements(currentGroupId);
    }
  }, [activeTab, currentGroupId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Poll messages every 5 seconds when on chat tab
  useEffect(() => {
    if (activeTab !== "chat" || !currentGroupId) return;
    const interval = setInterval(() => {
      fetchGroupMessages(currentGroupId, false);
    }, 5000);
    return () => clearInterval(interval);
  }, [activeTab, currentGroupId]);

  const fetchUserGroups = async () => {
    try {
      const response = await apiClient.get("/api/v1/study-groups/");
      const unique = response.data.filter(
        (g: any, i: number, self: any[]) => i === self.findIndex((x: any) => x.id === g.id)
      );
      setUserGroups(unique);
      if (unique.length > 0 && !currentGroupId) {
        selectGroup(unique[0].id);
      }
    } catch (error) {
      console.error("Failed to fetch groups:", error);
    }
  };

  const selectGroup = async (groupId: string) => {
    try {
      setCurrentGroup(null);
      setCurrentGroupId(groupId);
      setActiveTab("chat");
      const response = await apiClient.get(`/api/v1/study-groups/${groupId}`);
      setCurrentGroup(response.data);
      await fetchGroupMessages(groupId);
      await fetchGroupMembers(groupId);
      fetchGroupMemory(groupId);
    } catch (error) {
      console.error("Failed to fetch group detail:", error);
    }
  };

  const fetchGroupMemory = async (groupId: string) => {
    try {
      const response = await apiClient.get(`/api/v1/study-groups/${groupId}/memory`);
      setGroupMemory(response.data.memory);
    } catch (error) {
      setGroupMemory(null);
    }
  };

  const fetchGroupMessages = async (groupId: string, showLoading = true) => {
    try {
      const response = await apiClient.get(`/api/v1/study-groups/${groupId}/messages?limit=100`);
      setMessages(response.data);
    } catch (error) {
      console.error("Failed to fetch messages:", error);
    }
  };

  const fetchGroupMembers = async (groupId: string) => {
    setLoadingMembers(true);
    try {
      const response = await apiClient.get(`/api/v1/study-groups/${groupId}/members`);
      setGroupMembers(response.data);
    } catch (error) {
      console.error("Failed to fetch members:", error);
    } finally {
      setLoadingMembers(false);
    }
  };

  const fetchLeaderboard = async (groupId: string) => {
    setLoadingLeaderboard(true);
    try {
      const response = await apiClient.get(`/api/v1/study-groups/${groupId}/leaderboard?days=7`);
      setLeaderboard(response.data);
    } catch (error) {
      console.error("Failed to fetch leaderboard:", error);
    } finally {
      setLoadingLeaderboard(false);
    }
  };

  const fetchAchievements = async (groupId: string) => {
    setLoadingAchievements(true);
    try {
      const response = await apiClient.get(`/api/v1/study-groups/${groupId}/achievements`);
      setAchievements(response.data);
    } catch (error) {
      console.error("Failed to fetch achievements:", error);
    } finally {
      setLoadingAchievements(false);
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim() || !currentGroupId) return;
    setSendingMessage(true);
    const msgContent = newMessage;
    setNewMessage("");
    try {
      await apiClient.post(`/api/v1/study-groups/${currentGroupId}/messages`, {
        content: msgContent,
      });
      // Refetch messages to get the actual saved messages (including AI responses)
      await fetchGroupMessages(currentGroupId);
    } catch (error) {
      console.error("Failed to send message:", error);
      setNewMessage(msgContent);
    } finally {
      setSendingMessage(false);
    }
  };

  const handleCreateGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingGroup(true);
    setCreateError("");
    try {
      await apiClient.post("/api/v1/study-groups", {
        name: groupName,
        description: groupDescription,
      });
      setGroupName("");
      setGroupDescription("");
      setCreatingGroup(false);
      const groups = await apiClient.get("/api/v1/study-groups/");
      const unique = groups.data.filter(
        (g: any, i: number, self: any[]) => i === self.findIndex((x: any) => x.id === g.id)
      );
      setUserGroups(unique);
      if (unique.length > 0) {
        selectGroup(unique[unique.length - 1].id);
      }
    } catch (error: any) {
      setCreateError(error?.response?.data?.detail || "Failed to create group.");
      setCreatingGroup(false);
    }
  };

  const handleJoinGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    setJoiningGroup(true);
    setJoinError("");
    setJoinSuccess("");
    try {
      const response = await apiClient.post("/api/v1/study-groups/join", {
        invite_code: inviteCode,
      });
      setInviteCode("");
      setJoinSuccess(`Successfully joined "${response.data.name}"`);
      setJoiningGroup(false);
      fetchUserGroups();
    } catch (error: any) {
      setJoinError(error?.response?.data?.detail || "Failed to join group.");
      setJoiningGroup(false);
    }
  };

  const handleLeaveGroup = async () => {
    if (!currentGroupId) return;
    setLeavingGroup(true);
    try {
      await apiClient.post(`/api/v1/study-groups/${currentGroupId}/leave`);
      setCurrentGroup(null);
      setCurrentGroupId("");
      fetchUserGroups();
    } catch (error) {
      console.error("Failed to leave group:", error);
    } finally {
      setLeavingGroup(false);
    }
  };

  const handleDeleteGroup = async () => {
    if (!currentGroupId) return;
    if (!window.confirm("Are you sure you want to delete this group? This action cannot be undone.")) return;
    setDeletingGroup(true);
    try {
      await apiClient.delete(`/api/v1/study-groups/${currentGroupId}`);
      setCurrentGroup(null);
      setCurrentGroupId("");
      fetchUserGroups();
    } catch (error) {
      console.error("Failed to delete group:", error);
    } finally {
      setDeletingGroup(false);
    }
  };

  const getMemberName = (msg: any) => {
    if (msg.message_type === "ai") return "Mentora";
    return msg.sender_name || "Unknown";
  };

  const isAiMessage = (msg: any) => msg.message_type === "ai";

  return (
    <AppLayout title="Study Groups">
      <div className="space-y-4">
        {/* Create Group */}
        <div className="border rounded-lg p-4 bg-white dark:bg-slate-800">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Create Study Group</h2>
          <form onSubmit={handleCreateGroup}>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <input
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                className="w-full rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="Group name"
                required
              />
              <input
                value={groupDescription}
                onChange={(e) => setGroupDescription(e.target.value)}
                className="w-full rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="Description (optional)"
              />
            </div>
            <button
              type="submit"
              disabled={creatingGroup}
              className="w-full mt-3 py-2 rounded-md text-sm font-medium bg-primary-600 text-white hover:bg-primary-500 disabled:opacity-50"
            >
              {creatingGroup ? "Creating..." : "Create Group"}
            </button>
            {createError && <p className="mt-2 text-sm text-red-600">{createError}</p>}
          </form>
        </div>

        {/* Join Group */}
        <div className="border rounded-lg p-4 bg-white dark:bg-slate-800">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Join Study Group</h2>
          <form onSubmit={handleJoinGroup}>
            <div className="flex gap-2">
              <input
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value)}
                className="flex-1 rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="Enter invite code"
                required
              />
              <button
                type="submit"
                disabled={joiningGroup}
                className="px-4 py-2 rounded-md text-sm font-medium bg-primary-600 text-white hover:bg-primary-500 disabled:opacity-50"
              >
                {joiningGroup ? "Joining..." : "Join"}
              </button>
            </div>
            {joinError && <p className="mt-2 text-sm text-red-600">{joinError}</p>}
            {joinSuccess && <p className="mt-2 text-sm text-green-600">{joinSuccess}</p>}
          </form>
        </div>

        {/* Group Chips */}
        {userGroups.length > 0 && (
          <div className="flex gap-2 overflow-x-auto pb-2">
            {userGroups.map((group) => (
              <button
                key={group.id}
                onClick={() => selectGroup(group.id)}
                className={cn(
                  "px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors",
                  currentGroupId === group.id
                    ? "bg-primary-600 text-white shadow-md"
                    : "bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-50"
                )}
              >
                {group.name}
              </button>
            ))}
          </div>
        )}

        {/* Group Detail */}
        {currentGroup && (
          <div className="border rounded-lg bg-white dark:bg-slate-800">
            {/* Group Header */}
            <div className="p-4 border-b border-slate-200 dark:border-slate-700">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h2 className="text-xl font-semibold text-slate-800 dark:text-slate-100">
                    {currentGroup.name}
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Invite Code: <span className="font-mono">{currentGroup.invite_code}</span>
                    {currentGroup.description && ` — ${currentGroup.description}`}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-500 dark:text-slate-400">
                    {groupMembers.length} members
                  </span>
                  {currentGroup.owner_id === user?.id && (
                    <button
                      onClick={handleDeleteGroup}
                      disabled={deletingGroup}
                      className="px-3 py-1.5 rounded-md text-xs font-medium bg-red-700 text-white hover:bg-red-600 disabled:opacity-50"
                    >
                      {deletingGroup ? "Deleting..." : "Delete"}
                    </button>
                  )}
                  <button
                    onClick={handleLeaveGroup}
                    disabled={leavingGroup}
                    className="px-3 py-1.5 rounded-md text-xs font-medium bg-red-600 text-white hover:bg-red-500 disabled:opacity-50"
                  >
                    {leavingGroup ? "Leaving..." : "Leave"}
                  </button>
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-slate-200 dark:border-slate-700">
              {([
                { key: "chat", label: "Chat", icon: MessageSquare },
                { key: "members", label: "Members", icon: Users },
                { key: "leaderboard", label: "Leaderboard", icon: Trophy },
                { key: "achievements", label: "Achievements", icon: Award },
              ] as const).map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => setActiveTab(key)}
                  className={cn(
                    "flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors",
                    activeTab === key
                      ? "border-primary-600 text-primary-600 dark:text-primary-400 dark:border-primary-400"
                      : "border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </div>

            {/* Chat Tab */}
            {activeTab === "chat" && (
              <div className="flex flex-col" style={{ height: "500px" }}>
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {messages.length === 0 && (
                    <div className="text-center text-slate-400 dark:text-slate-500 py-8">
                      <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">No messages yet. Start the conversation!</p>
                      <p className="text-xs mt-1">Type /mentora followed by your question to ask Mentora</p>
                    </div>
                  )}
                  {messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={cn(
                        "flex gap-2",
                        msg.sender_id === user?.id ? "justify-end" : "justify-start"
                      )}
                    >
                      {msg.sender_id !== user?.id && (
                        <div className={cn(
                          "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0",
                          isAiMessage(msg)
                            ? "bg-gradient-to-br from-purple-500 to-blue-500 text-white"
                            : "bg-gradient-to-br from-primary-500 to-secondary-500 text-white"
                        )}>
                          {isAiMessage(msg) ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                        </div>
                      )}
                      <div className={cn("max-w-[75%]", msg.sender_id === user?.id ? "text-right" : "")}>
                        {msg.sender_id !== user?.id && (
                          <p className="text-[10px] text-slate-400 dark:text-slate-500 mb-0.5">
                            {getMemberName(msg)}
                          </p>
                        )}
                        <div
                          className={cn(
                            "rounded-lg px-3 py-2 text-sm",
                            isAiMessage(msg)
                              ? "bg-purple-50 dark:bg-purple-900/20 text-slate-800 dark:text-slate-100 border border-purple-200 dark:border-purple-800"
                              : msg.sender_id === user?.id
                                ? "bg-primary-600 text-white"
                                : "bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100"
                          )}
                        >
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        </div>
                        <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">
                          {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </p>
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>

                {/* Chat Input */}
                <div className="p-3 border-t border-slate-200 dark:border-slate-700">
                  <div className="flex items-center justify-between mb-1.5">
                    <p className="text-[10px] text-slate-400 dark:text-slate-500">
                      Type /mentora followed by your question to ask Mentora
                    </p>
                    {groupMemory && Object.keys(groupMemory).length > 0 && (
                      <p className="text-[10px] text-purple-500 dark:text-purple-400">
                        Mentora is using group learning context
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <input
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage();
                        }
                      }}
                      className="flex-1 rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder="Type a message..."
                      disabled={sendingMessage}
                    />
                    <button
                      onClick={handleSendMessage}
                      disabled={sendingMessage || !newMessage.trim()}
                      className="px-4 py-2 rounded-md bg-primary-600 text-white hover:bg-primary-500 disabled:opacity-50"
                    >
                      {sendingMessage ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Members Tab */}
            {activeTab === "members" && (
              <div className="p-4">
                {loadingMembers ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
                  </div>
                ) : groupMembers.length === 0 ? (
                  <p className="text-center text-slate-400 py-8">No members yet.</p>
                ) : (
                  <div className="space-y-2">
                    {groupMembers.map((member) => (
                      <div
                        key={member.id}
                        className="flex items-center gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50"
                      >
                        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white text-sm font-bold">
                          {member.user?.full_name
                            ? member.user.full_name[0].toUpperCase()
                            : member.user?.username?.[0]?.toUpperCase() ?? "U"}
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                            {member.user?.full_name || member.user?.username}
                          </p>
                          <p className="text-[10px] text-slate-400">{member.user?.username}</p>
                        </div>
                        <span className={cn(
                          "px-2 py-0.5 rounded-full text-[10px] font-medium",
                          member.role === "admin"
                            ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                            : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400"
                        )}>
                          {member.role === "admin" ? "Admin" : "Member"}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Leaderboard Tab */}
            {activeTab === "leaderboard" && (
              <div className="p-4">
                {loadingLeaderboard ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
                  </div>
                ) : leaderboard.length === 0 ? (
                  <p className="text-center text-slate-400 py-8">No study data yet.</p>
                ) : (
                  <div className="space-y-2">
                    {leaderboard.map((entry) => (
                      <div
                        key={entry.user_id}
                        className={cn(
                          "flex items-center gap-3 p-3 rounded-lg",
                          entry.rank === 1 ? "bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800" :
                          entry.rank === 2 ? "bg-slate-50 dark:bg-slate-700/30 border border-slate-200 dark:border-slate-700" :
                          "bg-slate-50 dark:bg-slate-700/30"
                        )}
                      >
                        <div className={cn(
                          "w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold",
                          entry.rank === 1 ? "bg-amber-400 text-white" :
                          entry.rank === 2 ? "bg-slate-400 text-white" :
                          entry.rank === 3 ? "bg-amber-600 text-white" :
                          "bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300"
                        )}>
                          {entry.rank}
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                            {entry.full_name || entry.username}
                          </p>
                          <p className="text-[10px] text-slate-400">
                            {entry.qualifying_days} qualifying days
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-bold text-slate-800 dark:text-slate-100">
                            {entry.study_minutes} min
                          </p>
                          {entry.current_streak > 0 && (
                            <p className="text-[10px] text-orange-500">
                              🔥 {entry.current_streak} day streak
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Achievements Tab */}
            {activeTab === "achievements" && (
              <div className="p-4">
                {loadingAchievements ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
                  </div>
                ) : achievements.length === 0 ? (
                  <p className="text-center text-slate-400 py-8">No achievements earned yet. Keep studying!</p>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {achievements.map((ach, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-3 p-3 rounded-lg bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/10 dark:to-orange-900/10 border border-amber-200 dark:border-amber-800"
                      >
                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white text-lg flex-shrink-0">
                          {ach.badge_type.includes("streak") ? "🔥" :
                           ach.badge_type === "dedicated_learner" ? "📚" :
                           ach.badge_type === "consistent_learner" ? "🎯" : "🏆"}
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                            {ach.badge_name}
                          </p>
                          <p className="text-[10px] text-slate-500 dark:text-slate-400">
                            {ach.full_name || ach.username}
                          </p>
                          <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">
                            {ach.description}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* No group selected */}
        {!currentGroup && userGroups.length === 0 && (
          <div className="text-center py-12 text-slate-400 dark:text-slate-500">
            <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-lg font-medium">No study groups yet</p>
            <p className="text-sm mt-1">Create a group or join one with an invite code</p>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
