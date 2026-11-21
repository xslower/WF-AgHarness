
import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "../../kernel/api";
import type { ProjectOverview, ProjectUiPrefs } from "../../kernel/api/types";
import type { PluginScanResult } from "../../kernel/api/types/plugin";
import { confirmDialog } from "../../kernel/ui/dialog";
import { askKeyGrants } from "../../kernel/ui/plugins/keyGrant";
import { errText } from "../../kernel/ui/errText";
import { baseName } from "../../kernel/ui/format";

import { useSelection, type Selection } from "../../kernel/ui/useSelection";

export interface ProjectController {
  data: ProjectOverview | null;
  error: string;
  busy: string;
  notice: string;
  reload: () => Promise<void>;
  sessSel: Selection;
  flowSel: Selection;
  sessAllChecked: boolean;
  flowAllChecked: boolean;
  toggleAllSessions: () => void;
  toggleAllFlows: () => void;
  
  removePlugin: (p: ProjectOverview["plugins"][number]) => Promise<void>;
  
  removeTool: (t: ProjectOverview["tools"][number]) => Promise<void>;
  
  adopt: (kind: "skill" | "tool" | "plugin", name: string) => Promise<void>;
  
  adoptErrors: Record<string, string>;
  
  reregister: (id: string) => Promise<void>;
  
  setUiPref: (key: keyof ProjectUiPrefs, value: boolean) => Promise<void>;
  
  setGitEnabled: (enabled: boolean) => Promise<void>;
  
  gitignoreText: string;
  setGitignoreText: (text: string) => void;
  saveGitignore: () => Promise<void>;
  
  pending: PluginScanResult | null;
  scanPlugins: () => Promise<void>;
  
  pluginUrl: (p: ProjectOverview["plugins"][number]) => string;
  removeSessions: (ids: string[]) => Promise<void>;
  removeFlows: (names: string[]) => Promise<void>;
  projectPlugins: ProjectOverview["plugins"];
  globalPlugins: ProjectOverview["plugins"];
}

