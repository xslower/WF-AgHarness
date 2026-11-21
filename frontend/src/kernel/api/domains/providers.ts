import type { Provider, TestResult } from "../types";
import { delJson, sendJson } from "../client";

export const providersApi = {
  addProvider: (p: Omit<Provider, "id">) =>
    sendJson<Provider>("/api/providers", "POST", p),
  updateProvider: (id: string, p: Omit<Provider, "id">) =>
    sendJson<Provider>(`/api/providers/${id}`, "PUT", p),
  deleteProvider: (id: string) => delJson<unknown>(`/api/providers/${id}`),
  fetchModels: (id: string) =>
    sendJson<{ models: Provider["models"] }>(`/api/providers/${id}/fetch_models`, "POST"),
  setQueue: (parent: string[], child: string[], summary: string[] = []) =>
    sendJson<unknown>("/api/model_queue", "PUT", { parent, child, summary }),
  removeModel: (pid: string, mid: string) =>
    
    delJson<unknown>(`/api/providers/${pid}/models/${encodeURIComponent(mid)}`),
  testModel: (spec: string) =>
    sendJson<TestResult>(`/api/test_model?spec=${encodeURIComponent(spec)}`, "POST"),
  importEnvProviders: () =>
    sendJson<{ imported: { name: string; models: number; error?: string }[]; skipped: string[] }>(
      "/api/providers/import_env",
      "POST",
    ),
};
