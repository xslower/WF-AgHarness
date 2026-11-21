
import { useState } from "react";

import { api } from "../../kernel/api";
import type { WfRun, WfRunSummary } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";
import type { useRunPolling } from "./useRunPolling";

export interface RunControls {
  history: WfRunSummary[];
  refreshHistory: (project: string, wfName?: string) => Promise<WfRunSummary[]>;
  cancelRun: (o: { project: string; flash: (t: string) => void }) => Promise<void>;
  resumeRun: (o: { project: string; flash: (t: string) => void }) => Promise<void>;
  openRun: (
    rid: string, project: string,
    o?: { keepPolling?: boolean; onError?: (t: string) => void },
  ) => Promise<void>;
  decideHuman: (o: {
    project: string; choice: string; comment: string; flash: (t: string) => void;
  }) => Promise<void>;
}

export function useRunControls(
  run: WfRun | null,
  setRun: (upd: (r: WfRun | null) => WfRun | null) => void,
  polling: ReturnType<typeof useRunPolling>,
): RunControls {
  const [history, setHistory] = useState<WfRunSummary[]>([]);

  
  const refreshHistory = async (project: string, wfName = "") => {
    const r = await api.wfRunList(project, wfName, 30).catch(() => null);
    if (r) setHistory(r.items);
    return r?.items ?? [];
  };

  
  const cancelRun = async (o: { project: string; flash: (t: string) => void }) => {
    if (!run) {
      
      o.flash("当前没有正在显示的运行；先从历史里打开一条再操作");
      return;
    }
    const target = run;
    
    polling.stop();
    setRun((r) => (r && r.id === target.id ? { ...r, status: "cancelled" } : r));
    try {
      await api.wfRunCancel(target.id, o.project);
      o.flash("⏹ 已中止");
    } catch (e) {
      
      o.flash(`中止失败：${errText(e)}`);
      const back = await api.wfRunStatus(target.id, o.project).catch(() => null);
      if (back) setRun(() => back);
      return;
    }
    const r = await api.wfRunStatus(target.id, o.project).catch(() => null);
    if (r) setRun(() => r);
    await refreshHistory(o.project, target.workflow);
  };

  
  const resumeRun = async (o: { project: string; flash: (t: string) => void }) => {
    if (!run) return;
    try {
      const rec = await api.wfResume(run.id, o.project);
      setRun(() => rec);
      o.flash(rec.status === "done" ? "✓ 续跑完成" : `✗ ${rec.error || rec.status}`);
    } catch (e) {
      o.flash(`续跑失败: ${errText(e)}`);
    }
    await refreshHistory(o.project, run.workflow);
  };

  
  const openRun = async (
    rid: string, project: string,
    o: { keepPolling?: boolean; onError?: (t: string) => void } = {},
  ) => {
    if (!o.keepPolling) polling.stop();
    try {
      setRun(() => null);
      const r = await api.wfRunStatus(rid, project);
      setRun(() => r);
    } catch (e) {
      
      o.onError?.(`打开运行 ${rid} 失败：${errText(e)}`);
    }
  };

  
  const decideHuman = async (o: {
    project: string; choice: string; comment: string; flash: (t: string) => void;
  }) => {
    if (!run?.pending_human) return;
    try {
      await api.wfHumanDecide(run.id, run.pending_human.node_id,
        o.choice, o.comment, o.project);
      o.flash(`✓ 已选择：${o.choice}`);
      const r = await api.wfRunStatus(run.id, o.project).catch(() => null);
      if (r) setRun(() => r);
    } catch (e) {
      o.flash(`提交失败: ${errText(e)}`);
    }
  };

  return { history, refreshHistory, cancelRun, resumeRun, openRun, decideHuman };
}
