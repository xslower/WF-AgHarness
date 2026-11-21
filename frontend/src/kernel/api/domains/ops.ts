import type {
  Checkpoint,
  EnvEntry,
  GithubTokenStatus,
  InstalledPluginList,
  McpServerCfg,
  McpStatusItem,
  PluginCatalogEntry,
  PluginDetail,
  PluginModeResult,

  PluginScanResult,

  PluginUninstallResult,
  ProjectUiPrefs,
  UsageSummary,
} from "../types";
import type { ThemeListResponse } from "../../theme/contracts";
import { buildQuery, delJson, getJson, patchJson, sendJson } from "../client";

export const opsApi = {
  usageSummary: () => getJson<UsageSummary>("/api/usage"),
  mcpGet: (project?: string) =>
    getJson<{ servers: Record<string, McpServerCfg>; status: McpStatusItem[];
              github: GithubTokenStatus }>(
      `/api/mcp${project ? `?project=${encodeURIComponent(project)}` : ""}`),
  mcpAdd: (body: McpServerCfg & { name: string; project?: string }) =>
    sendJson<{ ok: boolean; name: string; connected: boolean; error: string }>(
      "/api/mcp", "POST", body),
  mcpUpdate: (name: string, patch: Partial<McpServerCfg>, project?: string) =>
    patchJson<{ ok: boolean; connected: boolean; error: string }>(
      `/api/mcp/${encodeURIComponent(name)}${project ? `?project=${encodeURIComponent(project)}` : ""}`,
      patch),
  mcpDelete: (name: string, project?: string) =>
    delJson<unknown>(
      `/api/mcp/${encodeURIComponent(name)}${project ? `?project=${encodeURIComponent(project)}` : ""}`),
  mcpReload: (name: string, project?: string) =>
    sendJson<{ ok: boolean; connected: boolean; error: string; error_detail: string }>(
      `/api/mcp/${encodeURIComponent(name)}/reload${project ? `?project=${encodeURIComponent(project)}` : ""}`,
      "POST"),
  githubStatus: () => getJson<GithubTokenStatus>("/api/mcp/github"),
  githubSaveToken: (token: string) =>
    sendJson<GithubTokenStatus & { ok: boolean }>("/api/mcp/github", "PUT", { token }),
  githubTest: () =>
    sendJson<{ ok: boolean; login?: string; error?: string }>("/api/mcp/github/test", "POST"),
  ckList: (ws?: string) =>
    getJson<Checkpoint[]>(`/api/checkpoints${ws ? `?ws=${encodeURIComponent(ws)}` : ""}`),
  ckCreate: (message: string, ws?: string) =>
    sendJson<unknown>(
      `/api/checkpoints?message=${encodeURIComponent(message)}${ws ? `&ws=${encodeURIComponent(ws)}` : ""}`,
      "POST",
    ),
  ckRestore: (sha: string, ws?: string) =>
    sendJson<unknown>(
      `/api/checkpoints/restore?sha=${sha}${ws ? `&ws=${encodeURIComponent(ws)}` : ""}`,
      "POST",
    ),
  envsScan: () =>
    getJson<{ bindings: { python: string; node: string }; found: EnvEntry[] }>("/api/envs"),
  envsBind: (python: string, node: string) =>
    sendJson<unknown>("/api/envs", "PUT", { python, node }),
  envsCreateVenv: (path: string, base_python = "") =>
    sendJson<{ ok: boolean; path?: string; python?: string; error?: string }>(
      "/api/envs/create_venv",
      "POST",
      { path, base_python },
    ),
  themes: () => getJson<ThemeListResponse>("/api/themes"),
  
  
  pluginsInstalled: (project = "", scope: "global" | "all" = "global") =>
    getJson<InstalledPluginList>(
      `/api/plugins/installed${buildQuery({ project, scope })}`),

  
  pluginCatalog: () => getJson<{ plugins: PluginCatalogEntry[] }>(
    "/api/plugins/catalog"),

  
  pluginSetMode: (id: string, mode: "dev" | "release", project = "") =>
    sendJson<PluginModeResult>("/api/plugins/mode", "POST",
      { id, mode, project }),

  
  pluginDetail: (id: string, project = "") =>
    getJson<PluginDetail>(
      `/api/plugins/${encodeURIComponent(id)}/detail` +
      (project ? `?project=${encodeURIComponent(project)}` : "")),



  
  pluginInstall: (source: string, project = "", grantedProviderKeys: string[] = []) =>
    sendJson<{ id: string; version: string; project: string;
               files: string[]; warnings?: string[];
               providers?: string[] }>(
      "/api/plugins/install", "POST",
      { source, project, grantedProviderKeys }),


  
  pluginUninstall: (id: string, project = "") =>
    delJson<PluginUninstallResult>(
      `/api/plugins/installed/${encodeURIComponent(id)}` +
      (project ? `?project=${encodeURIComponent(project)}` : "")),

  
  pluginScan: (project = "") =>
    getJson<PluginScanResult>(
      `/api/plugins/discover${project ? `?project=${encodeURIComponent(project)}` : ""}`),

  
  pluginAdopt: (kind: "skill" | "tool" | "plugin", name: string, project = "",
                grantedProviderKeys: string[] = []) =>
    sendJson<{ kind: string; id: string; project: string; files: string[];
               warnings?: string[] }>(
      "/api/plugins/adopt", "POST",
      { kind, name, project, grantedProviderKeys }),

  skillsDetail: () => getJson<unknown>("/api/skills/detail"),

  
  pluginConfigGet: (id: string, project = "") =>
    getJson<PluginConfigResponse>(
      `/api/plugins/config/${encodeURIComponent(id)}` +
      (project ? `?project=${encodeURIComponent(project)}` : "")),

  
  pluginConfigPut: (id: string, values: Record<string, unknown>, project = "") =>
    sendJson<PluginConfigResponse>(
      `/api/plugins/config/${encodeURIComponent(id)}` +
      (project ? `?project=${encodeURIComponent(project)}` : ""),
      "PUT", { values }),

  
  pluginCompose: (id: string, project: string, values: Record<string, unknown>) =>
    sendJson<{ ok: boolean; text: string; fields: number; workflow: string }>(
      `/api/plugins/bot/${encodeURIComponent(id)}/compose` +
      (project ? `?project=${encodeURIComponent(project)}` : ""),
      "POST", { values }),

  
  setProjectUiPrefs: (path: string, ui: ProjectUiPrefs) =>
    sendJson<{ ui: ProjectUiPrefs }>(
      `/api/projects/ui-prefs?path=${encodeURIComponent(path)}`, "PUT", ui),

  
  setProjectGitPrefs: (path: string, enabled: boolean) =>
    sendJson<{ git: { enabled: boolean } }>(
      `/api/projects/git-prefs?path=${encodeURIComponent(path)}`, "PUT", { enabled }),


  skillsInstall: (url: string, name?: string, project = "") =>
    sendJson<unknown>("/api/skills/install", "POST",
                      { url, name: name || "", project }),
  skillsDelete: (name: string, project = "") =>
    delJson<unknown>(`/api/skills/${encodeURIComponent(name)}` +
                     (project ? `?project=${encodeURIComponent(project)}` : "")),
  skillsExplore: (q: string, page: number, size: number) =>
    getJson<unknown>(
      `/api/skills/explore?q=${encodeURIComponent(q)}&page=${page}&size=${size}`,
    ),
};
