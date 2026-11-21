
import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../kernel/api";
import type { SessionSummary } from "../../kernel/api";
import { confirmDialog } from "../../kernel/ui/dialog";
import { pickSessionId } from "./pickSessionId";


export const KIND = "workflow" as const;

export interface WorkflowChatSessions {
  
  sid: string | null;
  sessions: SessionSummary[];
  creating: boolean;
  reload: () => Promise<SessionSummary[]>;
  newSession: () => Promise<void>;
  remove: (s: SessionSummary) => Promise<void>;
  select: (id: string | null) => void;
}

export function useWorkflowChatSessions(opts: {
  project: string;
  name: string;
  
  dropChat: (id: string) => void;
}): WorkflowChatSessions {
  const { project, name, dropChat } = opts;
  
  const storeKey = `wfchat.${project}/${name}`;

  const [sidState, setSidState] = useState<string | null>(() => localStorage.getItem(storeKey));
  const [items, setItems] = useState<SessionSummary[]>([]);
  const [creating, setCreating] = useState(false);
  
  const sidRef = useRef(sidState);
  sidRef.current = sidState;

  const persist = useCallback((id: string | null) => {
    setSidState(id);
    try {
      if (id) localStorage.setItem(storeKey, id);
      else localStorage.removeItem(storeKey);
    } catch {  }
  }, [storeKey]);

  const reload = useCallback(async (): Promise<SessionSummary[]> => {
    const list = await api.listSessions(project, KIND, name).catch(() => []);
    setItems(list);
    return list;
  }, [project, name]);

  
  useEffect(() => {
    let cancelled = false;
    const localSid = localStorage.getItem(storeKey);
    setSidState(localSid);
    void (async () => {
      
      const [bound, list] = await Promise.all([
        api.bindSession(KIND, name, project).catch(() => ({ id: null as string | null })),
        reload(),
      ]);
      if (cancelled) return;
      
      persist(pickSessionId(localSid, list.map((s) => s.id), bound.id ?? null));
    })();
    return () => { cancelled = true; };
    
  }, [project, name, storeKey]);

  
  const newSession = async () => {
    if (creating) return;
    setCreating(true);
    try {
      const list = await reload();
      const empties = list.filter((x) => (x.message_count ?? 0) === 0);
      if (empties.length) {
        
        const keep = empties.find((x) => x.id === sidRef.current) ?? empties[empties.length - 1];
        for (const x of empties) {
          if (x.id !== keep.id) await api.deleteSession(x.id).catch(() => null);
        }
        persist(keep.id);
        await reload();
        return;
      }
      const s = await api.createSession("新会话", project, KIND, name);
      persist(s.id);
      await reload();
    } catch {
      
    } finally {
      setCreating(false);
    }
  };

  const remove = async (s: SessionSummary) => {
    const ok = await confirmDialog({
      title: "删除会话",
      message: `删除「${s.title}」？该会话的消息会一并删除，不可恢复。`,
      okText: "删除",
      danger: true,
    });
    if (!ok) return;
    await api.deleteSession(s.id);
    dropChat(s.id);   
    if (s.id === sidRef.current) persist(null);
    await reload();
  };

  const select = (id: string | null) => persist(id);

  return { sid: sidState, sessions: items, creating, reload, newSession, remove, select };
}
