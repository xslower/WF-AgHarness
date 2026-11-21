
import { useCallback, useRef } from "react";

import { api } from "../api";
import { dropSession as dropLocalSession } from "../chat/chatSessionStore";
import { alertDialog } from "../ui/dialog";
import { errText } from "../ui/errText";
export interface SessionLifecycleDeps {
  curId: string | null;
  
  dropSession: (id: string) => void;
  
  resetChat: () => void;
  setCurId: (id: string | null) => void;
  resetForNewSession: (id: string, project: string) => void;
  refreshSessions: () => Promise<void> | void;
}

export interface SessionLifecycle {
  
  newSessionFor: (project: string) => Promise<void>;
  
  deleteSession: (id: string) => Promise<void>;
}

export function useSessionLifecycle(deps: SessionLifecycleDeps): SessionLifecycle {
  
  const latest = useRef(deps);
  latest.current = deps;

  const newSessionFor = useCallback(async (project: string) => {
    try {
      const s = await api.createSession("新任务", project);
      latest.current.resetForNewSession(s.id, project);
    } catch (e) {
      void alertDialog(`创建会话失败：${errText(e)}`);
    }
  }, []);

  const deleteSession = useCallback(async (id: string) => {
    
    try {
      await api.deleteSession(id);
    } catch (e) {
      void alertDialog(`删除失败：${errText(e)}`);
      return;
    }
    const d = latest.current;
    d.dropSession(id);
    
    
    dropLocalSession(id);
    if (id === d.curId) {
      d.setCurId(null);
      d.resetChat();
    }
    await d.refreshSessions();
  }, []);

  return { newSessionFor, deleteSession };
}
