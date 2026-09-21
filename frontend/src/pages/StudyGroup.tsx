import { useState, useEffect, useRef } from "react";
import AppLayout from "@/components/layout/AppLayout";
import {
  Users, MessageSquare, Trophy, Award, Send, Loader2, Bot, User,
  Plus, LogIn, Copy, Check, Crown, Trash2, LogOut, Hash, Sparkles, X,
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { apiClient } from "@/lib/api";
import { cn } from "@/lib/utils";

type Tab = "chat" | "members" | "leaderboard" | "achievements";

const TABS: { key: Tab; label: string; icon: typeof MessageSquare }[] = [
  { key: "chat", label: "Chat", icon: MessageSquare },
  { key: "members", label: "Members", icon: Users },
  { key: "leaderboard", label: "Leaderboard", icon: Trophy },
  { key: "achievements", label: "Achievements", icon: Award },
];

const medalFor = (rank: number) =>
  rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : "";

const initialsOf = (name?: string, username?: string) =>
  (name?.trim()?.[0] || username?.trim()?.[0] || "U").toUpperCase();

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
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);

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

  const isOwner = currentGroup?.owner_id === user?.id;

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
      await apiClient.post("/api/v1/study-groups/", {
        name: groupName,
        description: groupDescription,
      });
      setGroupName("");
      setGroupDescription("");
      setCreatingGroup(false);
      setShowCreateModal(false);
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
      setShowJoinModal(false);
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

  const handleCopyInvite = async () => {
    if (!currentGroup?.invite_code) return;
    try {
      await navigator.clipboard.writeText(currentGroup.invite_code);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 1800);
    } catch {
      setCopiedCode(false);
    }
  };

  const getMemberName = (msg: any) => {
    if (msg.message_type === "ai") return "Mentora AI";
    return msg.sender_name || "Unknown";
  };

  const isAiMessage = (msg: any) => msg.message_type === "ai";

  const openCreateModal = () => {
    setCreateError("");
    setShowCreateModal(true);
  };

  const openJoinModal = () => {
    setJoinError("");
    setJoinSuccess("");
    setShowJoinModal(true);
  };

  return (
    <AppLayout title="Study Groups">
      <div className="max-w-6xl mx-auto space-y-4">

        {/* Header action bar */}
        <div className="card p-4 border border-slate-200 dark:border-slate-700 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-primary-500" /> Study Groups
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Collaborate with peers, ask Mentora, and climb the group leaderboard.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={openJoinModal} className="btn-secondary btn-sm">
              <LogIn className="w-4 h-4" /> Join Group
            </button>
            <button onClick={openCreateModal} className="btn-primary btn-sm">
              <Plus className="w-4 h-4" /> New Group
            </button>
          </div>
        </div>

        {userGroups.length === 0 ? (
          /* ---- Empty state ---- */
          <div className="card p-12 text-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center mx-auto">
              <Users className="w-8 h-8 text-primary-500" />
            </div>
            <div>
              <p className="text-lg font-semibold text-slate-800 dark:text-slate-100">No study groups yet</p>
              <p className="text-sm text-slate-500 mt-1">
                Create your own group or join one with an invite code to get started.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 pt-1">
              <button onClick={openCreateModal} className="btn-primary btn-sm">
                <Plus className="w-4 h-4" /> Create a Group
              </button>
              <button onClick={openJoinModal} className="btn-outline btn-sm">
                <LogIn className="w-4 h-4" /> Join with Code
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6">

            {/* ---- Groups sidebar ---- */}
            <div className="lg:col-span-1 space-y-2">
              <div className="flex items-center justify-between px-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Your Groups
                </span>
                <span className="text-xs text-slate-400">{userGroups.length}</span>
              </div>
              <div className="space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
                {userGroups.map((group) => {
                  const active = currentGroupId === group.id;
                  return (
                    <button
                      key={group.id}
                      onClick={() => selectGroup(group.id)}
                      className={cn(
                        "card w-full text-left p-3.5 border transition-all",
                        active
                          ? "border-primary-500 bg-primary-50/60 dark:bg-primary-900/20 shadow-sm"
                          : "hover:border-slate-300 dark:hover:border-slate-600"
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 text-white flex items-center justify-center text-sm font-bold flex-shrink-0 shadow-sm">
                          {initialsOf(group.name)}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
                            {group.name}
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                            {group.description || "No description"}
                          </p>
                        </div>
                        {active && <Check className="w-4 h-4 text-primary-500 flex-shrink-0" />}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* ---- Group detail ---- */}
            <div className="lg:col-span-2 min-w-0">
              {currentGroup ? (
                <div className="card overflow-hidden">
                  {/* Group header banner */}
                  <div className="relative overflow-hidden p-5 bg-gradient-to-br from-[#3C2468] via-[#4B2E83] to-[#2E1B50] text-white">
                    <div className="absolute -top-16 -right-10 w-56 h-56 rounded-full bg-white/10 blur-3xl pointer-events-none" />
                    <div className="absolute -bottom-20 left-1/4 w-48 h-48 rounded-full bg-primary-400/20 blur-3xl pointer-events-none" />
                    <div className="relative flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h2 className="text-xl font-bold truncate">{currentGroup.name}</h2>
                          {isOwner && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/15 border border-white/20">
                              <Crown className="w-3 h-3" /> Owner
                            </span>
                          )}
                        </div>
                        {currentGroup.description && (
                          <p className="text-sm text-white/70 mt-1">{currentGroup.description}</p>
                        )}
                        <div className="flex flex-wrap items-center gap-2 mt-3">
                          <button
                            onClick={handleCopyInvite}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/20 border border-white/15 text-xs font-mono transition-colors"
                            title="Copy invite code"
                          >
                            <Hash className="w-3.5 h-3.5" />
                            {currentGroup.invite_code}
                            {copiedCode ? (
                              <Check className="w-3.5 h-3.5 text-green-300" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                          <span className="inline-flex items-center gap-1.5 text-xs text-white/70">
                            <Users className="w-3.5 h-3.5" />
                            {groupMembers.length} member{groupMembers.length !== 1 ? "s" : ""}
                          </span>
                          {groupMemory && Object.keys(groupMemory).length > 0 && (
                            <span className="inline-flex items-center gap-1.5 text-xs text-white/70">
                              <Sparkles className="w-3.5 h-3.5" /> AI context active
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {isOwner && (
                          <button
                            onClick={handleDeleteGroup}
                            disabled={deletingGroup}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/10 hover:bg-danger-500/80 border border-white/15 transition-colors disabled:opacity-50"
                          >
                            {deletingGroup ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Trash2 className="w-3.5 h-3.5" />
                            )}
                            Delete
                          </button>
                        )}
                        <button
                          onClick={handleLeaveGroup}
                          disabled={leavingGroup}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/10 hover:bg-white/20 border border-white/15 transition-colors disabled:opacity-50"
                        >
                          {leavingGroup ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <LogOut className="w-3.5 h-3.5" />
                          )}
                          Leave
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Segmented tabs */}
                  <div className="p-3 border-b border-[#E7E5E0] dark:border-[#383533]">
                    <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-100 dark:bg-slate-800/60">
                      {TABS.map(({ key, label, icon: Icon }) => (
                        <button
                          key={key}
                          onClick={() => setActiveTab(key)}
                          className={cn(
                            "flex-1 flex items-center justify-center gap-1.5 px-2 sm:px-3 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all",
                            activeTab === key
                              ? "bg-white dark:bg-slate-700 text-primary-600 dark:text-primary-300 shadow-sm"
                              : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                          )}
                        >
                          <Icon className="w-3.5 h-3.5" />
                          <span className="hidden sm:inline">{label}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Chat Tab */}
                  {activeTab === "chat" && (
                    <div className="flex flex-col h-[calc(100vh-360px)] min-h-[420px]">
                      <div className="flex-1 overflow-y-auto px-4 py-5">
                        <div className="max-w-3xl mx-auto space-y-3.5">
                        {messages.length === 0 && (
                          <div className="text-center text-slate-400 py-10">
                            <div className="w-14 h-14 rounded-2xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center mx-auto mb-3">
                              <MessageSquare className="w-7 h-7 text-primary-400" />
                            </div>
                            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                              No messages yet
                            </p>
                            <p className="text-xs mt-1">Start the conversation with your group.</p>
                          </div>
                        )}
                        {messages.map((msg) => {
                          const mine = msg.sender_id === user?.id;
                          const ai = isAiMessage(msg);
                          return (
                            <div
                              key={msg.id}
                              className={cn("flex gap-2.5", mine ? "justify-end" : "justify-start")}
                            >
                              {!mine && (
                                <div
                                  className={cn(
                                    "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm",
                                    ai
                                      ? "bg-gradient-to-br from-primary-500 to-secondary-500 text-white"
                                      : "bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300"
                                  )}
                                >
                                  {ai ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                                </div>
                              )}
                              <div className={cn("max-w-[75%] flex flex-col", mine ? "items-end" : "items-start")}>
                                {!mine && (
                                  <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 mb-0.5 px-1">
                                    {getMemberName(msg)}
                                  </p>
                                )}
                                <div
                                  className={cn(
                                    "rounded-2xl px-3.5 py-2 text-sm shadow-sm",
                                    ai
                                      ? "bg-secondary-50 dark:bg-secondary-900/20 text-slate-800 dark:text-slate-100 border border-secondary-200 dark:border-secondary-800 rounded-bl-sm"
                                      : mine
                                        ? "bg-primary-500 text-white rounded-br-sm"
                                        : "bg-slate-100 dark:bg-slate-700/60 text-slate-800 dark:text-slate-100 rounded-bl-sm"
                                  )}
                                >
                                  <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                                </div>
                                <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5 px-1">
                                  {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                </p>
                              </div>
                            </div>
                          );
                        })}
                        <div ref={messagesEndRef} />
                        </div>
                      </div>

                      {/* Composer */}
                      <div className="border-t border-[#E7E5E0] dark:border-[#383533] bg-slate-50/50 dark:bg-slate-900/20 flex-shrink-0">
                        <div className="max-w-3xl mx-auto p-3">
                        <div className="flex items-center gap-2">
                          <input
                            value={newMessage}
                            onChange={(e) => setNewMessage(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                handleSendMessage();
                              }
                            }}
                            className="input flex-1 text-sm"
                            placeholder="Message your group…"
                            disabled={sendingMessage}
                          />
                          <button
                            onClick={handleSendMessage}
                            disabled={sendingMessage || !newMessage.trim()}
                            className="btn-primary btn-md !rounded-xl flex-shrink-0"
                            title="Send message"
                          >
                            {sendingMessage ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Send className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                        <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1.5 flex items-center gap-1">
                          <Sparkles className="w-3 h-3 text-primary-400" />
                          Tip: start a message with <span className="font-mono font-semibold">/mentora</span> to get AI help for the group.
                        </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Members Tab */}
                  {activeTab === "members" && (
                    <div className="p-4">
                      {loadingMembers ? (
                        <div className="flex items-center justify-center py-12">
                          <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
                        </div>
                      ) : groupMembers.length === 0 ? (
                        <p className="text-center text-slate-400 py-12 text-sm">No members yet.</p>
                      ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {groupMembers.map((member) => (
                            <div
                              key={member.id}
                              className="flex items-center gap-3 p-3.5 rounded-xl border border-[#E7E5E0] dark:border-[#383533] bg-white dark:bg-[#222120] hover:shadow-soft transition-shadow"
                            >
                              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white text-sm font-bold flex-shrink-0 shadow-sm">
                                {initialsOf(member.user?.full_name, member.user?.username)}
                              </div>
                              <div className="min-w-0 flex-1">
                                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
                                  {member.user?.full_name || member.user?.username}
                                </p>
                                <p className="text-[11px] text-slate-400 truncate">
                                  @{member.user?.username}
                                </p>
                              </div>
                              {member.role === "admin" ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400 flex-shrink-0">
                                  <Crown className="w-3 h-3" /> Admin
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400 flex-shrink-0">
                                  Member
                                </span>
                              )}
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
                        <div className="flex items-center justify-center py-12">
                          <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
                        </div>
                      ) : leaderboard.length === 0 ? (
                        <p className="text-center text-slate-400 py-12 text-sm">No study data yet.</p>
                      ) : (
                        <div className="space-y-2">
                          <p className="text-[11px] text-slate-400 px-1 pb-1">Top study time over the last 7 days</p>
                          {leaderboard.map((entry) => {
                            const rank = entry.rank;
                            const isPodium = rank <= 3;
                            return (
                              <div
                                key={entry.user_id}
                                className={cn(
                                  "flex items-center gap-3 p-3 rounded-xl border transition-colors",
                                  rank === 1
                                    ? "border-warning-300 bg-warning-50/70 dark:bg-warning-900/10"
                                    : rank === 2
                                      ? "border-slate-300 bg-slate-50 dark:bg-slate-700/30"
                                      : rank === 3
                                        ? "border-warning-200/70 bg-warning-50/40 dark:bg-slate-700/20"
                                        : "border-[#E7E5E0] dark:border-[#383533] bg-white dark:bg-[#222120]"
                                )}
                              >
                                <div
                                  className={cn(
                                    "w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0",
                                    rank === 1
                                      ? "bg-warning-400 text-white"
                                      : rank === 2
                                        ? "bg-slate-400 text-white"
                                        : rank === 3
                                          ? "bg-warning-600 text-white"
                                          : "bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-300"
                                  )}
                                >
                                  {rank}
                                </div>
                                <div className="min-w-0 flex-1">
                                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate flex items-center gap-1.5">
                                    {isPodium && <span>{medalFor(rank)}</span>}
                                    {entry.full_name || entry.username}
                                  </p>
                                  <p className="text-[10px] text-slate-400">
                                    {entry.qualifying_days} qualifying day{entry.qualifying_days !== 1 ? "s" : ""}
                                  </p>
                                </div>
                                <div className="text-right flex-shrink-0">
                                  <p className="text-sm font-bold text-slate-800 dark:text-slate-100">
                                    {entry.study_minutes} min
                                  </p>
                                  {entry.current_streak > 0 && (
                                    <p className="text-[10px] text-warning-600 dark:text-warning-400">
                                      🔥 {entry.current_streak} day streak
                                    </p>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Achievements Tab */}
                  {activeTab === "achievements" && (
                    <div className="p-4">
                      {loadingAchievements ? (
                        <div className="flex items-center justify-center py-12">
                          <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
                        </div>
                      ) : achievements.length === 0 ? (
                        <p className="text-center text-slate-400 py-12 text-sm">
                          No achievements earned yet. Keep studying!
                        </p>
                      ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {achievements.map((ach, idx) => (
                            <div
                              key={idx}
                              className="flex items-start gap-3 p-3.5 rounded-xl bg-gradient-to-br from-warning-50 to-primary-50/40 dark:from-warning-900/10 dark:to-primary-900/10 border border-warning-200/70 dark:border-warning-800/50"
                            >
                              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-warning-400 to-warning-600 flex items-center justify-center text-white text-lg flex-shrink-0 shadow-sm">
                                {ach.badge_type.includes("streak") ? "🔥" :
                                 ach.badge_type === "dedicated_learner" ? "📚" :
                                 ach.badge_type === "consistent_learner" ? "🎯" : "🏆"}
                              </div>
                              <div className="min-w-0">
                                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                                  {ach.badge_name}
                                </p>
                                <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
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
              ) : (
                <div className="card p-12 text-center space-y-3">
                  <div className="w-14 h-14 rounded-2xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center mx-auto">
                    <Users className="w-7 h-7 text-primary-400" />
                  </div>
                  <p className="font-semibold text-slate-700 dark:text-slate-200">Select a group</p>
                  <p className="text-xs text-slate-400">Choose a group from the list to view its chat and stats.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ---- Create Group Modal ---- */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="card p-6 max-w-lg w-full space-y-4 shadow-xl border-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-300">
                  <Users className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-lg text-slate-800 dark:text-slate-100">Create Study Group</h3>
                  <p className="text-xs text-slate-500">Start a group and invite your peers</p>
                </div>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="btn-ghost btn-sm"
                disabled={creatingGroup}
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {createError && (
              <p className="text-xs text-danger-600 bg-danger-50 dark:bg-danger-900/20 p-2.5 rounded-lg">{createError}</p>
            )}

            <form onSubmit={handleCreateGroup} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Group Name *</label>
                <input
                  value={groupName}
                  onChange={(e) => { setGroupName(e.target.value); setCreateError(""); }}
                  className="input"
                  placeholder="e.g. Data Structures Study Crew"
                  required
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">
                  Description <span className="text-slate-400 font-normal">(optional)</span>
                </label>
                <input
                  value={groupDescription}
                  onChange={(e) => setGroupDescription(e.target.value)}
                  className="input"
                  placeholder="What is this group about?"
                />
              </div>
              <div className="pt-1 flex gap-3">
                <button type="submit" disabled={creatingGroup} className="btn-primary btn-md flex-1">
                  {creatingGroup ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Creating…</>
                  ) : (
                    <><Plus className="w-4 h-4" /> Create Group</>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  disabled={creatingGroup}
                  className="btn-ghost btn-md"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ---- Join Group Modal ---- */}
      {showJoinModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="card p-6 max-w-lg w-full space-y-4 shadow-xl border-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-300">
                  <LogIn className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-lg text-slate-800 dark:text-slate-100">Join Study Group</h3>
                  <p className="text-xs text-slate-500">Enter an invite code shared by a group owner</p>
                </div>
              </div>
              <button
                onClick={() => setShowJoinModal(false)}
                className="btn-ghost btn-sm"
                disabled={joiningGroup}
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {joinError && (
              <p className="text-xs text-danger-600 bg-danger-50 dark:bg-danger-900/20 p-2.5 rounded-lg">{joinError}</p>
            )}
            {joinSuccess && (
              <p className="text-xs text-success-700 bg-success-50 dark:bg-success-900/20 p-2.5 rounded-lg">{joinSuccess}</p>
            )}

            <form onSubmit={handleJoinGroup} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Invite Code *</label>
                <div className="relative">
                  <Hash className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    value={inviteCode}
                    onChange={(e) => { setInviteCode(e.target.value); setJoinError(""); }}
                    className="input pl-10 font-mono"
                    placeholder="Paste invite code"
                    required
                    autoFocus
                  />
                </div>
              </div>
              <div className="pt-1 flex gap-3">
                <button type="submit" disabled={joiningGroup} className="btn-primary btn-md flex-1">
                  {joiningGroup ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Joining…</>
                  ) : (
                    <><LogIn className="w-4 h-4" /> Join Group</>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setShowJoinModal(false)}
                  disabled={joiningGroup}
                  className="btn-ghost btn-md"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
