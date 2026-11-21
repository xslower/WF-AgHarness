
import { api } from "../../api";
import type { PluginCatalogEntry } from "../../api";
import { errText } from "../errText";
import { askKeyGrants } from "./keyGrant";

export interface InstallOutcome {
  ok: boolean;
  
  text: string;
}


export async function installFromCatalog(p: PluginCatalogEntry): Promise<InstallOutcome> {
  if (p.error) return { ok: false, text: `无法安装 ${p.id}：${p.error}` };
  const keys = await askKeyGrants(p.id, p.requestedProviderKeys);
  if (keys === null) {
    return { ok: false, text: `已取消安装 ${p.id}（未授予密钥访问许可）` };
  }
  try {
    const r = await api.pluginInstall(p.path, "", keys);
    const n = (r.providers || []).length
      ? `，已创建 provider：${(r.providers || []).join("、")}` : "";
    return { ok: true, text: `✓ 已安装 ${p.id}${n}` };
  } catch (e) {
    return { ok: false, text: `安装 ${p.id} 失败：${errText(e)}` };
  }
}