export function useProjectOverview(path: string): ProjectController {
  const [data, setData] = useState<ProjectOverview | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");
  const [pending, setPending] = useState<PluginScanResult | null>(null);
  const [adoptErrors, setAdoptErrors] = useState<Record<string, string>>({});
  const [gitignoreText, setGitignoreText] = useState("");
  const sessSel = useSelection();
  const flowSel = useSelection();

  
  useEffect(() => {
    setPending(null);
    setNotice("");
    setAdoptErrors({});
  }, [path]);

  const pluginUrl = useCallback(
    (p: ProjectOverview["plugins"][number]) =>
      
      "/api/plugin?" + new URLSearchParams(
        Object.entries({ id: p.id, project: p.project || baseName(path) })
          .filter(([, v]) => !!v) as [string, string][]).toString(),
    [path]);

  const reload = useCallback(async () => {
    try {
      setError("");
      const next = await api.projectOverview(path);
      setData(next);
      sessSel.keepOnly(next.sessions.map((s) => s.id));
      flowSel.keepOnly(next.workflows.map((w) => w.name));
    } catch (e) {
      setError(errText(e));
    }
    
  }, [path]);

  const scanPlugins = async () => {
    setBusy("scan");
    try {
      
      const found = await api.pluginScan(path);
      setPending(found);
      setAdoptErrors({});
      const n = found.plugins.length + found.skills.length
        + found.tools.length + found.dev.length;
      setNotice(n ? `扫描完成：发现 ${n} 项待安装 / 开发模式包` : "扫描完成：没有待安装的项");
    } catch (e) {
      setNotice(`扫描失败：${errText(e)}`);
    } finally {
      setBusy("");
    }
  };

  const removePlugin = async (p: ProjectOverview["plugins"][number]) => {
    setBusy(p.id);
    try {
      
      
      await api.pluginUninstall(p.id, p.project || "");
      setNotice(`已卸载 ${p.name || p.id}（文件保留）`);
      await reload();
    } catch (e) {
      setNotice(`卸载失败：${errText(e)}`);
    } finally {
      setBusy("");
    }
  };

  const removeTool = async (t: ProjectOverview["tools"][number]) => {
    setBusy(t.id);
    try {
      await api.pluginUninstall(t.id, t.project || "");
      setNotice(`已卸载工具 ${t.name || t.id}（文件保留）`);
      await reload();
    } catch (e) {
      setNotice(`卸载失败：${errText(e)}`);
    } finally {
      setBusy("");
    }
  };

  const adopt = async (kind: "skill" | "tool" | "plugin", name: string) => {
    const key = `${kind}:${name}`;
    setBusy(key);
    setAdoptErrors((prev) => {
      if (!(key in prev)) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
    try {
      
      
      const dev = pending?.dev.find((x) => x.id === name);
      const tool = pending?.tools.find((x) => x.name === name);
      const installed = data?.plugins.find((x) => x.id === name);
      const requested = dev?.requestedProviderKeys
        ?? tool?.requestedProviderKeys
        ?? installed?.requestedProviderKeys ?? [];
      const grants = await askKeyGrants(name, requested);
      if (grants === null) {
        setNotice(`已取消安装 ${name}（未授予密钥访问许可）`);
        return;
      }
      await api.pluginAdopt(kind, name, path, grants);
      setNotice(`✓ 已安装 ${kind}「${name}」（不复制文件）`);
      
      
      
      setPending((prev) => {
        if (!prev) return prev;
        
        
        const drop = <T extends { id?: string; name?: string }>(arr: T[]) =>
          arr.filter((x) => (x.id ?? x.name) !== name);
        return { plugins: drop(prev.plugins), skills: drop(prev.skills),
                 tools: drop(prev.tools), dev: drop(prev.dev) };
      });
      await reload();
    } catch (e) {
      const why = errText(e);
      setNotice(`安装失败：${why}`);
      setAdoptErrors((prev) => ({ ...prev, [key]: why }));
    } finally {
      setBusy("");
    }
  };

  const reregister = async (id: string) => {
    setBusy(`dev:${id}`);
    try {
      const dev = pending?.dev.find((x) => x.id === id);
      const installed = data?.plugins.find((x) => x.id === id);
      const requested = dev?.requestedProviderKeys
        ?? installed?.requestedProviderKeys ?? [];
      const grants = await askKeyGrants(id, requested);
      if (grants === null) {
        setNotice(`已取消安装 ${id}（未授予密钥访问许可）`);
        return;
      }
      if (dev?.registered) await api.pluginUninstall(id, path);
      await api.pluginAdopt("plugin", id, path, grants);
      setNotice(`✓ 插件「${id}」已安装`);
      
      setPending((prev) => prev && {
        ...prev,
        dev: prev.dev.map((x) => (x.id === id ? { ...x, registered: true, errors: [] } : x)),
      });
      await reload();
    } catch (e) {
      setNotice(`安装失败：${errText(e)}`);
    } finally {
      setBusy("");
    }
  };

  const setUiPref = async (key: keyof ProjectUiPrefs, value: boolean) => {
    setBusy(`ui:${key}`);
    try {
      await api.setProjectUiPrefs(path, { [key]: value });
      await reload();
    } catch (e) {
      setNotice(`设置失败：${errText(e)}`);
    } finally {
      setBusy("");
    }
  };

  const setGitEnabled = async (enabled: boolean) => {
    setBusy("git:enabled");
    try {
      await api.setProjectGitPrefs(path, enabled);
      await reload();
    } catch (e) {
      setNotice(`设置失败：${errText(e)}`);
    } finally {
      setBusy("");
    }
  };

  useEffect(() => {
    if (!data?.git?.enabled) return;
    api.filePreview(`${path}/.gitignore`).then((r) => {
      setGitignoreText(r.content ?? "");
    }).catch(() => setGitignoreText(""));
  }, [data?.git?.enabled, path]);

  const saveGitignore = async () => {
    setBusy("gitignore");
    try {
      await api.fileSave(".gitignore", gitignoreText, path);
      setNotice(".gitignore 已保存");
    } catch (e) {
      setNotice(`保存 .gitignore 失败：${errText(e)}`);
    } finally {
      setBusy("");
    }
  };

  const removeSessions = async (ids: string[]) => {
    if (!ids.length) return;
    const ok = await confirmDialog({
      title: "删除会话", danger: true, okText: "删除",
      message: `确认删除选中的 ${ids.length} 个会话？消息与草稿一并删除。`,
    });
    if (!ok) return;
    setBusy("sessions");
    try {
      for (const id of ids) await api.deleteSession(id);
      sessSel.clear();
      await reload();
    } catch (e) {
      setError(`删除会话失败：${errText(e)}`);
      await reload();
    } finally {
      setBusy("");
    }
  };

  const removeFlows = async (names: string[]) => {
    if (!names.length) return;
    const ok = await confirmDialog({
      title: "删除工作流", danger: true, okText: "删除",
      message: `确认删除选中的 ${names.length} 个工作流？`,
    });
    if (!ok) return;
    setBusy("flows");
    try {
      for (const name of names) await api.wfDelete(name, path);
      flowSel.clear();
      await reload();
    } catch (e) {
      setError(`删除工作流失败：${errText(e)}`);
      await reload();
    } finally {
      setBusy("");
    }
  };

  const sessAllChecked = useMemo(
    () => !!data?.sessions.length && sessSel.size === data.sessions.length,
    [data?.sessions, sessSel.size]);
  const flowAllChecked = useMemo(
    () => !!data?.workflows.length && flowSel.size === data.workflows.length,
    [data?.workflows, flowSel.size]);

  const toggleAllSessions = () => {
    if (!data) return;
    if (sessAllChecked) { sessSel.clear(); return; }
    data.sessions.forEach((s) => { if (!sessSel.ids.has(s.id)) sessSel.toggle(s.id); });
  };
  const toggleAllFlows = () => {
    if (!data) return;
    if (flowAllChecked) { flowSel.clear(); return; }
    data.workflows.forEach((w) => { if (!flowSel.ids.has(w.name)) flowSel.toggle(w.name); });
  };

  const projectPlugins = useMemo(
    () => (data?.plugins ?? []).filter((p) => p.project), [data?.plugins]);
  const globalPlugins = useMemo(
    () => (data?.plugins ?? []).filter((p) => !p.project), [data?.plugins]);

  return {
    data, error, busy, notice, reload, pending, sessSel, flowSel,
    sessAllChecked, flowAllChecked, toggleAllSessions, toggleAllFlows,
    removePlugin, removeTool, adopt, adoptErrors, reregister, setUiPref, scanPlugins, pluginUrl,
    setGitEnabled, gitignoreText, setGitignoreText, saveGitignore,
    removeSessions, removeFlows, projectPlugins, globalPlugins,
  };
}
