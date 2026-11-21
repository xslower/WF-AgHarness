
import { useCallback, useEffect, useMemo, useRef, useSyncExternalStore } from "react";
import type { ApprovalItem, SessionDetail, TodoItem } from "../../api";
import type { DebugLog } from "./chatStorage";
import { IDLE_PLAN, type SessionStreamState } from "./chatEvents";
import { chatCtl, type TurnContext } from "./chatController";
import { clearAttentionFocus, setAttentionFocus } from "../../attention/focus";
import { streamStore } from "./sessionStore";
import { readPolicyPref, readPrefs } from "../../chat/sessionPrefs";
import { normalizeSpec } from "../../model/modelSpec";
import type { ChatStream, ChatStreamOptions, SendOptions } from "./chatTypes";

export type { LiveEvent, PlanState, SubAgent, SessionStreamState } from "./chatEvents";
export type { DebugLog } from "./chatStorage";
export type { TodoItem } from "../../api/types";
export type { ChatStream, ChatStreamOptions, SendOptions } from "./chatTypes";


function useSessionState(sid: string | null): SessionStreamState {
  const key = sid ?? "";
  const subscribe = useCallback(
    (cb: () => void) => streamStore.subscribe(key, cb), [key]);
  const getSnapshot = useCallback(() => streamStore.get(key), [key]);
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

export function useChatStream(options: ChatStreamOptions): ChatStream {
  const sid = options.sessionId;
  const state = useSessionState(sid);

  
  const ctxOf = () => ({
    sid, project: options.project,
    model: normalizeSpec(readPrefs(sid).model),
    policy: readPolicyPref(sid),
    sessionMeta: options.sessionMeta, onSessionCreated: options.setSessionId,
  });
  const ctxRef = useRef<TurnContext>(ctxOf());
  ctxRef.current = ctxOf();

  
  useEffect(() => {
    return chatCtl.onSessionsChanged(() => { void options.refreshSessions(); });
    
  }, []);

  useEffect(() => {
    chatCtl.setNotifyOnDone(options.notifyOnDone);
  }, [options.notifyOnDone]);

  
  
  
  
  useEffect(() => {
    if (sid) chatCtl.setFocus(sid);
  }, [sid]);

  
  
  useEffect(() => {
    if (!sid) return;
    setAttentionFocus(sid);
    return () => clearAttentionFocus(sid);
  }, [sid]);

  const actions = useMemo(() => ({
    send: (body: string, o: SendOptions = {}) => chatCtl.send(ctxRef.current, body, o),
    stop: () => chatCtl.stop(ctxRef.current.sid),
    queueAction: (action: "remove" | "interject" | "cancel_interject", id: string) =>
      chatCtl.queueAction(ctxRef.current.sid, action, id),
    sendPlanDecision: (decision: string, feedback?: string, plan?: string) =>
      chatCtl.sendPlanDecision(ctxRef.current.sid, decision, feedback, plan),
    removeApproval: (id: string) => chatCtl.removeApproval(ctxRef.current.sid, id),
    clearDebugLogs: () => chatCtl.clearDebugLogs(ctxRef.current.sid),
    setActiveSubAgent: (id: string | null) => chatCtl.setActiveSubAgent(ctxRef.current.sid, id),
    querySubAgent: (id: string) => chatCtl.querySubAgent(ctxRef.current.sid, id),
    messageSubAgent: (id: string, text: string) =>
      chatCtl.messageSubAgent(ctxRef.current.sid, id, text),
    stopSubAgent: (id: string) => chatCtl.stopSubAgent(ctxRef.current.sid, id),
    editFrom: (index: number) => chatCtl.editFrom(ctxRef.current.sid, index),
    loadOlder: () => chatCtl.loadOlder(ctxRef.current.sid),
    loadSession: (session: SessionDetail) => chatCtl.loadSession(session),
    reset: () => chatCtl.reset(),
    dropSession: (id: string) => chatCtl.dropSession(id),
  }), []);

  return {
    ...state,
    ...actions,
    
    pendingApprovals: state.pendingApprovals as ApprovalItem[],
    todos: state.todos as TodoItem[],
    planState: state.planState ?? IDLE_PLAN,
    debugLogs: state.debugLogs as DebugLog[],
  };
}
