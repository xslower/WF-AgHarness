import type { PromptPreset } from "../types";
import { getJson, sendJson } from "../client";

export const presetsApi = {
  listPresets: () => getJson<{ presets: PromptPreset[] }>("/api/presets"),
  savePreset: (preset: PromptPreset) =>
    sendJson<{ ok: boolean; id: string }>("/api/presets", "POST", preset),
  deletePreset: (id: string) => fetch(`/api/presets/${id}`, { method: "DELETE" }),
};
