
import { useState } from "react";

import { PluginConfigDialog } from "../../kernel/ui/plugins/PluginConfigDialog";
import { RichMarkdown } from "../../kernel/ui/markdown";
import { Icon } from "../../kernel/ui/icons";
import { baseName } from "../../kernel/ui/format";
import { usePluginDetail } from "./usePluginDetail";

interface Props {
  
  hostProject: string;
  pluginId: string;
  onBack: () => void;
  onOpenWorkflow: (project: string, name: string) => void;
}

export function PluginDetailPage(props: Props) {
  const c = usePluginDetail(props.hostProject, props.pluginId);
  const [configOpen, setConfigOpen] = useState(false);
  if (c.error && !c.plugin) {
    return (
      <div className="projhome">
        <div className="projhome-err">读取插件信息失败：{c.error}</div>
        <button onClick={() => void c.reload()}>重试</button>
      </div>
    );
  }
  if (c.loading && !c.plugin) return <div className="projhome projhome-loading">加载中…</div>;

  const p = c.plugin;
  const dev = p?.mode === "dev";
  const url = c.pluginUrl();
  const workflowNames: string[] = p?.workflows ?? [];

  return (
    <div className="projhome plugindetail">
      <header className="projhome-head">
        <div className="projhome-title">
          <button className="icon-btn" title="返回项目主页" onClick={props.onBack}>
            <Icon name="x" />
          </button>
          <span className="projhome-crumb" onClick={props.onBack}>{baseName(props.hostProject)}</span>
          <span className="projhome-crumb-sep">/</span>
          <h2>{p?.name || props.pluginId}</h2>
          <span className={`projhome-badge ${dev ? "dev" : ""}`}>
            {dev ? "开发模式" : "正式安装"}
          </span>
        </div>
        <div className="projhome-path" title={props.hostProject}>
          {props.hostProject}
        </div>
        <div className="projhome-actions">
          <button onClick={() => void c.reload()}>刷新</button>
          <button disabled={c.busy}
            title="改完代码/清单后重新读一遍登记"
            onClick={() => void c.reregister()}>重新安装</button>
          {dev && (
            <button className="danger" disabled={c.busy}
              title="转为正式安装（内部能力不对外暴露）"
              onClick={() => void c.release()}>
              {c.busy ? "转换中…" : "转为正式安装"}
            </button>
          )}
          {p?.has_page && (

            <a className="projhome-open" href={url} target="_blank" rel="noreferrer"
              title="在新页面打开插件">
              <Icon name="globe" /> 打开链接
            </a>
          )}
        </div>
        {c.error && <div className="projhome-err-inline">{c.error}</div>}
        {c.actionError && <div className="projhome-err-inline">{c.actionError}</div>}
      </header>


      <section className="projhome-sec">
        <h3>插件信息</h3>
        <div className="plugindetail-info">
          <div><span className="dim">插件 id</span><code>{props.pluginId}</code></div>
          <div><span className="dim">版本</span><span>{p?.version || "—"}</span></div>
          <div><span className="dim">模式</span><span>{dev
            ? "开发模式（改完代码点「重新安装」即时生效）"
            : "正式安装"}</span></div>
          <div><span className="dim">存储状态</span><span>{p?.state?.length
            ? p.state.join("、") : "无存档（plugin.data 为空）"}</span></div>
          {p?.desc && <div className="plugindetail-desc">{p.desc}</div>}
        </div>
      </section>

      <section className="projhome-sec">
        <h3>设置
          <button onClick={() => setConfigOpen(true)}>配置</button>
        </h3>
        <div className="projhome-hint">按插件声明的配置项保存；secret 留空表示不修改原值。
          配置值加密存在系统的 <code>agent.db</code>，插件运行时通过
          <code>plugin.config()</code> 读取。</div>
      </section>

      <PluginConfigDialog
        target={configOpen ? { id: props.pluginId, name: p?.name || props.pluginId,
          project: p?.project || props.hostProject } : null}
        onClose={() => setConfigOpen(false)}
      />

      {}
      {workflowNames.length > 0 && (
        <section className="projhome-sec">
          <h3>内部工作流 <em>{workflowNames.length}</em></h3>
          <div className="projhome-list">
            {workflowNames.map((name) => (
              <button key={name} className="projhome-row"
                onClick={() => props.onOpenWorkflow(props.hostProject, name)}>
                <span className="projhome-row-title">{name}</span>
                <span className="projhome-row-meta"><span className="projhome-row-text">插件内部</span></span>
              </button>
            ))}
          </div>
        </section>
      )}

      {p?.readme && (
        <section className="projhome-sec">
          <h3>使用说明</h3>
          <div className="projhome-plugin-readme md-body">
            <RichMarkdown text={p.readme} raw />
          </div>
        </section>
      )}
    </div>
  );
}
