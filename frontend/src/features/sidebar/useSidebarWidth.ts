
import { resizeWidth } from "../../kernel/ui/drag";
import { useScopedWidth } from "../../kernel/ui/useScopedState";
import { scopedStore, SCOPE_TTL_MS } from "../../kernel/ui/scopedStore";


export const SIDEBAR_MIN_W = 200;
export const SIDEBAR_MAX_W = 500;

export const SIDEBAR_DEFAULT_W = 268;

const STORE_KEY = "ui.sidebarW";


export function readSidebarWidth(scope: string): number {
  const v = scopedStore.read<unknown>(scope, STORE_KEY, SCOPE_TTL_MS);
  const n = typeof v === "string" && v.trim() ? Number(v) : v;
  return typeof n === "number" && Number.isFinite(n)
    && n >= SIDEBAR_MIN_W && n <= SIDEBAR_MAX_W ? n : SIDEBAR_DEFAULT_W;
}

export function useSidebarWidth(scope: string) {
  const [sidebarW, setSidebarW] = useScopedWidth(
    scope, STORE_KEY, SIDEBAR_DEFAULT_W, SIDEBAR_MIN_W, SIDEBAR_MAX_W);

  
  const onSidebarDrag = resizeWidth({
    width: sidebarW, min: SIDEBAR_MIN_W, max: SIDEBAR_MAX_W,
    edge: "right", setWidth: setSidebarW,
  });

  return { sidebarW, setSidebarW, onSidebarDrag };
}
