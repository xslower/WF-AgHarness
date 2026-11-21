import type { ArtifactList, FilePreview, RecentFiles, TrashInfo } from "../types";
import { getJson, sendJson } from "../client";


const withProject = (path: string, project: string) =>
  project ? { path, project } : { path };

export const artifactsApi = {
  artifacts: (project: string) =>
    getJson<ArtifactList>(`/api/artifacts?project=${encodeURIComponent(project)}`),

  
  recentFiles: (project: string, limit = 50, rev?: number) =>
    getJson<RecentFiles>(
      `/api/artifacts/recent?project=${encodeURIComponent(project)}&limit=${limit}`
        + (rev === undefined ? "" : `&rev=${rev}`),
    ),
  
  recentTouch: (project: string, path: string) =>
    sendJson<{ ok: boolean; rev: number }>("/api/artifacts/recent", "POST",
      { project, path }),

  filePreview: (path: string) =>
    getJson<FilePreview>(`/api/file?path=${encodeURIComponent(path)}`),
  fileDelete: (path: string, project = "") =>
    sendJson<unknown>("/api/file/delete", "POST", withProject(path, project)),
  fileMove: (path: string, dest: string, project = "") =>
    sendJson<unknown>("/api/file/move", "POST", { ...withProject(path, project), dest }),
  fileCopy: (path: string, dest: string, project = "") =>
    sendJson<unknown>("/api/file/copy", "POST", { ...withProject(path, project), dest }),
  fileSave: (path: string, content: string, project = "") =>
    sendJson<unknown>("/api/file/save", "POST", { ...withProject(path, project), content }),

  
  trashInfo: (project: string) =>
    getJson<TrashInfo>(`/api/trash?project=${encodeURIComponent(project)}`),
  
  trashPurge: (project: string, days = 0) =>
    sendJson<{ ok: boolean; removed: number; freed_bytes: number; kept: number }>(
      "/api/trash/purge", "POST", { project, days }),
};
