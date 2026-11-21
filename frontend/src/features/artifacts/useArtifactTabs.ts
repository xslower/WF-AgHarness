
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../kernel/api";
import { events } from "../../kernel/api/eventBridge";
import { alertDialog } from "../../kernel/ui/dialog";
import { errText } from "../../kernel/ui/errText";
import { scopedStore, SCOPE_TTL_MS } from "../../kernel/ui/scopedStore";
import type { Tab } from "../../kernel/ui/artifacts/types";
import { tabFromPreview } from "../../kernel/ui/artifacts/files";
import { isProjectEvent, normPath } from "./eventRefresh";
import { closeTabIn, normalizeUrl, patchTabIn, pushTab, urlTab } from "./tabRules";
import { bindSubAgentOpener } from "../../kernel/chat/subAgentTab";
import { bindWorkflowRunOpener } from "../../kernel/chat/workflowRunTab";

export interface TabState {
  tabs: Tab[];
  active: string | null;
  setActive: (key: string | null) => void;
  cur: Tab | null;
  addTab: (tab: Tab) => void;
  openFile: (f: { path: string; name: string; size: number }) => Promise<void>;
  openUrl: (rawUrl: string) => boolean;
  closeTab: (key: string) => void;
  patchTab: (key: string, patch: Partial<Tab>) => void;
  saveTab: (key: string) => Promise<void>;
}


interface StoredTab {
  key: string;
  title: string;
  kind: Tab["kind"];
  ext?: string;
  url?: string;
  mdPreview?: boolean;
  dirty?: boolean;
  content?: string;
  subagentId?: string;
  sessionId?: string;
  runId?: string;
  workflow?: string;
}

interface StoredTabs {
  tabs: StoredTab[];
  active: string | null;
}

const NAME = "artifacts";

function toStored(tabs: Tab[], active: string | null): StoredTabs {
  return {
    active,
    tabs: tabs.map((t) => ({
      key: t.key,
      title: t.title,
      kind: t.kind,
      ext: t.ext,
      url: t.url,
      mdPreview: t.mdPreview,
      dirty: t.dirty,
      subagentId: t.subagentId,
      sessionId: t.sessionId,
      runId: t.runId,
      workflow: t.workflow,
      
      content: t.dirty ? (t.content ?? "") : undefined,
    })),
  };
}


