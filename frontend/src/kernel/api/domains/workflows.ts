import type { NodeCatalogItem, WfAvailable, WfRun, WfRunSummary, WfWhy,
  WorkflowDef, WorkflowSummary } from "../types";
import { getJson, parseJson, parseJsonLoose } from "../client";

export const workflowsApi = {
  wfList: (project = "") =>
    getJson<WorkflowSummary[]>(`/api/workflows?project=${encodeURIComponent(project)}`),
  workflowNodes: () => getJson<NodeCatalogItem[]>("/api/workflows/nodes"),
  
  wfAvailable: (project = "") =>
    getJson<WfAvailable[]>(
      `/api/workflows/available?project=${encodeURIComponent(project)}`),
  wfGet: (name: string, project = "") =>
    getJson<WorkflowDef>(`/api/workflows/${name}?project=${encodeURIComponent(project)}`),
  wfSave: (wf: unknown, project = "") =>
    fetch(`/api/workflows?project=${encodeURIComponent(project)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(wf),
    }).then(parseJsonLoose<unknown>),
  wfDelete: (name: string, project = "") =>
    fetch(`/api/workflows/${name}?project=${encodeURIComponent(project)}`, {
      method: "DELETE",
    }),
  wfRename: (name: string, newName: string, project = "") =>
    fetch(`/api/workflows/${encodeURIComponent(name)}/rename?project=${encodeURIComponent(project)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ new_name: newName }),
    }).then(parseJsonLoose<unknown>),
  wfSetParent: (name: string, parent: string, project = "") =>
    fetch(`/api/workflows/${encodeURIComponent(name)}/parent?project=${encodeURIComponent(project)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parent }),
    }).then(parseJsonLoose<unknown>),
  
  wfSetStatus: (name: string, status: "draft" | "published", project = "") =>
    fetch(`/api/workflows/${encodeURIComponent(name)}/status?project=${encodeURIComponent(project)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    }).then(parseJsonLoose<unknown>),

  wfImport: (wf: unknown, project = "") =>
    fetch(`/api/workflows/import?project=${encodeURIComponent(project)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(wf),
    }).then(parseJsonLoose<unknown>),
  wfExport: (name: string, project = "") =>
    getJson<WorkflowDef>(
      `/api/workflows/${name}/export?project=${encodeURIComponent(project)}`,
    ),
  wfAssist: (name: string, instruction: string, project = "") =>
    fetch(`/api/workflows/${name}/assist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ instruction, project }),
    }).then(parseJsonLoose<{ ok: boolean; workflow: WorkflowDef }>),
  
  wfRun: (name: string, inputs: Record<string, unknown>, project = "",
          startNode = "", presetOutputs: Record<string, unknown> = {},
          parallelMode: "agent" | "sequential" = "sequential",
          human: "ask" | "auto-approve" | "auto-reject" = "ask",
          session = "") =>
    fetch(`/api/workflows/${name}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ inputs, project, start_node: startNode,
        preset_outputs: presetOutputs, parallel_mode: parallelMode, human,
        session }),
    }).then(parseJson<{ run_id: string }>),
  wfRunSingle: (name: string, nodeId: string, inputs: Record<string, unknown>,
          project = "", presetOutputs: Record<string, unknown> = {}) =>
    fetch(`/api/workflows/${name}/run_single`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ node_id: nodeId, inputs, project,
        preset_outputs: presetOutputs }),
    }).then(parseJson<WfRun>),
  wfRunStatus: (rid: string, project = "") =>
    getJson<WfRun>(`/api/workflows/runs/${rid}?project=${encodeURIComponent(project)}`),
  
  wfRunList: (project = "", workflow = "", limit = 30) =>
    getJson<{ items: WfRunSummary[] }>(
      `/api/workflows/runs?project=${encodeURIComponent(project)}` +
      `&workflow=${encodeURIComponent(workflow)}&limit=${limit}`),
  wfRunCancel: (rid: string, project = "") =>
    fetch(`/api/workflows/runs/${rid}/cancel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project }),
    }).then(parseJson<{ ok: boolean; status: string }>),
  
  wfHumanDecide: (rid: string, nodeId: string, choice: string, comment = "",
                  project = "") =>
    fetch(`/api/workflows/runs/${rid}/human`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project, node_id: nodeId, choice, comment }),
    }).then(parseJson<{ ok: boolean; node_id: string; choice: string }>),
  
  wfResume: (rid: string, project = "", startNode = "") =>
    fetch(`/api/workflows/runs/${rid}/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project, start_node: startNode }),
    }).then(parseJson<WfRun>),

  
  wfRunWhy: (rid: string,
             q: { project?: string; node?: string; key?: string; grep?: string } = {}) => {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries(q)) if (v) p.set(k, v);
    return getJson<WfWhy>(`/api/workflows/runs/${rid}/why?${p.toString()}`);
  },
  
  wfRunRedo: (rid: string, startNode: string, note = "", project = "") =>
    fetch(`/api/workflows/runs/${rid}/redo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project, start_node: startNode, note }),
    }).then(parseJson<{ run_id: string }>),
};
