
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { AppConfig } from "../api";
import { initSession, resetNewSessionSlot } from "../chat/chatSessionStore";
import { DEFAULT_SPEC, normalizeSpec } from "../model/modelSpec";
import {
  patchPrefs, readPrefs, specStillValid, type SessionPrefs,
} from "../chat/sessionPrefs";

export interface SessionChoice {
  curId: string | null;
  setCurId: (id: string | null) => void;
  curProject: string;
  setCurProject: (p: string) => void;
  modelSel: string;
  curPrefs: SessionPrefs;
  changeModel: (v: string) => void;
  changePlan: (v: boolean) => void;
  
  openSession: (id: string) => Promise<void>;
  
  resetForNewSession: (id: string, project: string) => void;
}

interface Args {
  config: AppConfig | null;
  
  chatRef: React.MutableRefObject<{
    loadSession: (s: Awaited<ReturnType<typeof api.getSession>>) => void;
    reset: () => void;
  } | null>;
}

export function useSessionChoice({ config, chatRef }: Args): SessionChoice {
  const [curId, setCurId] = useState<string | null>(null);
  const [curProject, setCurProject] = useState("");
  const [modelSel, setModelSel] = useState(() => normalizeSpec(readPrefs(null).model));
  
  const [curPrefs, setCurPrefs] = useState<SessionPrefs>(() => readPrefs(null));
  
  const latestId = useRef<string | null>(null);
  latestId.current = curId;

  
  
  useEffect(() => {
    const local = readPrefs(curId);
    setCurPrefs(local);
    setModelSel(normalizeSpec(local.model));
  }, [curId]);

  
  
  useEffect(() => {
    if (!config || !modelSel) return;
    if (specStillValid(modelSel, config)) return;
    console.warn("[model] spec 已失效，回落父队列：", modelSel, "会话=", curId);
    setModelSel(DEFAULT_SPEC);
    setCurPrefs(patchPrefs(curId, { model: DEFAULT_SPEC }));
  }, [config, modelSel, curId]);

  const openSession = useCallback(async (id: string) => {
    setCurId(id);
    latestId.current = id;
    
    const local = readPrefs(id);
    setCurPrefs(local);
    const m = normalizeSpec(local.model);
    setModelSel(specStillValid(m, config) ? m : DEFAULT_SPEC);
    
    const s = await api.getSession(id);
    if (s.project) setCurProject(s.project);
    chatRef.current?.loadSession(s);
  }, [config, chatRef]);

  const resetForNewSession = useCallback((id: string, project: string) => {
    setCurId(id);
    setCurProject(project);
    
    
    initSession(id);
    resetNewSessionSlot();
    const prefs = readPrefs(id);
    setCurPrefs(prefs);
    setModelSel(normalizeSpec(prefs.model));
    chatRef.current?.reset();
  }, [chatRef]);

  
  const changeModel = useCallback((v: string) => {
    const spec = normalizeSpec(v);
    setModelSel(spec);
    setCurPrefs(patchPrefs(curId, { model: spec }));
  }, [curId]);

  const changePlan = useCallback((v: boolean) => {
    setCurPrefs(patchPrefs(curId, { plan: v ? "1" : "0" }));
  }, [curId]);

  return {
    curId, setCurId, curProject, setCurProject,
    modelSel, curPrefs, changeModel, changePlan,
    openSession, resetForNewSession,
  };
}
