
import { useCallback } from "react";
import { useScopedState } from "../../kernel/ui/useScopedState";
import type { PanelSetters } from "./panelToggles";


const DEFAULTS = {
  palette: true,
  code: false,
  chat: true,
  inspector: true,
  log: true,      
};

export type PanelVisibility = typeof DEFAULTS;

export function usePanelVisibility(scope: string) {
  
  
  const [show, setShow] = useScopedState<PanelVisibility>(scope, "wf.panels", DEFAULTS);

  
  const setVisible = useCallback((panel: keyof PanelVisibility, open: boolean) => {
    setShow((s) => (s[panel] === open ? s : { ...s, [panel]: open }));
  }, []);

  
  const apply = useCallback((patch: Partial<PanelVisibility>) => {
    setShow((s) => ({ ...s, ...patch }));
  }, []);

  
  const setters = {
    palette: [show.palette, (fn: (v: boolean) => boolean) =>
      setShow((s) => ({ ...s, palette: fn(s.palette) }))],
    code: [show.code, (fn: (v: boolean) => boolean) =>
      setShow((s) => ({ ...s, code: fn(s.code) }))],
    chat: [show.chat, (fn: (v: boolean) => boolean) =>
      setShow((s) => ({ ...s, chat: fn(s.chat) }))],
    inspector: [show.inspector, (fn: (v: boolean) => boolean) =>
      setShow((s) => ({ ...s, inspector: fn(s.inspector) }))],
    log: [show.log, (fn: (v: boolean) => boolean) =>
      setShow((s) => ({ ...s, log: fn(s.log) }))],
  } as PanelSetters;

  return { show, setVisible, apply, setters };
}
