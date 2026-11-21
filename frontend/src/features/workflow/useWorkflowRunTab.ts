
import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../kernel/api";
import type { WfRun } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";


const POLL_MS = 1000;

export interface RunTabController {
  run: WfRun | null;
  
  msg: string;
  error: string;
  cancel: () => Promise<void>;
  resume: () => Promise<void>;
  
  redo: (nodeId: string) => Promise<void>;
  decide: (choice: string, comment: string) => Promise<void>;
  reload: () => Promise<void>;
}

export function useWorkflowRunTab(p: {
  runId: string;
  project: string;
}): RunTabController {
  const [run, setRun] = useState<WfRun | null>(null);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  
  const genRef = useRef(0);
  
  const idRef = useRef(p.runId);

  const fetchOnce = useCallback(async (): Promise<WfRun | null> => {
    if (!idRef.current) return null;
    const r = await api.wfRunStatus(idRef.current, p.project).catch(() => null);
    return r;
  }, [p.project]);

  
  const loop = useCallback(async (gen: number) => {
    const r = await fetchOnce();
    if (gen !== genRef.current) return;
    if (r) { setRun(r); setError(""); }
    else if (!run) setError("运行记录不存在或已被清理");
    if (r && r.status === "running") {
      window.setTimeout(() => { void loop(gen); }, POLL_MS);
    }
    
  }, [fetchOnce]);

  useEffect(() => {
    const gen = ++genRef.current;
    idRef.current = p.runId;
    setRun(null);
    setError("");
    void loop(gen);
    return () => { genRef.current++; };   
  }, [p.runId, p.project, loop]);

  
  const restart = useCallback(() => {
    const gen = ++genRef.current;
    void loop(gen);
  }, [loop]);

  const cancel = useCallback(async () => {
    if (!run) return;
    
    setRun((r) => (r ? { ...r, status: "cancelled" } : r));
    try {
      await api.wfRunCancel(run.id, p.project);
      setMsg("⏹ 已中止");
    } catch (e) {
      setMsg(`中止失败：${errText(e)}`);
    }
    restart();
  }, [run, p.project, restart]);

  const resume = useCallback(async () => {
    if (!run) return;
    try {
      const rec = await api.wfResume(run.id, p.project);
      setRun(rec);
      setMsg(rec.status === "done" ? "✓ 续跑完成" : `✗ ${rec.error || rec.status}`);
    } catch (e) {
      setMsg(`续跑失败：${errText(e)}`);
    }
  }, [run, p.project]);

  const decide = useCallback(async (choice: string, comment: string) => {
    const gate = run?.pending_human;
    if (!run || !gate) return;
    try {
      await api.wfHumanDecide(run.id, gate.node_id, choice, comment, p.project);
      setMsg(`✓ 已选择：${choice}`);
    } catch (e) {
      setMsg(`提交失败：${errText(e)}`);
    }
    restart();
  }, [run, p.project, restart]);

  const reload = useCallback(async () => {
    const r = await fetchOnce();
    if (r) setRun(r);
    restart();
  }, [fetchOnce, restart]);

  
  const redo = useCallback(async (nodeId: string) => {
    if (!run) return;
    try {
      const { run_id } = await api.wfRunRedo(run.id, nodeId, "", p.project);
      idRef.current = run_id;
      setMsg(`✓ 已从 ${nodeId} 重跑（新运行 ${run_id}）`);
    } catch (e) {
      setMsg(`重跑失败：${errText(e)}`);
    }
    restart();
  }, [run, p.project, restart]);

  return { run, msg, error, cancel, resume, redo, decide, reload };
}
