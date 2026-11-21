
import { useCallback, useState } from "react";

import { api } from "../../kernel/api";
import type { InstalledPlugin, PluginCatalogEntry } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";
import { useFlash } from "../../kernel/ui/useFlash";
import { installFromCatalog } from "../../kernel/ui/plugins/installCatalog";

export interface PluginsController {
  installed: InstalledPlugin[];
  catalog: PluginCatalogEntry[];
  busy: string;
  editing: string;
  setEditing: (v: string) => void;
  load: () => Promise<void>;
  install: (p: PluginCatalogEntry) => Promise<void>;
  uninstall: (p: InstalledPlugin) => Promise<void>;
  msg: string;
  flash: (t: string, ms?: number) => void;
}

export function usePlugins(): PluginsController {
  const [installed, setInstalled] = useState<InstalledPlugin[]>([]);
  const [catalog, setCatalog] = useState<PluginCatalogEntry[]>([]);
  const [busy, setBusy] = useState("");
  const [editing, setEditing] = useState("");
  const { msg, flash, flashErr } = useFlash(4000);

  const load = useCallback(async () => {
    try {
      const [r, cat] = await Promise.all([
        api.pluginsInstalled(),
        api.pluginCatalog().catch(() => ({ plugins: [] as PluginCatalogEntry[] })),
      ]);
      setInstalled(r.installed);
      setCatalog(cat.plugins || []);
    } catch (e) {
      flashErr(`加载失败：${errText(e)}`);
    }
  }, [flash]);

  const install = useCallback(async (p: PluginCatalogEntry) => {
    setBusy(p.id);
    try {
      const r = await installFromCatalog(p);
      if (r.ok) flash(r.text); else flashErr(r.text, 6000);
      if (r.ok) await load();
    } finally {
      setBusy("");
    }
  }, [flash, load]);

  const uninstall = async (p: InstalledPlugin) => {
    setBusy(p.id);
    try {
      await api.pluginUninstall(p.id, p.project);
      flash(`✓ 已卸载 ${p.id}（文件保留）`);
      await load();
    } catch (e) {
      flashErr(`卸载失败：${errText(e)}`, 6000);
    } finally {
      setBusy("");
    }
  };

  return {
    installed, catalog, busy, editing, setEditing,
    load, install, uninstall, msg, flash,
  };
}
