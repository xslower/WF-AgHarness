
import { useCallback, useState } from "react";

import { api } from "../../kernel/api";
import type { GithubTokenStatus, McpServerCfg, McpStatusItem } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";
import { useFlash } from "../../kernel/ui/useFlash";

export interface McpController {
  servers: Record<string, McpServerCfg>;
  status: McpStatusItem[];
  github: GithubTokenStatus;
  newName: string;
  setNewName: (v: string) => void;
  
  patch: (name: string, patch: Partial<McpServerCfg>) => void;
  removeServer: (name: string) => Promise<void>;
  addServer: () => Promise<void>;
  
  save: (name: string) => Promise<void>;
  
  reconnect: (name: string) => Promise<void>;
  reload: () => Promise<void>;
  
  tokenDraft: string;
  setTokenDraft: (v: string) => void;
  saveToken: () => Promise<void>;
  testToken: () => Promise<void>;
  msg: string;
}

export function useMcpServers(): McpController {
  const [servers, setServers] = useState<Record<string, McpServerCfg>>({});
  const [status, setStatus] = useState<McpStatusItem[]>([]);
  const [github, setGithub] = useState<GithubTokenStatus>({
    configured: false, hint: "", source: "",
  });
  const [newName, setNewName] = useState("");
  const [tokenDraft, setTokenDraft] = useState("");
  const { msg, flash } = useFlash(4000);

  const reload = useCallback(async () => {
    try {
      const d = await api.mcpGet();
      setServers(d.servers);
      setStatus(d.status);
      setGithub(d.github);
    } catch (e) {
      flash(`加载失败：${errText(e)}`);
    }
  }, [flash]);

  const save = async (name: string) => {
    const cfg = servers[name];
    if (!cfg) return;
    try {
      const r = await api.mcpUpdate(name, cfg);
      flash(r.connected ? `✓ ${name} 已保存并连接`
        : `✓ 已保存，${name} 未连接${r.error ? `：${r.error}` : ""}`);
      await reload();
    } catch (e) {
      flash(`保存失败：${errText(e)}`);
    }
  };

  const reconnect = async (name: string) => {
    try {
      const r = await api.mcpReload(name);
      flash(r.connected ? `✓ ${name} 已连接` : `✗ ${name} 未连接：${r.error || "原因未知"}`);
      await reload();
    } catch (e) {
      flash(`重连失败：${errText(e)}`);
    }
  };

  const patch = (name: string, p: Partial<McpServerCfg>) =>
    setServers((s) => ({ ...s, [name]: { ...s[name], ...p } }));

  const removeServer = async (name: string) => {
    try {
      await api.mcpDelete(name);
      await reload();
      flash(`✓ 已删除 ${name}`);
    } catch (e) {
      flash(`删除失败：${errText(e)}`);
    }
  };

  const addServer = async () => {
    const n = newName.trim();
    if (!n) return;
    try {
      await api.mcpAdd({ name: n, command: "", args: [], env: {} });
      setNewName("");
      await reload();
      flash(`✓ 已新增 ${n}，填好 command 后点保存`);
    } catch (e) {
      flash(`新增失败：${errText(e)}`);
    }
  };

  const saveToken = async () => {
    try {
      const r = await api.githubSaveToken(tokenDraft.trim());
      setGithub(r);
      setTokenDraft("");
      flash(r.configured ? `✓ Token 已保存（${r.hint}）` : "✓ Token 已清空");
    } catch (e) {
      flash(`保存失败：${errText(e)}`);
    }
  };

  const testToken = async () => {
    try {
      const r = await api.githubTest();
      flash(r.ok ? `✓ Token 有效，登录名 ${r.login}` : `✗ ${r.error || "验证失败"}`);
    } catch (e) {
      flash(`测试失败：${errText(e)}`);
    }
  };

  return {
    servers, status, github, newName, setNewName, patch, removeServer, addServer,
    save, reconnect, reload, tokenDraft, setTokenDraft, saveToken, testToken, msg,
  };
}
