
import { api } from "../../kernel/api";
import type { WorkflowDef } from "../../kernel/api";

export interface WorkflowPersistence {
  
  fetch: (name: string, project: string) => Promise<WorkflowDef>;
  
  setStatus: (name: string, status: "published" | "draft", project: string) => Promise<void>;
}

export function workflowPersistence(): WorkflowPersistence {
  return {
    fetch: (name, project) => api.wfGet(name, project),
    setStatus: async (name, status, project) => { await api.wfSetStatus(name, status, project); },
  };
}
