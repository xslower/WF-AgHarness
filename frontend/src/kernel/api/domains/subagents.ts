import { getJson, parseJsonLoose } from "../client";

export interface SubAgentDetail {
  id: string;
  status: "running" | "done" | "failed" | "stopped";
  messages: unknown[];
  events: unknown[];
  result_path: string;
  next_offset?: number | null;
}

export interface SubAgentSummary {
  id: string;
  parent_id: string;
  project: string;
  task: string;
  status: "running" | "done" | "failed" | "stopped";
  created_at: number;
  finished_at?: number;
  result_chars?: number;
  result_path?: string;
  error?: string;
  message_count?: number;
}

export const subagentsApi = {
  
  subagentList: (parent = "", project = "") =>
    getJson<SubAgentSummary[]>(
      `/api/subagents?parent=${encodeURIComponent(parent)}` +
      `&project=${encodeURIComponent(project)}`),
  getSubagent: (id: string, parent = "", offset = 0, limit = 100) =>
    getJson<SubAgentDetail>(
      `/api/subagents/${encodeURIComponent(id)}?parent=${encodeURIComponent(parent)}` +
      `&offset=${offset}&limit=${limit}`),
  subagentResult: (id: string, parent = "") =>
    getJson<{ id: string; status: string; content: string; path: string; chars: number }>(
      `/api/subagents/${encodeURIComponent(id)}/result?parent=${encodeURIComponent(parent)}`),
  messageSubagent: (id: string, text: string, parent = "") =>
    fetch(`/api/subagents/${encodeURIComponent(id)}/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, parent }),
    }).then(parseJsonLoose),
  stopSubagent: (id: string, parent = "", force = true) =>
    fetch(`/api/subagents/${encodeURIComponent(id)}/stop`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parent, force }),
    }).then(parseJsonLoose),
};
