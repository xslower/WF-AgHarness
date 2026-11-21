
import { useEffect } from "react";

import type { ProjectNode } from "../../kernel/api";
import { Icon } from "../../kernel/ui/icons";
import { useHomeOverview } from "./useHomeOverview";

interface Props {
  projTree: ProjectNode | null;
  onOpenProjectHome: (path: string) => void;
  onOpenWorkflow: (project: string, name: string) => void;
  onNewSession: (project: string) => void;
}

export function HomeView(props: Props) {
  const c = useHomeOverview();
  const { reload } = c;

  useEffect(() => { void reload(); }, [reload]);

  const tops = (props.projTree?.children ?? []).filter((x) => x.depth <= 1);
  const installed = c.catalog.filter((p) => p.installed);
  const pending = c.catalog.filter((p) => !p.installed);

  return (
    <div className="projhome home-view">
      <header className="projhome-head">
        <div className="projhome-title">
          <h2><Icon name="sparkle" /> WF-AgHarness</h2>
          <span className="projhome-tag">全局总览</span>
        </div>
        <div className="projhome-actions">
          <button onClick={() => void reload()}>刷新</button>
        </div>
        {c.notice && <div className="projhome-err-inline">{c.notice}</div>}
      </header>

      <section className="projhome-sec">
        <h3>项目 <em>{tops.length}</em></h3>
        {tops.length === 0 ? (
          <div className="projhome-empty">还没有项目，用侧栏「📁」注册一个目录</div>
        ) : (
          <div className="projhome-grid">
            {tops.map((x) => (
              <button key={x.path} className="projhome-card" title={x.path}
                onClick={() => props.onOpenProjectHome(x.path)}>
                <Icon name="folder" />
                <span className="projhome-card-name">{x.name}</span>
                <span className="projhome-card-meta">
                  {x.children.length ? `${x.children.length} 个子项目` : "—"}
                </span>
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="projhome-sec">
        <h3>全局工作流 <em>{c.flows.length}</em>
          <span className="dim projhome-hint-inline">只列已发布的（草稿在全局工作流页里编辑）</span>
        </h3>
        {c.flows.length === 0 ? (
          <div className="projhome-empty">
            还没有已发布的全局工作流。在「全局工作流」里编辑后点「发布」才会出现在这里。
          </div>
        ) : (
          <div className="projhome-grid">
            {c.flows.map((w) => (
              <button key={w.name} className="projhome-card" title={w.desc || w.name}
                onClick={() => props.onOpenWorkflow("", w.name)}>
                <Icon name="workflow" />
                <span className="projhome-card-name">{w.name}</span>
                <span className="projhome-card-meta">{w.nodes} 节点</span>
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="projhome-sec">
        <h3>全局插件 <em>{c.catalog.length}</em></h3>
        <div className="projhome-hint">
          源码根 <code>plugins/</code> 下的全局插件，安装不复制文件、卸载只移除安装记录；
          项目专属插件在项目主页里安装与管理。
        </div>

        <div className="q-title">已安装 <em>{installed.length}</em></div>
        {installed.length === 0 ? (
          <div className="projhome-empty">还没有安装全局插件</div>
        ) : (
          <div className="projhome-list">
            {installed.map((p) => <PluginCard key={p.path} p={p} c={c} />)}
          </div>
        )}

        <div className="q-title">待安装 <em>{pending.length}</em></div>
        {pending.length === 0 ? (
          <div className="projhome-empty">没有待安装的全局插件</div>
        ) : (
          <div className="projhome-list">
            {pending.map((p) => <PluginCard key={p.path} p={p} c={c} />)}
          </div>
        )}
      </section>

    </div>
  );
}


function PluginCard({ p, c }: {
  p: ReturnType<typeof useHomeOverview>["catalog"][number];
  c: ReturnType<typeof useHomeOverview>;
}) {
  return (
    <div className="projhome-row static plugincard" title={p.path}>
      <span className="projhome-row-title">
        {p.name}
        <span className="projhome-badge">{p.installed ? "已安装" : "未安装"}</span>
        {p.kinds.map((k) => <span key={k} className="projhome-badge project">{k}</span>)}
      </span>
      <span className="plugincard-desc">{p.error || p.desc || p.version}</span>
      <span className="plugincard-actions">
        {!p.installed ? (
          <button disabled={c.busy === p.id || !!p.error}
            onClick={() => void c.installGlobal(p)}>
            {c.busy === p.id ? "安装中…" : "安装"}
          </button>
        ) : (
          <button className="danger" disabled={c.busy === p.id}
            title="只移除安装记录，文件保留；配置在设置页「插件」"
            onClick={() => void c.uninstallGlobal(p)}>
            {c.busy === p.id ? "卸载中…" : "卸载"}
          </button>
        )}
      </span>
    </div>
  );
}
