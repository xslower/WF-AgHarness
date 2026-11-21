
import { useEffect, useState } from "react";

import { Icon } from "../../kernel/ui/icons";
import { fmtStamp } from "../../kernel/ui/fmtDate";
import { baseName } from "../../kernel/ui/format";
import type { ConfigTarget } from "../../kernel/ui/plugins/PluginConfigDialog";
import { PluginConfigDialog } from "../../kernel/ui/plugins/PluginConfigDialog";
import { skillLabel } from "./skillName";
import { ProjectTimers } from "./ProjectTimers";
import { useProjectOverview } from "./useProjectOverview";

interface Props {
  path: string;
  onBack: () => void;
  onOpenProject: (path: string) => void;
  onOpenSession: (id: string, project: string) => void;
  onNewSession: (project: string) => void;
  onOpenWorkflow: (project: string, name: string) => void;
  
  
  onOpenPlugin: (project: string, id: string) => void;
  
  onOpenBot: (project: string, id: string) => void;
}

export function ProjectHome(props: Props) {
  const c = useProjectOverview(props.path);
  const { reload } = c;
  
  const [showUi, setShowUi] = useState(false);
  
  const [config, setConfig] = useState<ConfigTarget | null>(null);

  useEffect(() => { void reload(); }, [reload]);

  if (c.error && !c.data) {
    return (
      <div className="projhome">
        <div className="projhome-err">读取项目信息失败：{c.error}</div>
        <button onClick={() => void reload()}>重试</button>
      </div>
    );
  }
  if (!c.data) return <div className="projhome projhome-loading">加载中…</div>;

  const d = c.data;
  const gitOn = !!d.git?.enabled;
  
  
  const scanned = c.pending !== null;
  const pending = c.pending ?? { plugins: [], skills: [], tools: [], dev: [] };
  const ui = d.ui ?? {};
  
  
  const children = d.children.filter((x) => !x.pluginProject);
  
  const installableDev = pending.dev.filter((p) => !p.registered);
  const pendingCount = pending.plugins.length + pending.skills.length
    + pending.tools.length + installableDev.length;
  return (
    <div className="projhome">
      <header className="projhome-head">
        <div className="projhome-title">
          <button className="icon-btn" title="返回会话" onClick={props.onBack}>
            <Icon name="x" />
          </button>
          {d.parent && (
            <button className="projhome-crumb" onClick={() => props.onOpenProject(d.parent!)}>
              {baseName(d.parent)}
            </button>
          )}
          {d.parent && <span className="projhome-crumb-sep">/</span>}
          <h2>{d.name}</h2>
          {d.is_top && <span className="projhome-tag">顶层项目</span>}
        </div>
        <div className="projhome-path" title={d.path}>{d.path}</div>
        <div className="projhome-actions">
          {d.parent && (
            <button onClick={() => props.onOpenProject(d.parent!)}>↑ 上级项目</button>
          )}
          <button onClick={() => props.onNewSession(d.path)}>
            <Icon name="chat" /> 新建会话
          </button>
          <button onClick={() => void reload()}>刷新</button>
          <button className="icon-btn" title="扫描插件 / 未安装项"
            disabled={c.busy === "scan"} onClick={() => void c.scanPlugins()}>
            <Icon name="search" />
          </button>
          <button className={`icon-btn${showUi ? " on" : ""}`} title="显示设置"
            aria-label="显示设置" aria-expanded={showUi}
            onClick={() => setShowUi((v) => !v)}>
            <Icon name="settings" />
          </button>
        </div>
        {showUi && (
          <div className="projhome-uiprefs">
            <label className="projhome-switch">
              <input type="checkbox" checked={!!ui.hiddenPluginProjects}
                disabled={c.busy === "ui:hiddenPluginProjects"}
                onChange={(e) => void c.setUiPref("hiddenPluginProjects", e.target.checked)} />
              隐藏插件子项目
            </label>
            <label className="projhome-switch">
              <input type="checkbox" checked={!!ui.hiddenWorkflows}
                disabled={c.busy === "ui:hiddenWorkflows"}
                onChange={(e) => void c.setUiPref("hiddenWorkflows", e.target.checked)} />
              隐藏工作流
            </label>
            <label className="projhome-switch">
              <input type="checkbox" checked={gitOn}
                disabled={c.busy === "git:enabled"}
                onChange={(e) => void c.setGitEnabled(e.target.checked)} />
              用 Git 跟踪文件修改（关闭时快照走 .trash/snap/，只备份被写的文件）
            </label>
            {gitOn && (
              <div className="projhome-gitignore">
                <textarea value={c.gitignoreText} rows={6}
                  onChange={(e) => c.setGitignoreText(e.target.value)}
                  placeholder=".gitignore 内容（每行一个忽略规则）" />
                <button disabled={c.busy === "gitignore"}
                  onClick={() => void c.saveGitignore()}>保存 .gitignore</button>
              </div>
            )}
            <span className="projhome-hint">只影响显示，不影响插件加载与工作流调用。</span>
          </div>
        )}
        {c.error && <div className="projhome-err-inline">{c.error}</div>}
        {c.notice && <div className="projhome-notice-inline">{c.notice}</div>}
      </header>

      <section className="projhome-sec">
        <h3>子项目 <em>{children.length}</em></h3>
        {children.length === 0 ? (
          <div className="projhome-empty">没有子项目</div>
        ) : (
          <div className="projhome-grid">
            {children.map((x) => (
              <button key={x.path} className="projhome-card"
                onClick={() => props.onOpenProject(x.path)}>
                <Icon name="folder" />
                <span className="projhome-card-name">{x.name}</span>
                <span className="projhome-card-meta">
                  {x.children ? `${x.children} 个子项目` : "—"}
                </span>
              </button>
            ))}
          </div>
        )}
      </section>

      <div className="projhome-cols">
        <section className="projhome-sec">
          <h3>
            <label className="projhome-checkall">
              <input type="checkbox" checked={c.sessAllChecked} disabled={!d.sessions.length}
                onChange={c.toggleAllSessions} />
              会话
            </label>
            <em>{d.sessions.length}</em>
            {c.sessSel.size > 0 && (
              <span className="projhome-batch">
                {c.sessSel.size} 项
                <button className="danger" disabled={c.busy === "sessions"}
                  onClick={() => void c.removeSessions([...c.sessSel.ids])}>批量删除</button>
                <button onClick={c.sessSel.clear}>取消</button>
              </span>
            )}
          </h3>
          {d.sessions.length === 0 ? (
            <div className="projhome-empty">还没有会话，点右上「新建会话」开始</div>
          ) : (
            <div className="projhome-list">
              {d.sessions.map((s) => (
                <div key={s.id}
                  className={`projhome-row ${c.sessSel.ids.has(s.id) ? "checked" : ""}`}>
                  <input type="checkbox" className="projhome-check"
                    checked={c.sessSel.ids.has(s.id)}
                    onChange={() => c.sessSel.toggle(s.id)} />
                  <button className="projhome-row-main"
                    onClick={() => props.onOpenSession(s.id, d.path)}>
                    <span className="projhome-row-title">{s.title}</span>
                    <span className="projhome-row-meta">
                      <span className="projhome-row-text">
                        {s.message_count ? `${s.message_count} 条` : ""} {fmtStamp(s.updated_at || s.created_at)}
                      </span>
                    </span>
                  </button>
                  <button className="icon-btn projhome-del" title="删除会话"
                    onClick={() => void c.removeSessions([s.id])}>
                    <Icon name="trash" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="projhome-sec">
          <h3>
            <label className="projhome-checkall">
              <input type="checkbox" checked={c.flowAllChecked} disabled={!d.workflows.length}
                onChange={c.toggleAllFlows} />
              工作流
            </label>
            <em>{d.workflows.length}</em>
            {c.flowSel.size > 0 && (
              <span className="projhome-batch">
                {c.flowSel.size} 项
                <button className="danger" disabled={c.busy === "flows"}
                  onClick={() => void c.removeFlows([...c.flowSel.ids])}>批量删除</button>
                <button onClick={c.flowSel.clear}>取消</button>
              </span>
            )}
          </h3>
          {d.workflows.length === 0 ? (
            <div className="projhome-empty">没有工作流（侧栏项目旁的＋可创建）</div>
          ) : (
            <div className="projhome-list">
              {d.workflows.map((w) => (
                <div key={w.name}
                  className={`projhome-row ${c.flowSel.ids.has(w.name) ? "checked" : ""}`}>
                  <input type="checkbox" className="projhome-check"
                    checked={c.flowSel.ids.has(w.name)}
                    onChange={() => c.flowSel.toggle(w.name)} />
                  <button className="projhome-row-main"
                    onClick={() => props.onOpenWorkflow(d.path, w.name)}>
                    <span className="projhome-row-title">{w.name}</span>
                    <span className="projhome-row-meta">
                      <span className="projhome-row-text">{w.nodes ?? 0} 节点 · {w.status || "draft"}</span>
                    </span>
                  </button>
                  <button className="icon-btn projhome-del" title="删除工作流"
                    onClick={() => void c.removeFlows([w.name])}>
                    <Icon name="trash" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <ProjectTimers project={d.path} />

      <section className="projhome-sec">
        <h3>已安装插件 <em>{d.plugins.length}</em></h3>
        <div className="projhome-hint">
          安装不复制文件；卸载只移除安装记录，文件原样留在包里。
        </div>
        <div className="projhome-list">
          {d.plugins.length === 0 ? (
            <div className="projhome-empty">还没有安装插件</div>
          ) : d.plugins.map((p) => (
            <div key={p.id} className="projhome-row static">
              <span className="projhome-row-title">
                {p.name || p.id}
                <span className="projhome-badge">{p.project ? "本项目" : "全局"}</span>
                {p.mode === "dev" && <span className="projhome-badge">开发模式</span>}
              </span>
              <span className="projhome-row-meta">
                <span className="projhome-row-text">{p.version || ""}</span>
                {p.has_config && (
                  <button title="配置（加密保存在系统 agent.db）"
                    onClick={() => setConfig({ id: p.id, name: p.name || p.id,
                      project: p.project || "" })}>配置</button>
                )}
                <button title="打开插件独立页面"
                  onClick={() => props.onOpenPlugin(d.path, p.id)}>
                  详情
                </button>
                {p.bot && (
                  <button title="打开问答页（对话区复用系统 ChatPanel）"
                    onClick={() => props.onOpenBot(d.path, p.id)}>
                    问答
                  </button>
                )}
                {p.has_page && (
                  <a className="projhome-open" href={c.pluginUrl(p)}
                    target="_blank" rel="noreferrer" title="打开插件页面">打开</a>
                )}
                <button className="icon-btn projhome-del" title="卸载（文件保留）"
                  disabled={c.busy === p.id}
                  onClick={() => void c.removePlugin(p)}><Icon name="trash" /></button>
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="projhome-sec">
        <h3><Icon name="sparkle" /> 未安装 / 开发模式 <em>{pendingCount}</em>
          <button className="icon-btn" title="重新扫描"
            disabled={c.busy === "scan"} onClick={() => void c.scanPlugins()}>
            <Icon name="search" />
          </button>
        </h3>
        <div className="projhome-hint">
          放进 <code>.agent/plugins</code> / <code>.agent/skills</code> /
          <code>.agent/tools</code> 的项在这里安装；格式不合格的包仍可打开子项目改代码
          （Chrome 插件开发模式），改完点「重新安装」即生效。
        </div>
        <div className="projhome-list">
          {!scanned && (
            <div className="projhome-empty">
              尚未扫描，点右上角「扫描插件」或此处的重新扫描按钮
            </div>
          )}
          {scanned && pendingCount === 0 && (
            <div className="projhome-empty">扫描完成：没有待安装的项</div>
          )}
          {pending.skills.map((s) => {
            const err = c.adoptErrors[`skill:${s.name}`];
            return (
              <div key={`sk-${s.name}`} className="projhome-row static">
                <span className="projhome-row-title">{s.display || s.name}
                  <span className="projhome-badge project">Skill</span></span>
                <span className="projhome-row-meta">
                  {err && (
                    <span className="projhome-row-text projhome-row-err" title={err}>{err}</span>
                  )}
                  <button disabled={c.busy === `skill:${s.name}`}
                    onClick={() => void c.adopt("skill", s.name)}>安装</button>
                </span>
              </div>
            );
          })}
          {pending.tools.map((t) => {
            const err = t.error || c.adoptErrors[`tool:${t.name}`];
            return (
              <div key={`tl-${t.name}`} className="projhome-row static">
                <span className="projhome-row-title">{t.display || t.name}
                  <span className="projhome-badge project">Tool</span>
                  {t.unit === "dir" && <span className="projhome-badge">多文件</span>}
                </span>
                <span className="projhome-row-meta" title={err || t.desc || ""}>
                  <span className={`projhome-row-text${err ? " projhome-row-err" : ""}`}>
                    {err || t.desc || ""}
                  </span>
                  <button disabled={c.busy === `tool:${t.name}`}
                    onClick={() => void c.adopt("tool", t.name)}>安装</button>
                </span>
              </div>
            );
          })}
          {installableDev.map((p) => {
            const err = c.adoptErrors[`plugin:${p.id}`] || p.error
              || (p.errors || []).join("；");
            return (
              <div key={`dev-${p.id}`} className="projhome-row static">
                <span className="projhome-row-title">
                  {p.name || p.id}
                  <span className="projhome-badge project">插件</span>
                  <span className="projhome-badge">开发模式 · 未安装</span>
                </span>
                <span className="projhome-row-meta" title={err || ""}>
                  {}
                  <span className={`projhome-row-text${err ? " projhome-row-err" : ""}`}>
                    {err || p.version || ""}
                  </span>
                  <button onClick={() => props.onOpenProject(p.path)}>打开子项目</button>
                  <button disabled={c.busy === `plugin:${p.id}`}
                    onClick={() => void c.adopt("plugin", p.id)}>安装</button>
                </span>
              </div>
            );
          })}
        </div>
      </section>

      <section className="projhome-sec">
        <h3>工具 <em>{(d.tools ?? []).length}</em></h3>
        {(d.tools ?? []).length === 0 ? (
          <div className="projhome-empty">没有独立安装的工具</div>
        ) : (
          <div className="projhome-list">
            {(d.tools ?? []).map((t) => (
              <div key={t.id} className="projhome-row static">
                <span className="projhome-row-title">
                  {t.name || t.id}
                  <span className="projhome-badge project">工具</span>
                </span>
                <span className="projhome-row-meta" title={t.config_error || t.error || t.desc || ""}>
                  <span className={`projhome-row-text${(t.error || t.config_error) ? " projhome-row-err" : ""}`}>
                    {t.error || t.config_error || t.desc || ""}
                  </span>
                  {t.has_config && (
                    <button title="配置（加密保存在系统 agent.db）"
                      onClick={() => setConfig({ id: t.id, name: t.name || t.id,
                        project: t.project || "" })}>配置</button>
                  )}
                  <button className="icon-btn projhome-del" title="卸载（文件保留）"
                    disabled={c.busy === t.id}
                    onClick={() => void c.removeTool(t)}><Icon name="trash" /></button>
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="projhome-sec">
        <h3>Skill <em>{d.skills.length}</em></h3>
        {d.skills.length === 0 ? (
          <div className="projhome-empty">没有可用 skill</div>
        ) : (
          <div className="projhome-chips">
            {d.skills.map((s) => (
              <span key={s} className="projhome-chip" title={s}>{skillLabel(s)}</span>
            ))}
          </div>
        )}
      </section>

      <PluginConfigDialog target={config} onClose={() => setConfig(null)}
        onSaved={() => void reload()} />
    </div>
  );
}
