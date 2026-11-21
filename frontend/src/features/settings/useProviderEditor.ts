
import { useState, type Dispatch, type SetStateAction } from "react";

import { api } from "../../kernel/api";
import type { AppConfig, Provider, TestResult } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";
import type { SettingsDraft } from "./useSettingsDraft";

export interface ProviderEditor {
  
  editingId: string | null;
  
  editingNew: boolean;
  
  savingKey: string | null;
  
  modelEdit: string | null;
  setModelEdit: (v: string | null) => void;
  beginEdit: (p: Provider) => void;
  cancelEdit: () => void;
  addProvider: () => void;
  saveProvider: (idx: number, silent?: boolean) => Promise<Provider | null>;
  pullModels: (idx: number) => Promise<void>;
  removeProvider: (idx: number) => Promise<void>;
  
  importEnv: () => Promise<void>;
  
  saveModelSettings: (p: Provider) => Promise<boolean>;
  tests: Record<string, TestResult | "pending">;
  test: (spec: string) => Promise<void>;
}

export function useProviderEditor(s: SettingsDraft): ProviderEditor {
  const { draft, setDraft, adoptConfig, reload, flash, flashErr } = s;
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingNew, setEditingNew] = useState(false);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [modelEdit, setModelEdit] = useState<string | null>(null);
  const [tests, setTests] = useState<Record<string, TestResult | "pending">>({});

  
  const saveProvider = async (idx: number, silent = false): Promise<Provider | null> => {
    const p = draft.providers[idx];
    if (!p) return null;
    const name = (p.name || "").trim();
    const baseUrl = (p.baseUrl || "").trim();
    if (!name || !baseUrl) { flashErr("名称和接口地址必填"); return null; }
    if (!/^https?:\/\//.test(baseUrl)) {
      flashErr("接口地址要以 http:// 或 https:// 开头");
      return null;
    }
    const key = p.id || "new";
    if (savingKey) return null;          
    setSavingKey(key);
    try {
      const body = { ...p, name, baseUrl };
      delete (body as { id?: string }).id;
      const saved: Provider = p.id
        ? await api.updateProvider(p.id, body)
        : await api.addProvider(body);
      
      setDraft((d) => {
        const cp = [...d.providers];
        cp[idx] = saved;
        return { ...d, providers: cp };
      });
      setEditingId(null);
      setEditingNew(false);
      if (!silent) flash("✓ 已保存");
      await reload();
      return saved;
    } catch (e) {
      flashErr(`保存失败：${errText(e)}`);
      return null;
    } finally {
      setSavingKey(null);
    }
  };

  
  const pullModels = async (idx: number) => {
    const p = draft.providers[idx];
    if (!p) return;
    const savedP = await saveProvider(idx, true);
    if (!savedP) return;                 
    const pid = savedP.id || p.id || "";
    if (!pid) { flashErr("先保存 Provider 再拉取模型"); return; }
    setSavingKey(pid);
    try {
      const r = await api.fetchModels(pid);
      const n = Array.isArray(r?.models) ? r.models.length : 0;
      await reload();
      flash(`✓ 已拉取：当前 ${n} 个模型`);
    } catch (e) {
      flashErr(`拉取失败：${errText(e)}`, 8000);
    } finally {
      setSavingKey(null);
    }
  };

  const removeProvider = async (idx: number) => {
    const p = draft.providers[idx];
    if (!p?.id) return;
    await api.deleteProvider(p.id);
    adoptConfig(await api.getConfig());
    setEditingId(null);
    setEditingNew(false);
  };

  
  const addProvider = () => {
    setDraft((d) => ({
      ...d,
      providers: [...d.providers,
                  { id: "", name: "", baseUrl: "", apiKey: "", models: [] } as Provider],
    }));
    setEditingId(null);
    setEditingNew(true);
  };

  const test = async (spec: string) => {
    setTests((t) => ({ ...t, [spec]: "pending" }));
    try {
      const r = await api.testModel(spec);
      setTests((t) => ({ ...t, [spec]: r }));
    } catch (e) {
      setTests((t) => ({ ...t, [spec]: { ok: false, error: String(e) } }));
    }
  };

  
  const importEnv = async () => {
    flash("扫描环境变量中…");
    try {
      const r = await api.importEnvProviders();
      const ok = r.imported.filter((x) => !x.error);
      const bad = r.imported.filter((x) => x.error);
      const detail = ok.map((x) => `${x.name}:${x.models}模型`).join("、");
      flash(`✓ 导入 ${ok.length} 个（${detail}）` +
        (bad.length ? `；失败: ${bad.map((x) => x.name).join("、")}` : "") ||
        "无新 provider");
      adoptConfig(await api.getConfig());
    } catch (e) {
      flashErr(`导入失败：${errText(e)}`);
    }
  };

  
  const saveModelSettings = async (p: Provider): Promise<boolean> => {
    try {
      await api.updateProvider(p.id, p);
      adoptConfig(await api.getConfig());
      flash("✓ 模型设置已保存");
      return true;
    } catch (e) {
      flashErr(`保存失败：${errText(e)}`);
      return false;
    }
  };

  return {
    editingId, editingNew, savingKey, modelEdit, setModelEdit,
    beginEdit: (p: Provider) => { setEditingId(p.id); setEditingNew(false); },
    cancelEdit: () => { setEditingId(null); setEditingNew(false); },
    addProvider, saveProvider, pullModels, removeProvider,
    importEnv, saveModelSettings, tests, test,
  };
}


export async function removeModelFromDraft(
  setDraft: Dispatch<SetStateAction<AppConfig>>,
  providerId: string,
  modelId: string,
): Promise<boolean> {
  try {
    await api.removeModel(providerId, modelId);
  } catch {
    return false;
  }
  setDraft((d) => {
    const providers = [...d.providers];
    const pi = providers.findIndex((x) => x.id === providerId);
    if (pi < 0) return d;
    providers[pi] = {
      ...providers[pi],
      models: providers[pi].models.filter((x) => x.id !== modelId),
    };
    
    const spec = `${providers[pi].name}/${modelId}`;
    const strip = (arr: string[]) => arr.filter((s) => s !== spec);
    return {
      ...d, providers,
      queues: {
        ...d.queues,
        parent: strip(d.queues.parent),
        child: strip(d.queues.child),
        summary: strip(d.queues.summary ?? []),
      },
    };
  });
  return true;
}
