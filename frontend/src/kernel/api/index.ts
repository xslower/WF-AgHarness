
import { configApi } from "./domains/config";
import { providersApi } from "./domains/providers";
import { sessionsApi } from "./domains/sessions";
import { projectsApi } from "./domains/projects";
import { workflowsApi } from "./domains/workflows";
import { artifactsApi } from "./domains/artifacts";
import { approvalsApi } from "./domains/approvals";
import { opsApi } from "./domains/ops";
import { presetsApi } from "./domains/presets";
import { subagentsApi } from "./domains/subagents";
import { timersApi } from "./domains/timers";

export const api = {
  ...configApi,
  ...providersApi,
  ...sessionsApi,
  ...projectsApi,
  ...workflowsApi,
  ...artifactsApi,
  ...approvalsApi,
  ...opsApi,
  ...presetsApi,
  ...subagentsApi,
  ...timersApi,
};

export * from "./types";
