
import type { Dispatch, SetStateAction } from "react";
import type { AppConfig, ModelSchedule, Provider } from "../../kernel/api";
import type { QueueName } from "../../kernel/model/modelSpec";


export type SettingsTab = "providers" | "queues" | "general" | "plugins" | "skills" | "mcp";

export type QueueKind = QueueName;

export const DAYS = "一二三四五六日";


export function cloneConfig(config: AppConfig): AppConfig {
  return JSON.parse(JSON.stringify(config));
}

export function patchP(
  setDraft: Dispatch<SetStateAction<AppConfig>>,
  idx: number,
  patch: Partial<Provider>,
) {
  setDraft((d) => {
    const providers = [...d.providers];
    providers[idx] = { ...providers[idx], ...patch };
    return { ...d, providers };
  });
}

export function patchM(
  setDraft: Dispatch<SetStateAction<AppConfig>>,
  pi: number,
  mi: number,
  patch: Partial<Provider["models"][number]>,
) {
  setDraft((d) => {
    const providers = [...d.providers];
    const models = [...providers[pi].models];
    models[mi] = { ...models[mi], ...patch };
    providers[pi] = { ...providers[pi], models };
    return { ...d, providers };
  });
}


export function patchMId(
  setDraft: Dispatch<SetStateAction<AppConfig>>,
  pi: number,
  modelId: string,
  patch: Partial<Provider["models"][number]>,
) {
  setDraft((d) => {
    const providers = [...d.providers];
    const mi = providers[pi].models.findIndex((m) => m.id === modelId);
    if (mi < 0) return d;
    const models = [...providers[pi].models];
    models[mi] = { ...models[mi], ...patch };
    providers[pi] = { ...providers[pi], models };
    return { ...d, providers };
  });
}

export function patchSchedules(
  setDraft: Dispatch<SetStateAction<AppConfig>>,
  pi: number,
  modelIdOrIdx: string | number,
  schedules: ModelSchedule[],
) {
  if (typeof modelIdOrIdx === "number") {
    
    patchM(setDraft, pi, modelIdOrIdx,
           { schedules: schedules.length ? schedules : undefined });
    return;
  }
  patchMId(setDraft, pi, modelIdOrIdx,
           { schedules: schedules.length ? schedules : undefined });
}

export function mSchedLabel(m: Provider["models"][number]): string {
  const ss = m.schedules;
  if (!ss?.length) return "全天";
  return ss.map((s) =>
    (s.days?.length ? "周" + s.days.map((d) => DAYS[d]).join("") : "每天") + ` ${s.start}-${s.end}`).join(", ");
}
