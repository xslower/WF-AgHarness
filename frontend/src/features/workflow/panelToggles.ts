
import type { PanelKey } from "./EditorToolbar";

export type PanelSetters = Record<Exclude<PanelKey, "llm">, [boolean, (fn: (v: boolean) => boolean) => void]>;


export function togglePanel(panel: string, setters: PanelSetters): boolean {
  const hit = (setters as Record<string, unknown>)[panel];
  if (!hit) return false;
  const [, set] = setters[panel as Exclude<PanelKey, "llm">];
  set((v) => !v);
  return true;
}


export function openPanel(panel: Exclude<PanelKey, "llm">, setters: PanelSetters, open = true): void {
  const [, set] = setters[panel];
  set(() => open);
}
