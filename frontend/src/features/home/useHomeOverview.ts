
import { useCallback, useState } from "react";

import { api } from "../../kernel/api";
import type { InstalledPlugin, PluginCatalogEntry, WorkflowSummary } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";
import { installFromCatalog } from "../../kernel/ui/plugins/installCatalog";

export interface HomeController {
  flows: WorkflowSummary[];
  plugins: InstalledPlugin[];
  
  catalog: PluginCatalogEntry[];
  loading: boolean;
  busy: string;
  notice: string;
  reload: () => Promise<void>;
  installGlobal: (p: PluginCatalogEntry) => Promise<void>;
  
  uninstallGlobal: (p: PluginCatalogEntry) => Promise<void>;
}

export function useHomeOverview(): HomeController {
  const [flows, setFlows] = useState<WorkflowSummary[]>([]);
  const [plugins, setPlugins] = useState<InstalledPlugin[]>([]);
  const [catalog, setCatalog] = useState<PluginCatalogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setNotice("");
    try {
      const [wf, pl, cat] = await Promise.all([
        api.wfList("").catch(() => [] as WorkflowSummary[]),
        api.pluginsInstalled().catch(() => ({ installed: [] as InstalledPlugin[], project: null })),
        api.pluginCatalog().catch(() => ({ plugins: [] as PluginCatalogEntry[] })),
      ]);
      setFlows(wf.filter((w) => (w.status || "draft") === "published"));
      setPlugins(pl.installed || []);
      setCatalog(cat.plugins || []);
    } catch (e) {
      setNotice(errText(e));
    } finally {
      setLoading(false);
      setBusy("");
    }
  }, []);

  
  const installGlobal = useCallback(async (p: PluginCatalogEntry) => {
    setBusy(p.id);
    try {
      const r = await installFromCatalog(p);
      setNotice(r.ok ? r.text : `✗ ${r.text}`);
      if (r.ok) await reload();
    } finally {
      setBusy("");
    }
  }, [reload]);

  
  const uninstallGlobal = useCallback(async (p: PluginCatalogEntry) => {
    setBusy(p.id);
    try {
      await api.pluginUninstall(p.id, "");
      setNotice(`已卸载 ${p.id}（文件保留）`);
      await reload();
      window.dispatchEvent(new CustomEvent("harness:refresh-tree"));
    } catch (e) {
      setNotice(`卸载失败：${errText(e)}`);
    } finally {
      setBusy("");
    }
  }, [reload]);

  return { flows, plugins, catalog, loading, busy, notice, reload,
           installGlobal, uninstallGlobal };
}
