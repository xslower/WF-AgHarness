
import { useEffect, useRef } from "react";
import { events } from "../../kernel/api/eventBridge";
import type { WfRun } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";

const SELF_SAVE_WINDOW_MS = 1500;
const RUN_REFRESH_DEBOUNCE_MS = 300;

export interface DiskSyncArgs {
  name: string;
  project: string;
  
  wfName: string;
  savedName: React.MutableRefObject<string>;
  lastRev: React.MutableRefObject<string>;
  loaded: React.MutableRefObject<boolean>;
  saveState: string;
  flash: (t: string) => void;
  
  reload: (remote?: boolean) => Promise<void>;
  
  selfSaveAt: React.MutableRefObject<number>;
}


export function useDiskSync(args: DiskSyncArgs): void {
  const {
    name, project, wfName, savedName, lastRev, loaded, saveState,
    flash, reload, selfSaveAt,
  } = args;

  useEffect(() => {
    if (!name) return;
    const off = events.on("workflow.changed", (ev) => {
      const p = ev.payload || {};
      if (String(p.project || "") !== project) return;
      const changed = String(p.name || "");
      const mine = savedName.current || wfName || name;
      if (changed !== mine) return;
      
      
      const rev = String(p.revision || "");
      if (rev && rev === lastRev.current) return;
      
      if (Date.now() - selfSaveAt.current < SELF_SAVE_WINDOW_MS) return;
      if (!loaded.current) return;
      
      
      
      if (saveState === "saving") return;
      if (saveState === "dirty") {
        flash("磁盘上的工作流被外部改了（AI 或另一个窗口）；你本地还有未保存改动，"
              + "先保存会以本地为准，后端 revision 校验会拒绝被覆盖的保存");
        return;
      }
      if (p.action === "delete") return;    
      void reload(true).catch((e) => flash(`同步磁盘版本失败：${errText(e)}`));
    });
    
    
    
    const offRe = events.onReconnect(() => {
      if (!loaded.current) return;
      if (saveState === "dirty" || saveState === "saving") {
        flash("重连后检测到本地未保存改动，未自动重载磁盘版本；先保存或放弃改动");
        return;
      }
      void reload(true).catch((e) => flash(`重连后同步磁盘版本失败：${errText(e)}`));
    });
    return () => { off(); offRe(); };
  }, [name, project, wfName, savedName, lastRev, loaded, saveState,
      reload, flash, selfSaveAt]);
}

export interface RunSyncArgs {
  name: string;
  project: string;
  savedName: React.MutableRefObject<string>;
  runRef: React.MutableRefObject<WfRun | null>;
  refreshHistory: (project: string, wfName?: string) => Promise<{ id: string }[]>;
  openRun: (rid: string, project: string,
            opts?: { keepPolling?: boolean }) => Promise<void>;
  
  onRunChanged: (run: WfRun | null) => void;
  run: WfRun | null;
  
  flash: (t: string) => void;
}


export function useRunSync(args: RunSyncArgs): void {
  const { name, project, savedName, runRef, refreshHistory, openRun,
          onRunChanged, run, flash } = args;

  
  const apiRef = useRef({ refreshHistory, openRun, flash });
  apiRef.current = { refreshHistory, openRun, flash };

  useEffect(() => {
    if (!name) return;
    let timer: number | null = null;
    const off = events.on("workflow.run", (ev) => {
      const p = ev.payload || {};
      if (String(p.project || "") !== project) return;
      const wfName = String(p.workflow || "");
      if (wfName && wfName !== (savedName.current || name)) return;
      if (timer) window.clearTimeout(timer);
      
      timer = window.setTimeout(() => {
        void apiRef.current.refreshHistory(project, name).then((items) => {
          const rid = String(p.run || "");
          const target = items.some((x) => x.id === rid) ? rid : items[0]?.id;
          if (!target) return;
          const cur = runRef.current?.id;
          
          
          
          if (!cur || cur === rid) {
            void apiRef.current.openRun(target, project, { keepPolling: true })
              .catch((e) => apiRef.current.flash(`打开运行记录失败：${errText(e)}`));
          }
        }).catch((e) => apiRef.current.flash(`刷新运行历史失败：${errText(e)}`));
      }, RUN_REFRESH_DEBOUNCE_MS);
    });
    
    const offRe = events.onReconnect(() => {
      void apiRef.current.refreshHistory(project, name).then((items) => {
        const rid = items[0]?.id;
        if (!rid || (runRef.current?.id && runRef.current.id !== rid)) return;
        void apiRef.current.openRun(rid, project, { keepPolling: true })
          .catch((e) => apiRef.current.flash(`打开运行记录失败：${errText(e)}`));
      }).catch((e) => apiRef.current.flash(`重连后刷新运行历史失败：${errText(e)}`));
    });
    return () => { off(); offRe(); if (timer) window.clearTimeout(timer); };
  }, [project, name, savedName, runRef]);

  
  const runIdForViewRef = useRef<string | null>(null);
  useEffect(() => {
    const id = run?.id ?? null;
    if (runIdForViewRef.current === id) return;
    runIdForViewRef.current = id;
    onRunChanged(run);
  }, [run, onRunChanged]);
}
