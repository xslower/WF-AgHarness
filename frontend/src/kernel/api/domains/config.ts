import type { AppConfig, Settings, UtilityModels } from "../types";
import { getJson, sendJson } from "../client";

export const configApi = {
  getConfig: () => getJson<AppConfig>("/api/config"),
  
  putSettings: (s: Partial<Settings>) => sendJson<Settings>("/api/settings", "PUT", s),
  putUtility: (u: UtilityModels) => sendJson<unknown>("/api/utility", "PUT", u),
  suggestInput: (text: string, sessionId: string) =>
    sendJson<{ completion: string }>("/api/suggest_input", "POST", {
      text,
      session_id: sessionId,
    }),
};
