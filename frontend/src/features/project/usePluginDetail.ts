
import { useCallback, useEffect, useState } from "react";

import { api } from "../../kernel/api";
import type { PluginDetail as PluginDetailData } from "../../kernel/api/types";
import { confirmDialog } from "../../kernel/ui/dialog";
import { askKeyGrants } from "../../kernel/ui/plugins/keyGrant";
import { errText } from "../../kernel/ui/errText";

export interface PluginDetail {
  plugin: PluginDetailData | null;
  error: string;
  loading: boolean;
  reload: () => Promise<void>;
  
  pluginUrl: () => string;
  
  release: () => Promise<void>;
  
  reregister: () => Promise<void>;
  busy: boolean;
  actionError: string;
}

export function usePluginDetail(hostProject: string,
                                pluginId: string): PluginDetail {
  const [plugin, setPlugin] = useState<PluginDetailData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");

  
  const hostName = hostProject.replace(/\/+$/, "").split("/").pop() || "";

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setPlugin(await api.pluginDetail(pluginId, hostName));
      setError("");
    } catch (e) {
      setError(errText(e));
    } finally {
      setLoading(false);
    }
  }, [pluginId, hostName]);

  useEffect(() => { void reload(); }, [reload]);

  const pluginUrl = useCallback(() =>
    "/api/plugin?" + new URLSearchParams(
      Object.entries({ id: pluginId, project: plugin?.project || hostName })
        .filter(([, v]) => !!v) as [string, string][]).toString(),
    [pluginId, hostName, plugin?.project]);

  const setMode = useCallback(async (mode: "dev" | "release") => {
    setBusy(true);
    setActionError("");
    try {
      await api.pluginSetMode(pluginId, mode, plugin?.project || hostName);
      await reload();
      
      window.dispatchEvent(new CustomEvent("harness:refresh-tree"));
    } catch (e) {
      setActionError(errText(e));
    } finally {
      setBusy(false);
    }
  }, [pluginId, plugin?.project, hostName, reload]);

  const release = useCallback(async () => {
    if (!(await confirmDialog({
      message: `把「${pluginId}」转为正式安装？转为正式安装后内部工作流 / skill / tool`
        + " 都会隐藏。可手工改回 plugin.yaml 的 mode。",
      okText: "转为正式安装", danger: true,
    }))) return;
    await setMode("release");
  }, [pluginId, setMode]);

  const reregister = useCallback(async () => {
    if (!(await confirmDialog({
      message: `重新安装「${pluginId}」？会先摘掉当前登记再按包内 plugin.yaml 重读，\n`
        + "用于开发模式改完代码 / 清单后生效。文件不会被删。",
      okText: "重新安装",
    }))) return;
    setBusy(true);
    setActionError("");
    try {
      const project = plugin?.project || hostName;
      
      
      
      const grants = await askKeyGrants(pluginId, plugin?.requestedProviderKeys);
      if (grants === null) {
        setActionError(`已取消重新安装 ${pluginId}（未授予密钥访问许可）`);
        return;
      }
      
      await api.pluginUninstall(pluginId, project);
      await api.pluginAdopt("plugin", pluginId, project, grants);
      await reload();
      window.dispatchEvent(new CustomEvent("harness:refresh-tree"));
    } catch (e) {
      setActionError(errText(e));
    } finally {
      setBusy(false);
    }
  }, [pluginId, plugin?.project, plugin?.requestedProviderKeys,
      hostName, reload]);

  return { plugin, error, loading, reload, pluginUrl,
           release, reregister, busy, actionError };
}
