import { useState, useEffect, useRef, useCallback } from "react";
import AppLayout from "@/components/layout/AppLayout";
import {
  Users, MessageSquare, Trophy, Award, Send, Loader2, Bot, User,
  Link2, Copy, RefreshCw, Trash2, Mail, UserPlus, X, Check, ChevronDown,
  Reply, Forward, Pencil, MoreVertical, CornerUpRight,
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { apiClient, getApiBase } from "@/lib/api";
import { cn } from "@/lib/utils";

type Tab = "chat" | "members" | "leaderboard" | "achievements";

interface OnlineStatus { [userId: number]: boolean; }
interface TypingStatus { [userId: number]: boolean; }

export default function StudyGroup() {
  const { user } = useAuthStore();

  // Group list state
  const [userGroups, setUserGroups] = useState<any[]>([]);
  const [currentGroup, setCurrentGroup] = useState<any>(null);
  const [currentGroupId, setCurrentGroupId] = useState("");

  // Create state
  const [groupName, setGroupName] = useState("");
  const [groupDescription, setGroupDescription] = useState("");
  const [creatingGroup, setCreatingGroup] = useState(false);
  const [createError, setCreateError] = useState("");
  const [deletingGroup, setDeletingGroup] = useState(false);

  // Tab state
  const [activeTab, setActiveTab] = useState<Tab>("chat");

  // Chat state
  const [messages, setMessages] = useState<any[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [sendingMessage, setSendingMessage] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);

  // Members state
  const [groupMembers, setGroupMembers] = useState<any[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);

  // Leaderboard / Achievements
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [loadingLeaderboard, setLoadingLeaderboard] = useState(false);
  const [achievements, setAchievements] = useState<any[]>([]);
  const [loadingAchievements, setLoadingAchievements] = useState(false);

  // Leave state
  const [leavingGroup, setLeavingGroup] = useState(false);

  // Group memory
  const [groupMemory, setGroupMemory] = useState<any>(null);

  // WebSocket
  const wsRef = useRef<WebSocket | null>(null);
  const [onlineUsers, setOnlineUsers] = useState<OnlineStatus>({});
  const [typingUsers, setTypingUsers] = useState<TypingStatus>({});
  const [wsConnected, setWsConnected] = useState(false);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isTypingRef = useRef(false);

  // Invitation
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteTab, setInviteTab] = useState<"username" | "email" | "link">("username");
  const [inviteUsername, setInviteUsername] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteResult, setInviteResult] = useState("");
  const [inviteLink, setInviteLink] = useState("");
  const [copiedLink, setCopiedLink] = useState(false);
  const [invitations, setInvitations] = useState<any[]>([]);
  const [showInvitations, setShowInvitations] = useState(false);

  // === Messenger-like features ===
  const [replyTo, setReplyTo] = useState<any>(null);
  const [editingMessage, setEditingMessage] = useState<any>(null);
  const [editContent, setEditContent] = useState("");
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; message: any } | null>(null);
  const [showForwardModal, setShowForwardModal] = useState(false);
  const [forwardMessage, setForwardMessage] = useState<any>(null);
  const [forwardTargetGroups, setForwardTargetGroups] = useState<number[]>([]);

  // ============================================================
  // Initial data load
  // ============================================================

  useEffect(() => { fetchUserGroups(); }, []);

  useEffect(() => {
    if (activeTab === "chat" && currentGroupId) fetchGroupMessages(currentGroupId);
    else if (activeTab === "members" && currentGroupId) fetchGroupMembers(currentGroupId);
    else if (activeTab === "leaderboard" && currentGroupId) fetchLeaderboard(currentGroupId);
    else if (activeTab === "achievements" && currentGroupId) fetchAchievements(currentGroupId);
  }, [activeTab, currentGroupId]);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  // Close context menu on outside click
  useEffect(() => {
    const handler = () => setContextMenu(null);
    if (contextMenu) document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, [contextMenu]);

  // ============================================================
  // WebSocket connection
  // ============================================================

  const connectWebSocket = useCallback((groupId: string) => {
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
    const tokens = localStorage.getItem("mentora_tokens");
    if (!tokens) return;
    let parsed: any;
    try { parsed = JSON.parse(tokens); } catch { return; }
    const accessToken = parsed.access_token;
    if (!accessToken) return;

    // Derive the WebSocket URL from the API base URL so it works in dev
    // (Vite on :5173 vs backend on :8000) and in production. VITE_WS_URL
    // takes precedence when explicitly configured.
    const apiUrl = getApiBase();
    const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    let wsUrl = import.meta.env.VITE_WS_URL;
    if (!wsUrl) {
      const host = apiUrl.replace(/^https?:\/\//, "").replace(/\/.*$/, "");
      wsUrl = `${wsScheme}://${host}`;
    }
    const ws = new WebSocket(`${wsUrl.replace(/\/$/, "")}/api/v1/study-groups/${groupId}/ws?token=${encodeURIComponent(accessToken)}`);
    wsRef.current = ws;

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => {
      setWsConnected(false);
      setTimeout(() => { if (currentGroupId === groupId) connectWebSocket(groupId); }, 3000);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (event) => {
      try { handleWsMessage(JSON.parse(event.data)); } catch (e) { console.error("WS parse error:", e); }
    };
  }, [currentGroupId]);

  const disconnectWebSocket = useCallback(() => {
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; setWsConnected(false); setOnlineUsers({}); setTypingUsers({}); }
  }, []);

  useEffect(() => {
    if (currentGroupId) connectWebSocket(currentGroupId);
    return () => disconnectWebSocket();
  }, [currentGroupId, connectWebSocket, disconnectWebSocket]);

  // ============================================================
  // WebSocket message handler
  // ============================================================

  const handleWsMessage = useCallback((msg: any) => {
    const { type, data } = msg;
    switch (type) {
      case "message":
        setMessages((prev) => {
          if (prev.some((m) => m.id === data.id)) return prev;
          return [...prev, normalizeWsMessage(data)];
        });
        break;
      case "ai_response":
        setMessages((prev) => {
          if (prev.some((m) => m.id === data.id)) return prev;
          return [...prev, normalizeWsMessage(data)];
        });
        break;
      case "message_edited":
        setMessages((prev) => prev.map((m) => m.id === data.id ? { ...m, ...normalizeWsMessage(data) } : m));
        break;
      case "message_deleted":
        setMessages((prev) => prev.map((m) => m.id === data.id ? { ...m, ...normalizeWsMessage(data) } : m));
        break;
      case "online_users": {
        const map: OnlineStatus = {};
        (data.user_ids || []).forEach((uid: number) => { map[uid] = true; });
        setOnlineUsers(map);
        break;
      }
      case "user_online": setOnlineUsers((prev) => ({ ...prev, [data.user_id]: true })); break;
      case "user_offline": setOnlineUsers((prev) => ({ ...prev, [data.user_id]: false })); setTypingUsers((prev) => ({ ...prev, [data.user_id]: false })); break;
      case "typing_start": setTypingUsers((prev) => ({ ...prev, [data.user_id]: true })); break;
      case "typing_stop": setTypingUsers((prev) => ({ ...prev, [data.user_id]: false })); break;
      case "error": console.error("WS error:", data.message); break;
    }
  }, []);

  const normalizeWsMessage = (data: any) => ({
    id: data.id,
    sender_id: data.sender?.id ?? data.sender_id,
    sender_name: data.sender?.full_name || data.sender?.username || data.sender_name,
    content: data.message || data.content,
    group_id: data.group_id,
    message_type: data.message_type,
    created_at: data.created_at,
    edited_at: data.edited_at || null,
    deleted_at: data.deleted_at || null,
    is_deleted: data.is_deleted || false,
    reply_to: data.reply_to || null,
    forwarded_from: data.forwarded_from || null,
  });

  // ============================================================
  // Data fetching
  // ============================================================

  const fetchUserGroups = async () => {
    try {
      const response = await apiClient.get("/api/v1/study-groups/");
      const unique = response.data.filter((g: any, i: number, self: any[]) => i === self.findIndex((x: any) => x.id === g.id));
      setUserGroups(unique);
      if (unique.length > 0 && !currentGroupId) selectGroup(unique[0].id);
    } catch (error) { console.error("Failed to fetch groups:", error); }
  };

  const selectGroup = async (groupId: string) => {
    try {
      setCurrentGroup(null); setCurrentGroupId(groupId); setActiveTab("chat"); setMessages([]); setHasMore(true);
      const response = await apiClient.get(`/api/v1/study-groups/${groupId}`);
      setCurrentGroup(response.data);
      await fetchGroupMessages(groupId); await fetchGroupMembers(groupId); fetchGroupMemory(groupId);
    } catch (error) { console.error("Failed to fetch group detail:", error); }
  };

  const fetchGroupMemory = async (groupId: string) => { try { const r = await apiClient.get(`/api/v1/study-groups/${groupId}/memory`); setGroupMemory(r.data.memory); } catch { setGroupMemory(null); } };
  const fetchGroupMessages = async (groupId: string, before?: number) => {
    try {
      const url = before ? `/api/v1/study-groups/${groupId}/messages?limit=50&before=${before}` : `/api/v1/study-groups/${groupId}/messages?limit=50`;
      const r = await apiClient.get(url);
      if (before) { setMessages((prev) => { const ids = new Set(prev.map((m) => m.id)); return [...r.data.filter((m: any) => !ids.has(m.id)), ...prev]; }); }
      else setMessages(r.data);
      setHasMore(r.data.length === 50);
    } catch (error) { console.error("Failed to fetch messages:", error); }
  };
  const loadMoreMessages = async () => { if (!currentGroupId || loadingMore || !hasMore || messages.length === 0) return; setLoadingMore(true); await fetchGroupMessages(currentGroupId, messages[0]?.id); setLoadingMore(false); };
  const fetchGroupMembers = async (groupId: string) => { setLoadingMembers(true); try { const r = await apiClient.get(`/api/v1/study-groups/${groupId}/members`); setGroupMembers(r.data); } catch { } finally { setLoadingMembers(false); } };
  const fetchLeaderboard = async (groupId: string) => { setLoadingLeaderboard(true); try { const r = await apiClient.get(`/api/v1/study-groups/${groupId}/leaderboard?days=7`); setLeaderboard(r.data); } catch { } finally { setLoadingLeaderboard(false); } };
  const fetchAchievements = async (groupId: string) => { setLoadingAchievements(true); try { const r = await apiClient.get(`/api/v1/study-groups/${groupId}/achievements`); setAchievements(r.data); } catch { } finally { setLoadingAchievements(false); } };
  const fetchInvitations = async () => { try { const r = await apiClient.get("/api/v1/study-groups/invitations"); setInvitations(r.data); } catch { } };

  // ============================================================
  // Message actions
  // ============================================================

  const handleSendMessage = () => {
    if (!newMessage.trim() || !currentGroupId || !wsRef.current) return;
    const payload: any = { type: "message", content: newMessage.trim() };
    if (replyTo) { payload.reply_to_message_id = replyTo.id; setReplyTo(null); }
    wsRef.current.send(JSON.stringify(payload));
    setNewMessage(""); stopTyping();
  };

  const handleEditMessage = () => {
    if (!editingMessage || !editContent.trim() || !wsRef.current) return;
    wsRef.current.send(JSON.stringify({ type: "edit_message", message_id: editingMessage.id, content: editContent.trim() }));
    setEditingMessage(null); setEditContent("");
  };

  const handleDeleteMessage = (msgId: number) => {
    if (!wsRef.current) return;
    wsRef.current.send(JSON.stringify({ type: "delete_message", message_id: msgId }));
    setContextMenu(null);
  };

  const handleForwardMessage = async () => {
    if (!forwardMessage || forwardTargetGroups.length === 0) return;
    try {
      await apiClient.post(`/api/v1/study-groups/${forwardMessage.group_id}/messages/${forwardMessage.id}/forward`, {
        target_group_ids: forwardTargetGroups,
      });
      setShowForwardModal(false); setForwardMessage(null); setForwardTargetGroups([]);
    } catch (err) { console.error("Forward failed:", err); }
  };

  // ============================================================
  // Typing indicator
  // ============================================================

  const startTyping = useCallback(() => { if (!isTypingRef.current && wsRef.current) { isTypingRef.current = true; wsRef.current.send(JSON.stringify({ type: "typing_start" })); } }, []);
  const stopTyping = useCallback(() => { 
    if (isTypingRef.current && wsRef.current) { 
      isTypingRef.current = false; 
      wsRef.current.send(JSON.stringify({ type: "typing_stop" })); 
    } 
    if (typingTimeoutRef.current) { clearTimeout(typingTimeoutRef.current); typingTimeoutRef.current = null; } 
  }, []);
  const handleMessageInput = (value: string) => {
    setNewMessage(value);
    if (value.trim()) { 
      startTyping(); 
      if (typingTimeoutRef.current) { clearTimeout(typingTimeoutRef.current); typingTimeoutRef.current = null; } 
      typingTimeoutRef.current = setTimeout(() => { stopTyping(); isTypingRef.current = false; }, 2000); 
    } else { 
      stopTyping(); 
    }
  };

  // ============================================================
  // Group actions
  // ============================================================

  const handleCreateGroup = async (e: React.FormEvent) => {
    e.preventDefault(); setCreatingGroup(true); setCreateError("");
    try { await apiClient.post("/api/v1/study-groups", { name: groupName, description: groupDescription }); setGroupName(""); setGroupDescription(""); setCreatingGroup(false); const g = await apiClient.get("/api/v1/study-groups/"); const u = g.data.filter((x: any, i: number, s: any[]) => i === s.findIndex((y: any) => y.id === x.id)); setUserGroups(u); if (u.length > 0) selectGroup(u[u.length - 1].id); } catch (err: any) { setCreateError(err?.response?.data?.detail || "Failed to create group."); setCreatingGroup(false); }
  };

  const handleLeaveGroup = async () => { if (!currentGroupId) return; setLeavingGroup(true); try { disconnectWebSocket(); await apiClient.post(`/api/v1/study-groups/${currentGroupId}/leave`); setCurrentGroup(null); setCurrentGroupId(""); fetchUserGroups(); } catch { } finally { setLeavingGroup(false); } };
  const handleDeleteGroup = async () => { if (!currentGroupId) return; if (!window.confirm("Delete this group? This cannot be undone.")) return; setDeletingGroup(true); try { disconnectWebSocket(); await apiClient.delete(`/api/v1/study-groups/${currentGroupId}`); setCurrentGroup(null); setCurrentGroupId(""); fetchUserGroups(); } catch { } finally { setDeletingGroup(false); } };

  // ============================================================
  // Invitation actions
  // ============================================================

  const handleInviteByUsername = async () => { if (!inviteUsername.trim() || !currentGroupId) return; setInviteLoading(true); setInviteResult(""); try { await apiClient.post(`/api/v1/study-groups/${currentGroupId}/invitations/by-username`, { username: inviteUsername.trim() }); setInviteResult("Invitation sent!"); setInviteUsername(""); } catch (err: any) { setInviteResult(err?.response?.data?.detail || "Failed."); } finally { setInviteLoading(false); } };
  const handleInviteByEmail = async () => { if (!inviteEmail.trim() || !currentGroupId) return; setInviteLoading(true); setInviteResult(""); try { await apiClient.post(`/api/v1/study-groups/${currentGroupId}/invitations/by-email`, { email: inviteEmail.trim() }); setInviteResult("Invitation sent!"); setInviteEmail(""); } catch (err: any) { setInviteResult(err?.response?.data?.detail || "Failed."); } finally { setInviteLoading(false); } };
  const handleGetInviteLink = async () => { if (!currentGroupId) return; setInviteLoading(true); try { const r = await apiClient.post(`/api/v1/study-groups/${currentGroupId}/invite-link`); setInviteLink(r.data.link); } catch (err: any) { setInviteResult(err?.response?.data?.detail || "Failed."); } finally { setInviteLoading(false); } };
  const handleCopyLink = () => { if (inviteLink) { navigator.clipboard.writeText(inviteLink); setCopiedLink(true); setTimeout(() => setCopiedLink(false), 2000); } };
  const handleRegenerateLink = async () => { if (!currentGroupId) return; setInviteLoading(true); try { const r = await apiClient.post(`/api/v1/study-groups/${currentGroupId}/invite-link/regenerate`); setInviteLink(r.data.link); } catch { } finally { setInviteLoading(false); } };
  const handleAcceptInvitation = async (id: number) => { try { await apiClient.post(`/api/v1/study-groups/invitations/${id}/accept`); fetchInvitations(); fetchUserGroups(); } catch { } };
  const handleDeclineInvitation = async (id: number) => { try { await apiClient.post(`/api/v1/study-groups/invitations/${id}/decline`); fetchInvitations(); } catch { } };

  // ============================================================
  // Helpers
  // ============================================================

  const getMemberName = (msg: any) => msg.message_type === "ai" ? "Mentora AI" : msg.sender_name || "Unknown";
  const isAiMessage = (msg: any) => msg.message_type === "ai";
  const isOnline = (userId: number) => onlineUsers[userId] === true;
  const onlineCount = Object.values(onlineUsers).filter(Boolean).length;
  const getTypingIndicatorText = () => {
    const typingIds = Object.entries(typingUsers).filter(([, t]) => t).map(([uid]) => parseInt(uid));
    if (typingIds.length === 0) return null;
    const names = typingIds.map((uid) => { const m = groupMembers.find((m) => m.user_id === uid); return m?.user?.full_name || m?.user?.username || "Someone"; });
    if (names.length === 1) return `${names[0]} is typing...`;
    if (names.length === 2) return `${names[0]} and ${names[1]} are typing...`;
    return `${names[0]} and ${names.length - 1} others are typing...`;
  };

  const isOwnMessage = (msg: any) => msg.sender_id === user?.id;

  // Anyone can delete a message (removed for everyone, like Messenger);
  // only the sender can edit their own messages.
  const canDelete = (msg: any) => !msg.is_deleted && msg.message_type !== "ai";
  const canEdit = (msg: any) => canDelete(msg) && isOwnMessage(msg);

  const handleContextMenu = (e: React.MouseEvent, msg: any) => {
    e.preventDefault();
    if (msg.is_deleted) return;
    setContextMenu({ x: e.clientX, y: e.clientY, message: msg });
  };

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <AppLayout title="Study Groups">
      <div className="space-y-4">
        {/* Create Group */}
        <div className="border rounded-lg p-4 bg-white dark:bg-slate-800">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Create Study Group</h2>
          <form onSubmit={handleCreateGroup}>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <input value={groupName} onChange={(e) => setGroupName(e.target.value)} className="w-full rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500" placeholder="Group name" required />
              <input value={groupDescription} onChange={(e) => setGroupDescription(e.target.value)} className="w-full rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500" placeholder="Description (optional)" />
            </div>
            <button type="submit" disabled={creatingGroup} className="w-full mt-3 py-2 rounded-md text-sm font-medium bg-primary-600 text-white hover:bg-primary-500 disabled:opacity-50">{creatingGroup ? "Creating..." : "Create Group"}</button>
            {createError && <p className="mt-2 text-sm text-red-600">{createError}</p>}
          </form>
        </div>

        {/* Group Chips */}
        {userGroups.length > 0 && (
          <div className="flex gap-2 overflow-x-auto pb-2">
            {userGroups.map((group) => (
              <button key={group.id} onClick={() => selectGroup(group.id)} className={cn("px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors", currentGroupId === group.id ? "bg-primary-600 text-white shadow-md" : "bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-50")}>{group.name}</button>
            ))}
          </div>
        )}

        {/* Group Detail */}
        {currentGroup && (
          <div className="border rounded-lg bg-white dark:bg-slate-800">
            {/* Header */}
            <div className="p-4 border-b border-slate-200 dark:border-slate-700">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h2 className="text-xl font-semibold text-slate-800 dark:text-slate-100">{currentGroup.name}</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    {groupMembers.length} members{onlineCount > 0 && ` · ${onlineCount} online`}{wsConnected && <span className="ml-1 inline-block w-1.5 h-1.5 rounded-full bg-green-500" />}
                    {currentGroup.description && ` — ${currentGroup.description}`}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => { setShowInviteModal(true); setInviteLink(""); setInviteResult(""); }} className="px-3 py-1.5 rounded-md text-xs font-medium bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 flex items-center gap-1"><UserPlus className="w-3 h-3" /> Invite</button>
                  <button onClick={() => { setShowInvitations(!showInvitations); fetchInvitations(); }} className="px-3 py-1.5 rounded-md text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 flex items-center gap-1"><Mail className="w-3 h-3" /> Invitations</button>
                  {currentGroup.owner_id === user?.id && <button onClick={handleDeleteGroup} disabled={deletingGroup} className="px-3 py-1.5 rounded-md text-xs font-medium bg-red-700 text-white hover:bg-red-600 disabled:opacity-50">{deletingGroup ? "Deleting..." : "Delete"}</button>}
                  <button onClick={handleLeaveGroup} disabled={leavingGroup} className="px-3 py-1.5 rounded-md text-xs font-medium bg-red-600 text-white hover:bg-red-500 disabled:opacity-50">{leavingGroup ? "Leaving..." : "Leave"}</button>
                </div>
              </div>
            </div>

            {/* Invitations Panel */}
            {showInvitations && (
              <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/30">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-slate-800 dark:text-slate-100">Pending Invitations</h3>
                  <button onClick={() => setShowInvitations(false)} className="text-slate-400 hover:text-slate-600"><X className="w-4 h-4" /></button>
                </div>
                {invitations.filter((i) => i.status === "pending").length === 0 ? <p className="text-xs text-slate-400">No pending invitations.</p> : (
                  <div className="space-y-2">
                    {invitations.filter((i) => i.status === "pending").map((inv) => (
                      <div key={inv.id} className="flex items-center justify-between p-2 rounded bg-white dark:bg-slate-800">
                        <div><p className="text-xs font-medium text-slate-800 dark:text-slate-100">{inv.group_name || `Group #${inv.group_id}`}</p><p className="text-[10px] text-slate-400">{inv.inviter_name ? `From ${inv.inviter_name}` : inv.invited_email || `User #${inv.invited_user_id}`}</p></div>
                        {inv.invited_user_id === user?.id && <div className="flex gap-1"><button onClick={() => handleAcceptInvitation(inv.id)} className="px-2 py-1 rounded text-[10px] font-medium bg-green-600 text-white hover:bg-green-500">Accept</button><button onClick={() => handleDeclineInvitation(inv.id)} className="px-2 py-1 rounded text-[10px] font-medium bg-red-600 text-white hover:bg-red-500">Decline</button></div>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Tabs */}
            <div className="flex border-b border-slate-200 dark:border-slate-700">
              {([ { key: "chat", label: "Chat", icon: MessageSquare }, { key: "members", label: "Members", icon: Users }, { key: "leaderboard", label: "Leaderboard", icon: Trophy }, { key: "achievements", label: "Achievements", icon: Award } ] as const).map(({ key, label, icon: Icon }) => (
                <button key={key} onClick={() => setActiveTab(key)} className={cn("flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors", activeTab === key ? "border-primary-600 text-primary-600 dark:text-primary-400 dark:border-primary-400" : "border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300")}><Icon className="w-4 h-4" />{label}</button>
              ))}
            </div>

            {/* ======================== CHAT TAB ======================== */}
            {activeTab === "chat" && (
              <div className="flex flex-col" style={{ height: "500px" }}>
                <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-4 space-y-1">
                  {hasMore && messages.length > 0 && (
                    <button onClick={loadMoreMessages} disabled={loadingMore} className="w-full text-center text-xs text-slate-400 hover:text-slate-600 py-2">
                      {loadingMore ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : "Load older messages"}
                    </button>
                  )}
                  {messages.length === 0 && (
                    <div className="text-center text-slate-400 dark:text-slate-500 py-8">
                      <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">No messages yet. Start the conversation!</p>
                      <p className="text-xs mt-1">Type /mentora followed by your question to ask Mentora</p>
                    </div>
                  )}
                  {messages.map((msg) => (
                    <MessageBubble
                      key={msg.id}
                      msg={msg}
                      user={user}
                      onReply={() => setReplyTo(msg)}
                      onEdit={() => { setEditingMessage(msg); setEditContent(msg.content); setContextMenu(null); }}
                      onDelete={() => handleDeleteMessage(msg.id)}
                      onForward={() => { setForwardMessage(msg); setShowForwardModal(true); setContextMenu(null); }}
                      onContextMenu={(e) => handleContextMenu(e, msg)}
                      editingMessage={editingMessage}
                      editContent={editContent}
                      setEditContent={setEditContent}
                      handleEditMessage={handleEditMessage}
                      cancelEdit={() => { setEditingMessage(null); setEditContent(""); }}
                      isOwn={isOwnMessage(msg)}
                      isAi={isAiMessage(msg)}
                    />
                  ))}
                  {getTypingIndicatorText() && (
                    <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500 pl-9">
                      <div className="flex gap-1"><span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "0ms" }} /><span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "150ms" }} /><span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "300ms" }} /></div>
                      {getTypingIndicatorText()}
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {/* Reply preview */}
                {replyTo && (
                  <div className="px-4 py-2 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/50 flex items-center gap-2">
                    <Reply className="w-4 h-4 text-primary-500 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-[10px] font-medium text-primary-600 dark:text-primary-400">Replying to {replyTo.sender_name || "Unknown"}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{replyTo.content}</p>
                    </div>
                    <button onClick={() => setReplyTo(null)} className="text-slate-400 hover:text-slate-600"><X className="w-4 h-4" /></button>
                  </div>
                )}

                {/* Chat Input */}
                <div className="p-3 border-t border-slate-200 dark:border-slate-700">
                  <div className="flex items-center justify-between mb-1.5">
                    <p className="text-[10px] text-slate-400 dark:text-slate-500">Type /mentora followed by your question to ask Mentora</p>
                    {groupMemory && Object.keys(groupMemory).length > 0 && <p className="text-[10px] text-purple-500 dark:text-purple-400">Mentora is using group learning context</p>}
                  </div>
                  <div className="flex gap-2">
                    <input
                      value={newMessage}
                      onChange={(e) => handleMessageInput(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSendMessage(); } }}
                      className="flex-1 rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder={replyTo ? `Reply to ${replyTo.sender_name || "Unknown"}...` : "Type a message..."}
                      disabled={!wsConnected}
                    />
                    <button onClick={handleSendMessage} disabled={!newMessage.trim() || !wsConnected} className="px-4 py-2 rounded-md bg-primary-600 text-white hover:bg-primary-500 disabled:opacity-50">
                      {sendingMessage ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* ======================== MEMBERS TAB ======================== */}
            {activeTab === "members" && (
              <div className="p-4">
                {loadingMembers ? <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-primary-500" /></div>
                  : groupMembers.length === 0 ? <p className="text-center text-slate-400 py-8">No members yet.</p>
                  : <div className="space-y-2">{groupMembers.map((member) => (
                    <div key={member.id} className="flex items-center gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50">
                      <div className="relative">
                        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white text-sm font-bold">{member.user?.full_name ? member.user.full_name[0].toUpperCase() : member.user?.username?.[0]?.toUpperCase() ?? "U"}</div>
                        <div className={cn("absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white dark:border-slate-700", isOnline(member.user_id) ? "bg-green-500" : "bg-slate-300 dark:bg-slate-600")} />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-slate-800 dark:text-slate-100">{member.user?.full_name || member.user?.username}{member.user_id === user?.id && <span className="text-[10px] text-slate-400 ml-1">(you)</span>}</p>
                        <p className="text-[10px] text-slate-400">{member.user?.username}</p>
                      </div>
                      <span className={cn("px-2 py-0.5 rounded-full text-[10px] font-medium", member.role === "admin" ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400")}>{member.role === "admin" ? "Admin" : "Member"}</span>
                    </div>
                  ))}</div>
              }
              </div>
            )}

            {/* ======================== LEADERBOARD TAB ======================== */}
            {activeTab === "leaderboard" && (
              <div className="p-4">
                {loadingLeaderboard ? <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-primary-500" /></div>
                  : leaderboard.length === 0 ? <p className="text-center text-slate-400 py-8">No study data yet.</p>
                  : <div className="space-y-2">{leaderboard.map((e) => (
                    <div key={e.user_id} className={cn("flex items-center gap-3 p-3 rounded-lg", e.rank === 1 ? "bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800" : "bg-slate-50 dark:bg-slate-700/30")}>
                      <div className={cn("w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold", e.rank === 1 ? "bg-amber-400 text-white" : e.rank === 2 ? "bg-slate-400 text-white" : e.rank === 3 ? "bg-amber-600 text-white" : "bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300")}>{e.rank}</div>
                      <div className="flex-1"><p className="text-sm font-medium text-slate-800 dark:text-slate-100">{e.full_name || e.username}</p><p className="text-[10px] text-slate-400">{e.qualifying_days} qualifying days</p></div>
                      <div className="text-right"><p className="text-sm font-bold text-slate-800 dark:text-slate-100">{e.study_minutes} min</p>{e.current_streak > 0 && <p className="text-[10px] text-orange-500">{e.current_streak} day streak</p>}</div>
                    </div>
                  ))}</div>
              }
              </div>
            )}

            {/* ======================== ACHIEVEMENTS TAB ======================== */}
            {activeTab === "achievements" && (
              <div className="p-4">
                {loadingAchievements ? <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-primary-500" /></div>
                  : achievements.length === 0 ? <p className="text-center text-slate-400 py-8">No achievements earned yet. Keep studying!</p>
                  : <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">{achievements.map((ach, idx) => (
                    <div key={idx} className="flex items-start gap-3 p-3 rounded-lg bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/10 dark:to-orange-900/10 border border-amber-200 dark:border-amber-800">
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white text-lg flex-shrink-0">{ach.badge_type.includes("streak") ? "" : ach.badge_type === "dedicated_learner" ? "" : ""}</div>
                      <div><p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{ach.badge_name}</p><p className="text-[10px] text-slate-500 dark:text-slate-400">{ach.full_name || ach.username}</p><p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">{ach.description}</p></div>
                    </div>
                  ))}</div>
              }
              </div>
            )}
          </div>
        )}

        {/* No group selected */}
        {!currentGroup && userGroups.length === 0 && (
          <div className="text-center py-12 text-slate-400 dark:text-slate-500">
            <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-lg font-medium">No study groups yet</p>
            <p className="text-sm mt-1">Create a group or join one with an invitation link</p>
          </div>
        )}

        {/* ======================== CONTEXT MENU ======================== */}
        {contextMenu && (
          <div
            className="fixed z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg py-1 min-w-[160px]"
            style={{ left: Math.min(contextMenu.x, window.innerWidth - 180), top: Math.min(contextMenu.y, window.innerHeight - 200) }}
          >
            <button onClick={() => { setReplyTo(contextMenu.message); setContextMenu(null); }} className="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2"><Reply className="w-4 h-4" /> Reply</button>
            {canEdit(contextMenu.message) && (
              <button onClick={() => { setEditingMessage(contextMenu.message); setEditContent(contextMenu.message.content); setContextMenu(null); }} className="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2"><Pencil className="w-4 h-4" /> Edit</button>
            )}
            <button onClick={() => { setForwardMessage(contextMenu.message); setShowForwardModal(true); setContextMenu(null); }} className="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2"><Forward className="w-4 h-4" /> Forward</button>
            {canDelete(contextMenu.message) && (
              <button onClick={() => handleDeleteMessage(contextMenu.message.id)} className="w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2"><Trash2 className="w-4 h-4" /> Delete for everyone</button>
            )}
          </div>
        )}

        {/* ======================== INVITE MODAL ======================== */}
        {showInviteModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowInviteModal(false)}>
            <div className="bg-white dark:bg-slate-800 rounded-lg p-6 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4"><h3 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Invite Members</h3><button onClick={() => setShowInviteModal(false)} className="text-slate-400 hover:text-slate-600"><X className="w-5 h-5" /></button></div>
              <div className="flex gap-1 mb-4 bg-slate-100 dark:bg-slate-700 rounded-md p-1">
                {(["username", "email", "link"] as const).map((tab) => (
                  <button key={tab} onClick={() => setInviteTab(tab)} className={cn("flex-1 py-1.5 rounded text-xs font-medium transition-colors", inviteTab === tab ? "bg-white dark:bg-slate-600 text-slate-800 dark:text-slate-100 shadow" : "text-slate-500 dark:text-slate-400")}>{tab === "username" ? "Username" : tab === "email" ? "Email" : "Link"}</button>
                ))}
              </div>
              {inviteTab === "username" && <div><label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Search by username</label><div className="flex gap-2"><input value={inviteUsername} onChange={(e) => setInviteUsername(e.target.value)} className="flex-1 rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500" placeholder="e.g. saroj" /><button onClick={handleInviteByUsername} disabled={inviteLoading || !inviteUsername.trim()} className="px-4 py-2 rounded-md text-sm font-medium bg-primary-600 text-white hover:bg-primary-500 disabled:opacity-50">{inviteLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Invite"}</button></div></div>}
              {inviteTab === "email" && <div><label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Invite by email</label><div className="flex gap-2"><input type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} className="flex-1 rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500" placeholder="user@example.com" /><button onClick={handleInviteByEmail} disabled={inviteLoading || !inviteEmail.trim()} className="px-4 py-2 rounded-md text-sm font-medium bg-primary-600 text-white hover:bg-primary-500 disabled:opacity-50">{inviteLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Invite"}</button></div></div>}
              {inviteTab === "link" && <div><p className="text-xs text-slate-500 dark:text-slate-400 mb-3">Share this link to let anyone join the group.</p>{!inviteLink ? <button onClick={handleGetInviteLink} disabled={inviteLoading} className="w-full py-2 rounded-md text-sm font-medium bg-primary-600 text-white hover:bg-primary-500 disabled:opacity-50 flex items-center justify-center gap-2">{inviteLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Link2 className="w-4 h-4" />} Generate Link</button> : <div><div className="flex gap-2"><input value={inviteLink} readOnly className="flex-1 rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 px-3 py-2 text-xs font-mono focus:outline-none" /><button onClick={handleCopyLink} className="px-3 py-2 rounded-md text-sm font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 flex items-center gap-1">{copiedLink ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}</button></div><button onClick={handleRegenerateLink} disabled={inviteLoading} className="mt-2 w-full py-1.5 rounded text-xs font-medium text-slate-500 hover:text-slate-700 flex items-center justify-center gap-1"><RefreshCw className="w-3 h-3" /> Regenerate Link</button></div>}</div>}
              {inviteResult && <p className={cn("mt-3 text-xs", inviteResult.includes("success") || inviteResult.includes("sent") ? "text-green-600" : "text-red-600")}>{inviteResult}</p>}
            </div>
          </div>
        )}

        {/* ======================== FORWARD MODAL ======================== */}
        {showForwardModal && forwardMessage && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowForwardModal(false)}>
            <div className="bg-white dark:bg-slate-800 rounded-lg p-6 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Forward Message</h3>
                <button onClick={() => setShowForwardModal(false)} className="text-slate-400 hover:text-slate-600"><X className="w-5 h-5" /></button>
              </div>
              <div className="p-3 rounded bg-slate-50 dark:bg-slate-700/50 mb-4">
                <p className="text-[10px] text-slate-400">{forwardMessage.sender_name}</p>
                <p className="text-xs text-slate-600 dark:text-slate-300 truncate">{forwardMessage.content}</p>
              </div>
              <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">Select groups to forward to:</p>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {userGroups.filter((g) => g.id !== forwardMessage.group_id).map((g) => (
                  <label key={g.id} className="flex items-center gap-2 p-2 rounded hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={forwardTargetGroups.includes(g.id)}
                      onChange={(e) => setForwardTargetGroups((prev) => e.target.checked ? [...prev, g.id] : prev.filter((id) => id !== g.id))}
                      className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-sm text-slate-800 dark:text-slate-100">{g.name}</span>
                  </label>
                ))}
              </div>
              <div className="flex gap-2 mt-4">
                <button onClick={() => setShowForwardModal(false)} className="flex-1 py-2 rounded-md text-sm font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200">Cancel</button>
                <button onClick={handleForwardMessage} disabled={forwardTargetGroups.length === 0} className="flex-1 py-2 rounded-md text-sm font-medium bg-primary-600 text-white hover:bg-primary-500 disabled:opacity-50 flex items-center justify-center gap-1"><Forward className="w-4 h-4" /> Forward ({forwardTargetGroups.length})</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}

// ============================================================
// MessageBubble Component
// ============================================================

function MessageBubble({ msg, user, onReply, onEdit, onDelete, onForward, onContextMenu, editingMessage, editContent, setEditContent, handleEditMessage, cancelEdit, isOwn, isAi }: {
  msg: any; user: any; onReply: () => void; onEdit: () => void; onDelete: () => void; onForward: () => void;
  onContextMenu: (e: React.MouseEvent) => void; editingMessage: any; editContent: string; setEditContent: (v: string) => void;
  handleEditMessage: () => void; cancelEdit: () => void; isOwn: boolean; isAi: boolean;
}) {
  const isEditing = editingMessage?.id === msg.id;

  return (
    <div
      className={cn("flex gap-2 group relative", isOwn ? "justify-end" : "justify-start")}
      onContextMenu={onContextMenu}
    >
      {!isOwn && (
        <div className={cn("w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-1", isAi ? "bg-gradient-to-br from-purple-500 to-blue-500 text-white" : "bg-gradient-to-br from-primary-500 to-secondary-500 text-white")}>
          {isAi ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
        </div>
      )}
      <div className={cn("max-w-[75%]", isOwn ? "text-right" : "")}>
        {!isOwn && <p className="text-[10px] text-slate-400 dark:text-slate-500 mb-0.5">{msg.sender_name || "Unknown"}</p>}

        {/* Reply-to preview */}
        {msg.reply_to && (
          <div className={cn("rounded-t-lg px-3 py-1.5 text-[10px] border-b-0", isOwn ? "bg-primary-700 text-primary-100" : "bg-slate-200 dark:bg-slate-600 text-slate-500 dark:text-slate-400")}>
            <p className="font-medium">{msg.reply_to.sender_name || "Unknown"}</p>
            <p className="truncate opacity-75">{msg.reply_to.content}</p>
          </div>
        )}

        {/* Forwarded-from indicator */}
        {msg.forwarded_from && (
          <div className={cn("rounded-t-lg px-3 py-1 text-[10px] flex items-center gap-1", isOwn ? "bg-primary-700 text-primary-100" : "bg-slate-200 dark:bg-slate-600 text-slate-500 dark:text-slate-400")}>
            <CornerUpRight className="w-3 h-3" />
            <span>Forwarded{msg.forwarded_from.sender_name ? ` from ${msg.forwarded_from.sender_name}` : ""}</span>
          </div>
        )}

        {/* Message content */}
        {isEditing ? (
          <div className="rounded-lg bg-white dark:bg-slate-800 border border-primary-300 dark:border-primary-700 p-2">
            <input
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleEditMessage(); } if (e.key === "Escape") cancelEdit(); }}
              className="w-full bg-transparent text-sm text-slate-800 dark:text-slate-100 focus:outline-none"
              autoFocus
            />
            <div className="flex justify-end gap-1 mt-1">
              <button onClick={cancelEdit} className="text-[10px] px-2 py-0.5 rounded text-slate-400 hover:text-slate-600">Cancel</button>
              <button onClick={handleEditMessage} className="text-[10px] px-2 py-0.5 rounded bg-primary-600 text-white hover:bg-primary-500">Save</button>
            </div>
          </div>
        ) : (
          <div className={cn("rounded-lg px-3 py-2 text-sm", isAi ? "bg-purple-50 dark:bg-purple-900/20 text-slate-800 dark:text-slate-100 border border-purple-200 dark:border-purple-800" : isOwn ? "bg-primary-600 text-white" : "bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100")}>
            {msg.is_deleted ? (
              <p className="italic opacity-60">{msg.content}</p>
            ) : (
              <p className="whitespace-pre-wrap">{msg.content}</p>
            )}
          </div>
        )}

        {/* Timestamp + edited indicator */}
        <div className="flex items-center gap-1 mt-0.5">
          <p className="text-[10px] text-slate-400 dark:text-slate-500">
            {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </p>
          {msg.edited_at && !msg.is_deleted && <p className="text-[10px] text-slate-400 dark:text-slate-500 italic">(edited)</p>}
        </div>

        {/* Hover actions */}
        {!msg.is_deleted && !isEditing && (
          <div className="hidden group-hover:flex items-center gap-1 mt-0.5">
            <button onClick={onReply} className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"><Reply className="w-3 h-3" /></button>
            <button onClick={onForward} className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"><Forward className="w-3 h-3" /></button>
            {isOwn && <button onClick={onEdit} className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"><Pencil className="w-3 h-3" /></button>}
            <button onClick={onDelete} className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-slate-400 hover:text-red-600"><Trash2 className="w-3 h-3" /></button>
          </div>
        )}
      </div>
    </div>
  );
}
