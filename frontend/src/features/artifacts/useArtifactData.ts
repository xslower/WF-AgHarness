
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../kernel/api";
import type { ArtifactFile, Checkpoint, RecentFile } from "../../kernel/api";
import { events } from "../../kernel/api/eventBridge";
import { alertDialog, confirmDialog } from "../../kernel/ui/dialog";
import { errText } from "../../kernel/ui/errText";
import { fmtBytes } from "../../kernel/ui/format";
import { createCoalescer, isProjectEvent } from "./eventRefresh";
import type { useFileTree } from "./useFileTree";



export function toFile(r: RecentFile): ArtifactFile {
  return { name: r.rel || r.name, path: r.path, size: r.size, mtime: r.mtime };
}

export interface ArtifactData {
  files: ArtifactFile[];
  reports: ArtifactFile[];
  cks: Checkpoint[];
  showSnaps: boolean;
  setShowSnaps: (v: boolean) => void;
  setCks: (v: Checkpoint[]) => void;
  refresh: () => void;
  purgeTrash: () => Promise<void>;
}

export function useArtifactData(
  project: string,
  listTab: "recent" | "files",
  tree: ReturnType<typeof useFileTree>,
): ArtifactData {
  const [files, setFiles] = useState<ArtifactFile[]>([]);
  const [reports, setReports] = useState<ArtifactFile[]>([]);
  const [cks, setCks] = useState<Checkpoint[]>([]);
  const [showSnaps, setShowSnaps] = useState(false);
  
  const projectRef = useRef(project);
  projectRef.current = project;

  
  const loadLists = useCallback((proj: string) => {
    const fail = (e: unknown) => {
      if (projectRef.current === proj) {
        void alertDialog(`产出物列表加载失败：${errText(e)}`);
      }
    };
    api.recentFiles(proj).then((d) => {
      if (projectRef.current === proj) setFiles(d.items.map(toFile));
    }).catch(fail);
    api.artifacts(proj).then((d) => {
      if (projectRef.current === proj) setReports(d.reports);
    }).catch(fail);
  }, []);

  useEffect(() => {
    setFiles([]);   
    tree.reset(project);
    if (!project) {
      setReports([]);
      return;
    }
    
    loadLists(project);
  }, [project, loadLists, tree.reset]);

  
  const refresh = useCallback(() => {
    if (!project) return;
    loadLists(project);
    if (listTab === "files") void tree.load(project, true);
  }, [project, listTab, loadLists, tree.load]);

  
  const purgeTrash = useCallback(async () => {
    if (!project) return;
    try {
      const info = await api.trashInfo(project);
      if (!info.total_files) {
        void alertDialog("回收站是空的");
        return;
      }
      const ttl = info.retention_days > 0
        ? `（自动保留 ${info.retention_days} 天）` : "（自动清理已关闭）";
      const ok = await confirmDialog({
        title: "清空回收站",
        danger: true,
        okText: "立即删除",
        message:
          `回收站共 ${info.total_files} 个文件、${fmtBytes(info.total_bytes)}，`
          + `分 ${info.entries.length} 个批次${ttl}。\n立即全部删除？此操作不可恢复。`,
      });
      if (!ok) return;
      const r = await api.trashPurge(project, 0);
      void alertDialog(`已清理 ${r.removed} 个批次，释放 ${fmtBytes(r.freed_bytes)}`);
      refresh();
    } catch (e) {
      void alertDialog(`清理失败：${e}`);
    }
  }, [project, refresh]);

  
  useEffect(() => {
    if (project && listTab === "files") void tree.load(project);
  }, [project, listTab, tree.load]);

  
  
  useEffect(() => {
    if (!showSnaps) return;
    const proj = project;
    api.ckList(proj || undefined).then((list) => {
      if (projectRef.current === proj) setCks(list);
    }).catch((e) => {
      if (projectRef.current === proj) {
        setCks([]);
        void alertDialog(`快照列表加载失败：${errText(e)}`);
      }
    });
  }, [showSnaps, project]);

  
  
  useEffect(() => {
    if (!project) return;
    const refresher = createCoalescer(300, () => {
      loadLists(project);
      if (listTab === "files") void tree.load(project);
    });
    
    
    const onEvent = (ev: { payload?: Record<string, unknown> }) => {
      if (!isProjectEvent(ev.payload, project)) return;
      refresher.fire();
    };
    const off = events.on("file.changed", onEvent);
    const offOpened = events.on("file.opened", onEvent);
    const offRe = events.onReconnect(() => refresher.fire());
    return () => {
      off();
      offOpened();
      offRe();
      refresher.cancel();
    };
  }, [project, listTab, loadLists, tree.load]);

  return { files, reports, cks, showSnaps, setShowSnaps, setCks, refresh, purgeTrash };
}
