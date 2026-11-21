
import type {
  ExternalThemeManifest,
  ThemeLayout,
  ThemeManifest,
  ThemeTokens,
} from "./contracts";
import { BUILTIN_THEMES } from "./presets";

export interface Identified {
  id: string;
}

export class PluginRegistry<T extends Identified> {
  private items = new Map<string, T>();
  private frozen = false;

  constructor(public readonly name: string) {}

  register(item: T): T {
    if (this.frozen) throw new Error(`${this.name} 已冻结，禁止运行期注册`);
    if (!item.id) throw new Error(`${this.name} 注册项缺少 id`);
    if (this.items.has(item.id)) throw new Error(`${this.name} 重复注册: ${item.id}`);
    this.items.set(item.id, item);
    return item;
  }

  get(id: string): T | undefined {
    return this.items.get(id);
  }

  all(): T[] {
    return [...this.items.values()];
  }

  getOrFirst(id: string): T | undefined {
    return this.get(id) ?? this.all()[0];
  }

  freeze(): void {
    this.frozen = true;
  }
}


export function normalizeExternalTheme(
  raw: ExternalThemeManifest,
  fallback: ThemeManifest,
): ThemeManifest {
  const tokens: ThemeTokens = { ...fallback.tokens, ...(raw.tokens ?? {}) };
  const layout: ThemeLayout = { ...fallback.layout, ...(raw.layout ?? {}) };
  if (!["compact", "cozy", "comfortable"].includes(layout.density)) {
    layout.density = fallback.layout.density;
  }
  if (!["classic", "split", "focus"].includes(layout.preset)) {
    layout.preset = fallback.layout.preset;
  }
  return {
    id: raw.id,
    name: raw.name || raw.id,
    description: raw.description ?? "",
    tokens,
    layout,
    version: raw.version,
    source: raw.source,
  };
}


export function createThemeRegistry(extra: ThemeManifest[] = []): PluginRegistry<ThemeManifest> {
  const registry = new PluginRegistry<ThemeManifest>("themes");
  for (const theme of [...BUILTIN_THEMES, ...extra]) {
    if (!theme.id || registry.get(theme.id)) continue;
    registry.register(theme);
  }
  registry.freeze();
  return registry;
}


export const themeRegistry = createThemeRegistry();
