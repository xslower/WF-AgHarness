
import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { AppConfig, ProjectNode, SessionSummary, WorkflowSummary } from "../api";
import { events } from "../api/eventBridge";

const CONFIG_CACHE_KEY = "ui.config";

function readConfigCache(): AppConfig | null {
  try {
    const raw = localStorage.getItem(CONFIG_CACHE_KEY);
    return raw ? (JSON.parse(raw) as AppConfig) : null;
  } catch {
    return null;
  }
}

export interface AppData {
  sessions: SessionSummary[];
  projTree: ProjectNode | null;
  wfs: Record<string, WorkflowSummary[]>;
  config: AppConfig | null;
  setConfig: (c: AppConfig) => void;
  refreshConfig: () => Promise<void>;
  refreshSessions: () => Promise<void>;
  refreshTree: () => Promise<void>;
  refreshWfs: (project: string) => Promise<void>;
}

export function useAppData(): AppData {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [projTree, setProjTree] = useState<ProjectNode | null>(null);
  const [wfs, setWfs] = useState<Record<string, WorkflowSummary[]>>({});
  const [config, setConfigState] = useState<AppConfig | null>(readConfigCache);

  const setConfig = useCallback((c: AppConfig) => {
    setConfigState(c);
    try { localStorage.setItem(CONFIG_CACHE_KEY, JSON.stringify(c)); } catch {  }
  }, []);

  
  const refreshConfig = useCallback(async () => {
    try {
      setConfig(await api.getConfig());
    } catch {
      
    }
  }, [setConfig]);

  const refreshSessions = useCallback(async () => {
    
    setSessions(await api.listSessions(undefined, ""));
  }, []);

  const refreshTree = useCallback(async () => {
    setProjTree(await api.projectsTree().catch(() => null));
  }, []);

  const refreshWfs = useCallback(async (project: string) => {
    
    
    const list = (await api.wfList(project).catch(() => [] as WorkflowSummary[]))
      .filter((w) => !w.internal);
    setWfs((w) => ({ ...w, [project || "__"]: list }));
  }, []);

  useEffect(() => {
    void refreshSessions();
    void refreshTree();
    void refreshConfig();
  }, [refreshSessions, refreshTree, refreshConfig]);

  
  
  
  useEffect(() => {
    const offs = [
      events.on("config.changed", () => { void refreshConfig(); }),
      
      events.onReconnect(() => { void refreshConfig(); }),
    ];
    return () => { for (const off of offs) off(); };
  }, [refreshConfig]);

  return { sessions, projTree, wfs, config, setConfig, refreshConfig,
           refreshSessions, refreshTree, refreshWfs };
}
