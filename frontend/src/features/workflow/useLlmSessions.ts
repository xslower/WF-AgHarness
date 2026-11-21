
import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../kernel/api";
import type { ChatMessage, SessionSummary } from "../../kernel/api";


export const WF_SESSION = "wf-session";
export const WF_NODE = "wf-node";

export interface LlmSessionsController {
  sessions: SessionSummary[];
  nodes: SessionSummary[];
  msgs: ChatMessage[];
  refreshSessions: () => Promise<void>;
  refreshNodes: (sid: string) => Promise<void>;
  refreshMsgs: (node: string) => Promise<void>;
}

export function useLlmSessions(p: {
  project: string;
  workflow: string;
  
  runSession: string | null;
  
  session: string;
  node: string;
  
  running: boolean;
}): LlmSessionsController {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [nodes, setNodes] = useState<SessionSummary[]>([]);
  const [msgs, setMsgs] = useState<ChatMessage[]>([]);
  
  const genRef = useRef({ sessions: 0, nodes: 0, msgs: 0 });

  const refreshSessions = useCallback(async () => {
    const g = ++genRef.current.sessions;
    if (!p.workflow) return;
    const rows = await api.listSessions(p.project, WF_SESSION, p.workflow).catch(() => null);
    if (rows && g === genRef.current.sessions) setSessions(rows);
  }, [p.project, p.workflow]);

  const refreshNodes = useCallback(async (sid: string) => {
    const g = ++genRef.current.nodes;
    if (!sid) { setNodes([]); return; }
    const rows = await api.listSessions(p.project, WF_NODE, sid).catch(() => null);
    if (rows && g === genRef.current.nodes) setNodes(rows);
  }, [p.project]);

  const refreshMsgs = useCallback(async (node: string) => {
    const g = ++genRef.current.msgs;
    if (!node) { setMsgs([]); return; }
    
    const d = await api.getSession(node, 0).catch(() => null);
    if (g === genRef.current.msgs) {
      setMsgs(d ? ((d.messages || []) as ChatMessage[]) : []);
    }
  }, []);

  useEffect(() => { void refreshSessions(); }, [refreshSessions]);
  useEffect(() => { void refreshNodes(p.session); }, [p.session, refreshNodes]);
  useEffect(() => { void refreshMsgs(p.node); }, [p.node, refreshMsgs]);

  
  useEffect(() => {
    if (!p.running) return;
    const t = window.setInterval(() => {
      void refreshSessions();
      void refreshNodes(p.session);
      if (p.node) void refreshMsgs(p.node);
    }, 2000);
    return () => window.clearInterval(t);
  }, [p.running, p.session, p.node, refreshSessions, refreshNodes, refreshMsgs]);

  return { sessions, nodes, msgs, refreshSessions, refreshNodes, refreshMsgs };
}
