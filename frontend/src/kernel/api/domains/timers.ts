import type { TimerInput, TimerJob } from "../types";
import { buildQuery, delJson, getJson, patchJson, sendJson } from "../client";


export const timersApi = {
  
  listTimers: (owner?: string, project?: string) =>
    getJson<TimerJob[]>(`/api/timers${buildQuery({ owner, project })}`),
  createTimer: (body: TimerInput) =>
    sendJson<TimerJob>("/api/timers", "POST", body),
  updateTimer: (name: string, patch: Partial<TimerInput>) =>
    patchJson<TimerJob>(`/api/timers/${encodeURIComponent(name)}`, patch),
  deleteTimer: (name: string) =>
    delJson<{ ok: boolean }>(`/api/timers/${encodeURIComponent(name)}`),
};
