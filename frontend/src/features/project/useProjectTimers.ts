
import { useCallback, useEffect, useState } from "react";

import { api } from "../../kernel/api";
import type { TimerInput, TimerJob } from "../../kernel/api/types";
import { resync as resyncRunner } from "../../kernel/timers/runner";
import { errText } from "../../kernel/ui/errText";

export interface ProjectTimers {
  jobs: TimerJob[];
  busy: string;
  error: string;
  reload: () => Promise<void>;
  save: (job: TimerJob, patch: TimerDraft) => Promise<void>;
  create: (draft: TimerDraft) => Promise<void>;
  remove: (name: string) => Promise<void>;
  toggle: (job: TimerJob) => Promise<void>;
}


export interface TimerDraft extends Omit<TimerInput, "payload"> {
  
  target: string;
  
  title: string;
  
  prompt: string;
  
  workflow: string;
}

const EMPTY: TimerDraft = {
  name: "", owner: "frontend", action: "session", kind: "every", spec: "3600",
  target: "", title: "", prompt: "", workflow: "",
};

export const emptyTimerDraft = EMPTY;


export function toDraft(job: TimerJob): TimerDraft {
  const p = (job.payload || {}) as unknown as Record<string, unknown>;
  return {
    name: job.name,
    owner: job.owner,
    action: job.action,
    kind: job.kind,
    spec: job.spec,
    target: String(p.workflow || p.prompt || ""),
    title: String(p.title || ""),
    prompt: String(p.prompt || ""),
    workflow: String(p.workflow || ""),
  };
}


function toInput(d: TimerDraft): TimerInput {
  const payload = d.action === "session"
    ? { project: d.target, prompt: d.prompt, title: d.title || d.name }
    : { project: d.target, workflow: d.workflow, inputs: {} };
  return {
    name: d.name.trim(), owner: d.owner, action: d.action,
    kind: d.kind, spec: d.spec.trim(), payload,
  };
}

export function useProjectTimers(project: string): ProjectTimers {
  const [jobs, setJobs] = useState<TimerJob[]>([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    try {
      const all = await api.listTimers(undefined, project);
      setJobs(all);
      setError("");
    } catch (e) {
      setError(errText(e));
    }
  }, [project]);

  useEffect(() => { void reload(); }, [reload]);

  const run = useCallback(async (key: string, fn: () => Promise<unknown>) => {
    setBusy(key);
    setError("");
    try {
      await fn();
      await reload();
      
      void resyncRunner();
    } catch (e) {
      setError(errText(e));
    } finally {
      setBusy("");
    }
  }, [reload]);

  const create = useCallback(
    (d: TimerDraft) => run("create", () => api.createTimer(toInput(d))), [run]);

  const save = useCallback(
    (job: TimerJob, d: TimerDraft) => run(job.name, async () => {
      const input = toInput(d);
      const patch = { ...input };
      delete (patch as { name?: string }).name;   
      return api.updateTimer(job.name, patch);
    }), [run]);

  const remove = useCallback(
    (name: string) => run(name, () => api.deleteTimer(name)), [run]);

  const toggle = useCallback(
    (job: TimerJob) => run(job.name,
      () => api.updateTimer(job.name, { enabled: !job.enabled })), [run]);

  return { jobs, busy, error, reload, save, create, remove, toggle };
}