export function useArtifactTabs(project: string, onOpenMain: () => void,
                                scope: string): TabState {
  const [tabs, setTabs] = useState<Tab[]>([]);
  const [active, setActive] = useState<string | null>(null);
  
  const scopeRef = useRef(scope);

  
  const persist = useCallback((sc: string, ts: Tab[], act: string | null) => {
    
    if (!ts.length) scopedStore.clearScope(sc);
    else scopedStore.write(sc, NAME, toStored(ts, act), SCOPE_TTL_MS);
  }, []);

  
  const refreshCleanFiles = useCallback((ts: Tab[]) => {
    for (const t of ts) {
      if (t.dirty || t.kind === "web" || t.kind === "image" || !t.key) continue;
      void api.filePreview(t.key).then((d) => {
        const fresh = tabFromPreview(t.key, d);
        setTabs((cur) => cur.map((x) => (x.key === t.key && !x.dirty
          ? { ...x, content: fresh.content, dataurl: fresh.dataurl, dirty: false }
          : x)));
      }).catch(() => {  });
    }
  }, []);

  
  useEffect(() => {
    if (scopeRef.current === scope) return;
    scopeRef.current = scope;
    const saved = scopedStore.read<StoredTabs>(scope, NAME, SCOPE_TTL_MS);
    if (!saved?.tabs?.length) {
      setTabs([]);
      setActive(null);
      return;
    }
    const restored: Tab[] = saved.tabs.map((t) => ({
      key: t.key,
      title: t.title,
      kind: t.kind,
      ext: t.ext,
      url: t.url,
      mdPreview: t.mdPreview,
      content: t.dirty ? (t.content ?? "") : "",
      subagentId: t.subagentId,
      sessionId: t.sessionId,
      runId: t.runId,
      workflow: t.workflow,
      dirty: !!t.dirty,
      dataurl: undefined,
    }) as Tab);
    setTabs(restored);
    setActive(saved.active && restored.some((t) => t.key === saved.active)
      ? saved.active : restored[restored.length - 1]?.key ?? null);

    
    refreshCleanFiles(restored);
  }, [scope, refreshCleanFiles]);

  
  useEffect(() => {
    const id = setTimeout(() => persist(scope, tabs, active), 250);
    return () => clearTimeout(id);
  }, [scope, tabs, active, persist]);

  
  
  const addTab = useCallback((tab: Tab) => {
    setTabs((ts) => pushTab(ts, tab));
    setActive(tab.key);
    onOpenMain();       
  }, [onOpenMain]);

  const openFile = useCallback(async (f: { path: string; name: string; size: number }) => {
    const d = await api.filePreview(f.path).catch(() => null);
    if (!d) return;
    addTab(tabFromPreview(f.path, d));
    
    if (project) api.recentTouch(project, f.path).catch(() => {});
  }, [addTab, project]);

  
  
  
  useEffect(() => {
    const sid = scope.startsWith("sess:") ? scope.slice(5) : "";
    bindSubAgentOpener((req) => addTab({
      key: `subagent:${req.id}`,
      title: (req.task || "子 Agent").slice(0, 24),
      kind: "subagent",
      subagentId: req.id,
      sessionId: req.sessionId || (sid === "__new__" ? "" : sid),
    }));
    return () => bindSubAgentOpener(null);
  }, [addTab, scope]);

  
  
  
  useEffect(() => {
    bindWorkflowRunOpener((req) => addTab({
      key: `wfrun:${req.runId}`,
      title: (req.workflow || "工作流运行").slice(0, 24),
      kind: "workflow-run",
      runId: req.runId,
      workflow: req.workflow || "",
      project: req.project || project,
    }));
    return () => bindWorkflowRunOpener(null);
  }, [addTab, project]);

  
  const openUrl = useCallback((rawUrl: string): boolean => {
    const url = normalizeUrl(rawUrl);
    if (!url) return false;
    addTab(urlTab(url));
    return true;
  }, [addTab]);

  const closeTab = useCallback((key: string) => {
    setTabs((ts) => {
      const next = closeTabIn(ts, key, active);
      setActive(next.active);
      return next.tabs;
    });
  }, [active]);

  const patchTab = useCallback((key: string, patch: Partial<Tab>) => {
    setTabs((ts) => patchTabIn(ts, key, patch));
  }, []);

  const saveTab = useCallback(async (key: string) => {
    const t = tabs.find((x) => x.key === key);
    if (!t || !t.dirty) return;
    try {
      await api.fileSave(t.key, t.content ?? "", project);
      patchTab(key, { dirty: false });
    } catch (e) {
      
      
      void alertDialog(`保存失败（内容仍未保存）：${errText(e)}`);
    }
  }, [tabs, project, patchTab]);

  
  
  const selfWrite = useRef<Map<string, number>>(new Map());
  const curRef = useRef<{ tabs: Tab[]; project: string }>({ tabs, project });
  curRef.current = { tabs, project };

  
  const saveTabTracked = useCallback(async (key: string) => {
    selfWrite.current.set(key, Date.now());
    await saveTab(key);
  }, [saveTab]);

  
  useEffect(() => {
    const dirty = tabs.filter((t) => t.dirty && (t.kind === "code" || t.kind === "md"));
    if (!dirty.length) return;
    const timers = dirty.map((t) => setTimeout(() => void saveTabTracked(t.key), 2000));
    return () => timers.forEach(clearTimeout);
    
  }, [tabs, saveTabTracked]);

  
  useEffect(() => {
    if (!project) return;
    const off = events.on("file.changed", (ev: { payload?: Record<string, unknown> }) => {
      const p = ev.payload ?? {};
      if (!isProjectEvent(p, project)) return;
      const changed = normPath(p.path ?? p.rel ?? "");
      if (!changed) return;
      setTabs((ts) => {
        const hit = ts.find((t) => normPath(t.key).endsWith(changed) || changed.endsWith(normPath(t.key)));
        if (!hit) return ts;
        const lastSelf = selfWrite.current.get(hit.key) ?? 0;
        if (Date.now() - lastSelf < 1500) return ts;    
        if (hit.dirty) {
          
          return ts.map((t) => (t.key === hit.key ? { ...t, conflict: true } : t));
        }
        
        void api.filePreview(hit.key).then((d) => {
          const fresh = tabFromPreview(hit.key, d);
          setTabs((cur2) => cur2.map((t) => (t.key === hit.key && !t.dirty
            ? { ...t, content: fresh.content, dataurl: fresh.dataurl }
            : t)));
        }).catch(() => {});
        return ts;
      });
    });
    return () => { off(); };
  }, [project]);

  
  
  useEffect(() => {
    return events.onReconnect(() => refreshCleanFiles(curRef.current.tabs));
  }, [refreshCleanFiles]);

  const cur = active ? tabs.find((t) => t.key === active) ?? null : null;

  return { tabs, active, setActive, cur, addTab, openFile, openUrl,
    closeTab, patchTab, saveTab: saveTabTracked };
}
