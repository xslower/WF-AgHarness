import type {
  AttentionSnapshot, ChatMessage, SessionDetail, SessionLive, SessionSummary,
} from "../types";
import { delJson, getJson, sendJson } from "../client";

export const sessionsApi = {
  
  listSessions: (project?: string, kind?: string, origin?: string) => {
    const q = new URLSearchParams();
    if (project !== undefined) q.set("project", project);
    if (kind !== undefined) q.set("kind", kind);
    if (origin !== undefined) q.set("origin", origin);
    const s = q.toString();
    return getJson<SessionSummary[]>(`/api/sessions${s ? `?${s}` : ""}`);
  },
  

  
  sessionLive: (sid: string, since = 0) =>
    getJson<SessionLive>(`/api/sessions/${sid}/live${since > 0 ? `?since=${since}` : ""}`),
  
  attention: () => getJson<AttentionSnapshot>("/api/sessions/attention"),
  
  bindSession: (kind: string, origin: string, project = "") => {
    const q = new URLSearchParams({ kind, origin });
    if (project) q.set("project", project);
    return getJson<{ id: string | null; session?: SessionSummary | null }>(
      `/api/sessions/bind?${q.toString()}`);
  },
  createSession: (title: string, project = "", kind = "", origin = "") => {
    const q = new URLSearchParams({ title, project });
    if (kind) q.set("kind", kind);
    if (origin) q.set("origin", origin);
    return sendJson<{ id: string }>(`/api/sessions?${q.toString()}`, "POST");
  },
  getSession: (id: string, tailPairs = 2) =>
    getJson<SessionDetail>(`/api/sessions/${id}${tailPairs > 0 ? `?tail_pairs=${tailPairs}` : ""}`),
  
  sessionMessagesBefore: (sid: string, before: number, limit = 150) =>
    getJson<SessionDetail>(
      `/api/sessions/${sid}/messages?before=${before}&limit=${limit}`),
  
  
  deleteSession: (id: string) => delJson<{ ok: boolean }>(`/api/sessions/${id}`),
  renameSession: (id: string, title: string) =>
    sendJson<{ ok: boolean; title: string }>(`/api/sessions/${id}/rename`, "POST", { title }),
  truncate: (sid: string, index: number) =>
    sendJson<{ messages: ChatMessage[] }>(`/api/sessions/${sid}/truncate`, "POST", { index }),
};
