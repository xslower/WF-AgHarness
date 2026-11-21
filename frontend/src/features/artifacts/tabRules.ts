
import type { Tab } from "../../kernel/ui/artifacts/types";


export function pushTab(tabs: Tab[], tab: Tab): Tab[] {
  return tabs.some((t) => t.key === tab.key) ? tabs : [...tabs, tab];
}


export function closeTabIn(tabs: Tab[], key: string,
                           active: string | null): { tabs: Tab[]; active: string | null } {
  const rest = tabs.filter((t) => t.key !== key);
  if (active !== key) return { tabs: rest, active };

  return { tabs: rest, active: rest[rest.length - 1]?.key ?? null };
}


export function patchTabIn(tabs: Tab[], key: string, patch: Partial<Tab>): Tab[] {
  return tabs.map((t) => (t.key === key ? { ...t, ...patch } : t));
}


export function normalizeUrl(raw: string): string | null {
  const u = raw.trim();
  if (!u) return null;
  return /^https?:\/\//.test(u) ? u : null;
}


export function urlTab(url: string): Tab {
  return {
    key: url,
    title: url.replace(/^https?:\/\//, ''),
    kind: "web",
    url,
  };
}
