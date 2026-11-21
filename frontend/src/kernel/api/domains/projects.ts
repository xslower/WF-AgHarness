import type { BrowseResult, ProjectNode, ProjectOverview, ProjectPolicy } from "../types";


export interface ProjectRegisterResult {
  name: string;
  path: string;
  migrateFrom: string;
  recovered: { scanned: number; recovered: number; rebound: number; skipped: number };
}
export interface ProjectMoveResult {
  path: string;
  from: string;
  runtime_moved: number;
  registry_moved: number;
  sessions_moved: number;
  recovered: ProjectRegisterResult["recovered"];
}
import { delJson, getJson, sendJson } from "../client";

export const projectsApi = {
  projectsTree: () => getJson<ProjectNode>("/api/projects/tree"),
  
  projectOverview: (path: string) =>
    getJson<ProjectOverview>(`/api/projects/overview?path=${encodeURIComponent(path)}`),
  
  projectUnregister: (path: string, deleteFiles = false) =>
    delJson(`/api/projects?path=${encodeURIComponent(path)}${deleteFiles ? "&delete_files=true" : ""}`),
  projectRegister: (path: string) =>
    sendJson<ProjectRegisterResult>("/api/projects/register", "POST", { path }),
  
  projectMove: (path: string, parent: string) =>
    sendJson<ProjectMoveResult>("/api/projects/move", "POST", { path, parent }),
  
  projectMigrate: (oldPath: string, newPath: string) =>
    sendJson<ProjectMoveResult>("/api/projects/migrate", "POST", { old: oldPath, new: newPath }),
  projectBrowse: (path = "") => getJson<BrowseResult>(`/api/projects/browse?path=${encodeURIComponent(path)}`),
  fileTree: (project: string) =>
    getJson<unknown>(`/api/projects/file_tree?project=${encodeURIComponent(project)}`),
  
  fileTreeChildren: (project: string, dir: string) =>
    getJson<unknown[]>(`/api/projects/file_tree_children?project=${encodeURIComponent(project)}&dir=${encodeURIComponent(dir)}`),
  
  projectPolicy: (path: string) =>
    getJson<ProjectPolicy>(`/api/projects/policy?path=${encodeURIComponent(path)}`),
  setProjectPolicy: (path: string, mode: string) =>
    sendJson<{ ok: boolean; mode: string }>("/api/projects/policy", "POST", { path, mode }),
};
