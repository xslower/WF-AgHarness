
import { useEffect } from "react";

import type { InstalledPlugin } from "../../kernel/api";
import { Icon } from "../../kernel/ui/icons";
import { PluginConfigDialog } from "../../kernel/ui/plugins/PluginConfigDialog";
import { usePlugins } from "./usePlugins";
import { baseName } from "../../kernel/ui/format";

export function PluginsTab() {
  const c = usePlugins();
  
  const editing = c.installed.find((p) => p.id === c.editing) ?? null;

  useEffect(() => { void c.load(); }, [c.load]);

  return (
    <div className="panel">
      <div className="dim">
        安装不复制文件；卸载只移除安装记录，文件原样留在包里。
        配置由插件的 <code>plugin.yaml</code> 声明自动生成。
      </div>
      {c.msg && <div className="notice">{c.msg}</div>}

      <div className="q-title" style={{ marginTop: 16 }}>
        全局插件目录 <em>{c.catalog.length}</em>
      </div>
      <div className="dim">源码根 <code>plugins/</code> 下的包；装进去只是登记，不复制文件。</div>
      {c.catalog.map((p) => (
        <div key={p.path} className="provider-card">
          <div className="row" style={{ alignItems: "center", flexWrap: "wrap", gap: 8 }}>
            <b>{p.name}</b>
            <span className="dim">v{p.version}</span>
            <span className={p.installed ? "projhome-badge" : "projhome-badge project"}>
              {p.installed ? "已安装" : "未安装"}
            </span>
            {p.kinds.map((k) => <span key={k} className="projhome-badge project">{k}</span>)}
            <span className="dim" title={p.path}>{p.error || p.desc}</span>
            {!p.installed && (
              <button disabled={c.busy === p.id || !!p.error}
                onClick={() => void c.install(p)}>
                {c.busy === p.id ? "安装中…" : "安装"}
              </button>
            )}
          </div>
        </div>
      ))}
      {c.catalog.length === 0 && (
        <div className="dim pad8">plugins/ 目录里没有插件包</div>
      )}

      <div className="q-title" style={{ marginTop: 16 }}>
        已安装记录 <em>{c.installed.length}</em>
      </div>
      {c.installed.length === 0 && (
        <div className="dim pad8">还没有安装插件。把包放进项目的
          <code>.agent/plugins/</code>，在项目主页点「安装」。</div>
      )}

      {c.installed.map((p) => (
        <div key={`${p.project}/${p.id}`} className="provider-card">
          <div className="row" style={{ alignItems: "center", flexWrap: "wrap", gap: 8 }}>
            <b>{p.id}</b>
            <span className="dim">v{p.version}</span>
            <span className={p.project ? "projhome-badge project" : "projhome-badge"}>
              {p.project ? baseName(p.project) : "全局"}
            </span>
            <span className="dim" title={p.source}>来源：{shortSource(p.source)}</span>
            <button onClick={() => c.setEditing(p.id)}>配置</button>
            <button className="icon-btn" title="卸载（文件保留）"
              disabled={c.busy === p.id}
              onClick={() => void c.uninstall(p)}><Icon name="trash" /></button>
          </div>
        </div>
      ))}

      <PluginConfigDialog
        target={editing ? { id: editing.id, name: editing.id,
          project: editing.project || "" } : null}
        onClose={() => c.setEditing("")}
        onSaved={() => void c.load()}
      />
    </div>
  );
}


function shortSource(src: string): string {
  const parts = src.split(/[\\/]/).filter(Boolean);
  return parts.slice(-2).join("/") || src;
}
