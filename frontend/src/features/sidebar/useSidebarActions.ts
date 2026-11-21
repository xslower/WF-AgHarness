
import { useCallback, useRef } from "react";

import { api } from "../../kernel/api";
import type { SessionSummary, WorkflowDef, WorkflowSummary } from "../../kernel/api";
import { alertDialog, confirmDialog } from "../../kernel/ui/dialog";
import { errText } from "../../kernel/ui/errText";
import { baseName } from "../../kernel/ui/format";
import { newWorkflow } from "../workflow/defaultWorkflow";

export interface SidebarActionDeps {
  wfs: Record<string, WorkflowSummary[]>;
  refreshSessions: () => Promise<void>;
  refreshTree: () => Promise<void>;
  refreshWfs: (project: string) => Promise<void>;
  onExpand: (path: string) => void;
  onNewSession: (id: string, project: string) => void;
  onOpenWorkflow: (project: string, name: string) => void;
}

export interface SidebarActions {
  addTask: (project: string) => Promise<void>;
  addFlow: (project: string) => Promise<void>;
  renameSession: (sid: string, title: string) => Promise<void>;
  removeProject: (path: string) => Promise<void>;
  setFlowParent: (project: string, name: string, parent: string) => Promise<void>;
  
  registerProject: (dir: string) => Promise<boolean>;
  
  moveProject: (path: string, parent: string) => Promise<boolean>;
}


import { nextWorkflowName } from "../workflow/workflowName";

const NEW_FLOW = newWorkflow;

export function useSidebarActions(deps: SidebarActionDeps): SidebarActions {
  const {
    wfs, refreshSessions, refreshTree, refreshWfs,
    onExpand, onNewSession, onOpenWorkflow,
  } = deps;
  
  
  const registering = useRef<Set<string>>(new Set());

  
  const addTask = useCallback(async (project: string) => {
    try {
      const s = await api.createSession("新任务", project);
      await refreshSessions();
      onExpand(project);
      onNewSession(s.id, project);
    } catch (e) {
      void alertDialog(`创建任务失败：${errText(e)}`);
    }
  }, [refreshSessions, onExpand, onNewSession]);

  
  const addFlow = useCallback(async (project: string) => {
    const name = nextWorkflowName((wfs[project] || []).map((w) => w.name));
    try {
      await api.wfSave(NEW_FLOW(name), project);
      await refreshWfs(project);
      onExpand(project);
      onOpenWorkflow(project, name);
    } catch {
      
    }
  }, [wfs, refreshWfs, onExpand, onOpenWorkflow]);

  const renameSession = useCallback(async (sid: string, title: string) => {
    const t = title.trim();
    if (!t) return;
    try {
      await api.renameSession(sid, t);
      await refreshSessions();
    } catch (e) {
      void alertDialog(`重命名失败: ${errText(e)}`);
    }
  }, [refreshSessions]);

  
  const removeProject = useCallback(async (path: string) => {
    const name = baseName(path) || path;
    if (!(await confirmDialog({
      title: "移除项目", danger: true, okText: "继续",
      message: `要从侧栏移除项目「${name}」吗？\n\n下一步可选择是否连目录一起删。`,
    }))) return;
    const delFiles = await confirmDialog({
      title: "是否连文件一起删", danger: true,
      okText: "连目录一起删", cancelText: "只从列表移除",
      message: `连目录一起删：整个目录移入 ${path}/../.trash/（可手工找回）\n`
        + `只从列表移除：文件全部保留，仅从侧栏列表移除\n\n目录：${path}`,
    });
    try {
      await api.projectUnregister(path, delFiles);
      await refreshTree();
      await refreshSessions();
    } catch (e) {
      void alertDialog(`删除失败：${errText(e)}`);
    }
  }, [refreshTree, refreshSessions]);

  
  const setFlowParent = useCallback(async (project: string, name: string, parent: string) => {
    try {
      await api.wfSetParent(name, parent, project);
      await refreshWfs(project);
    } catch {
      
    }
  }, [refreshWfs]);

  const registerProject = useCallback(async (dir: string): Promise<boolean> => {
    if (registering.current.has(dir)) return false;
    registering.current.add(dir);
    try {
      const r = await api.projectRegister(dir);
      
      
      if (r.migrateFrom && await confirmDialog({
        title: "发现同名旧项目",
        message: `检测到旧项目「${r.migrateFrom}」的目录已不在，新项目与它同名。\n\n是否把旧项目的会话与运行数据迁移到新位置？（只重接引用，不改动你现在放好的目录）`,
        okText: "迁移", cancelText: "不迁移",
      })) {
        try {
          await api.projectMigrate(r.migrateFrom, r.path);
          await refreshSessions();
        } catch (e) {
          void alertDialog(`迁移失败: ${errText(e)}`);
        }
      } else if (r.recovered.recovered || r.recovered.rebound) {
        await refreshSessions();
      }
      await refreshTree();
      return true;
    } catch (e) {
      void alertDialog(`注册失败: ${errText(e)}`);
      return false;
    } finally {
      registering.current.delete(dir);
    }
  }, [refreshTree, refreshSessions]);

  
  const moveProject = useCallback(async (path: string, parent: string): Promise<boolean> => {
    try {
      await api.projectMove(path, parent);
      await refreshSessions();
      await refreshTree();
      return true;
    } catch (e) {
      void alertDialog(`移动项目失败: ${errText(e)}`);
      return false;
    }
  }, [refreshTree, refreshSessions]);

  return {
    addTask, addFlow, renameSession,
    removeProject, setFlowParent, registerProject, moveProject,
  };
}


export function groupByProject(sessions: SessionSummary[]): Map<string, SessionSummary[]> {
  const m = new Map<string, SessionSummary[]>();
  for (const s of sessions) {
    if (s.kind) continue;          
    const k = s.project || "";
    const arr = m.get(k);
    if (arr) arr.push(s); else m.set(k, [s]);
  }
  return m;
}
