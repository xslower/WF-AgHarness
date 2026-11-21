import { api } from "../api";
import type { TimerJob, TimerSessionPayload, TimerWorkflowPayload } from "../api/types";
import { chatCtl } from "../ui/chat/chatController";




const RESYNC_MS = 10 * 60 * 1000;

let started = false;
let resyncTimer: ReturnType<typeof setInterval> | null = null;

let waits = new Map<string, ReturnType<typeof setTimeout>>();

const busy = new Set<string>();


export function startTimerRunner(): void {
  if (started) return;
  started = true;
  void resync();
  resyncTimer = setInterval(() => void resync(), RESYNC_MS);
}


export function stopTimerRunner(): void {
  started = false;
  if (resyncTimer !== null) clearInterval(resyncTimer);
  resyncTimer = null;
  for (const t of waits.values()) clearTimeout(t);
  waits = new Map();
  busy.clear();
}


export async function resync(): Promise<void> {
  for (const t of waits.values()) clearTimeout(t);
  waits = new Map();
  let jobs: TimerJob[] = [];
  try {
    jobs = await api.listTimers("frontend");
  } catch {
    return;      
  }
  for (const job of jobs) {
    if (!job.enabled || job.nextRunAt === null) continue;
    schedule(job);
  }
}

function schedule(job: TimerJob): void {
  const delay = Math.max(0, job.nextRunAt! * 1000 - Date.now());
  const t = setTimeout(() => {
    waits.delete(job.name);
    void fire(job);
  }, delay);
  waits.set(job.name, t);
}

async function fire(job: TimerJob): Promise<void> {
  if (busy.has(job.name)) return;      
  busy.add(job.name);
  try {
    if (job.action === "session") await runSession(job);
    else await runWorkflow(job);
  } catch (e) {
    
    console.warn(`[timer] ${job.name} 执行失败`, e);
  } finally {
    busy.delete(job.name);
    
    void resync();
  }
}

async function runSession(job: TimerJob): Promise<void> {
  const p = job.payload as TimerSessionPayload;
  const title = p.title || `${job.name}`;
  const { id } = await api.createSession(title, p.project);
  
  await chatCtl.send(
    { sid: id, project: p.project, model: p.model || "parent" },
    p.prompt,
    { plan: false },
  );
}

async function runWorkflow(job: TimerJob): Promise<void> {
  const p = job.payload as TimerWorkflowPayload;
  await api.wfRun(p.workflow, p.inputs || {}, p.project, "", {}, "sequential",
    "auto-approve");
}
