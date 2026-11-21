
import { useCallback, useState } from "react";

import { api } from "../../kernel/api";
import type { WfRun } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";
import { useRunPolling } from "./useRunPolling";
import { useRunControls } from "./useRunControls";
import { redoFrom } from "./redoRun";
import type { StartRunOpts, RunSingleOpts, RunFromOpts } from "./runEntries";


function doneText(r: WfRun): string {
  return r.status === "done" ? "✓ 完成" : `✗ ${r.error || r.status}`;
}

export function useWorkflowRun() {
  const [run, setRunState] = useState<WfRun | null>(null);
  const setRun = useCallback((upd: (r: WfRun | null) => WfRun | null) => {
    setRunState((prev) => upd(prev));
  }, []);
  
  const [session, setSession] = useState("");

  const polling = useRunPolling();
  const { timerRef } = polling;

  
  const lastOutputs = useCallback(() => {
    const out: Record<string, string> = {};
    if (run) {
      for (const [id, st] of Object.entries(run.nodes)) {
        if (st.status === "done" && st.output) out[id] = st.output;
      }
    }
    return out;
  }, [run]);

  const controls = useRunControls(run, setRun, polling);
  const { refreshHistory } = controls;

  
  const startPolling = async (runId: string, project: string,
                             flash: (t: string) => void) => {
    polling.start(runId, project, (r) => setRunState(r), (r) => flash(doneText(r)));
  };

  const startRun = async (opts: StartRunOpts) => {
    const { wfName, project, inputVals, parallelMode, flash } = opts;
    try {
      const { run_id } = await api.wfRun(wfName, inputVals, project, "", {},
                                          parallelMode, "ask", session);
      flash("▶ 运行中…");
      await startPolling(run_id, project, flash);
      await refreshHistory(project, wfName);
    } catch (e) { flash(`运行失败: ${errText(e)}`); }
  };

  
  const runSingleNode = async (opts: RunSingleOpts) => {
    const { wfName, selId, project, inputVals, flash } = opts;
    flash("▶ 试运行中…");
    try {
      const r = await api.wfRunSingle(wfName, selId, inputVals, project, lastOutputs());
      
      setRunState((old) => (old ? { ...old, nodes: { ...old.nodes, ...r.nodes } } : r));
      const st = r.nodes[selId];
      flash(st?.status === "done" ? "✓ 试运行完成" : `✗ ${st?.error || r.error || "失败"}`);
    } catch (e) { flash(`试运行失败: ${errText(e)}`); }
  };

  
  const startRunFrom = async (opts: RunFromOpts) => {
    const { wfName, selId, project, inputVals, parallelMode, flash } = opts;
    try {
      const { run_id } = await api.wfRun(wfName, inputVals, project, selId,
                                        lastOutputs(), parallelMode, "ask", session);
      flash(`▶ 从 ${selId} 运行中…`);
      await startPolling(run_id, project, flash);
    } catch (e) { flash(`运行失败: ${errText(e)}`); }
  };

  
  const redoRun = async (o: { nodeId: string; project: string;
                              flash: (t: string) => void; note?: string }) => {
    await redoFrom({ run, project: o.project, flash: o.flash,
      follow: async (rid) => { await startPolling(rid, o.project, o.flash); },
      refresh: () => refreshHistory(o.project, run?.workflow ?? "") },
    o.nodeId, o.note ?? "");
  };

  return {
    run, setRun, timerRef, lastOutputs,
    startRun, runSingleNode, startRunFrom, redoRun,
    ...controls,
    session, setSession,
  };
}
