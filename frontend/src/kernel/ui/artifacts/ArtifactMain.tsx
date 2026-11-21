
import { CodeEditor } from "./CodeEditor";
import { RichMarkdown } from "../markdown";
import type { ReactNode } from "react";
import type { Tab, UrlBarState } from "./types";
import { Icon } from "../icons";


export interface ArtifactMainProps extends UrlBarState {
  tabs: Tab[];
  cur: Tab | null;
  active: string | null;
  setActive: (key: string | null) => void;
  closeTab: (key: string) => void;
  patchTab: (key: string, patch: Partial<Tab>) => void;
  saveTab: (key: string) => void;
  
  subAgentView?: ReactNode;
  
  workflowRunView?: ReactNode;
}

export function ArtifactMain({
  tabs, cur, active, setActive, closeTab, patchTab, saveTab,
  urlInput, setUrlInput, showUrlBar, setShowUrlBar, openUrl, subAgentView,
  workflowRunView,
}: ArtifactMainProps) {
  return (
    <>
      <div className="art-tabs">
        {tabs.map((t) => (
          
          <span key={t.key} className={`art-tab ${t.key === active ? "active" : ""}`}
            title={`${t.title}（双击关闭）`} onClick={() => setActive(t.key)}
            onDoubleClick={(e) => { e.preventDefault(); closeTab(t.key); }}>
            {t.dirty ? <span className="art-tab-dirty">●</span> : null}
            {t.conflict ? <span className="art-tab-conflict" title="文件已被外部修改（本地有未保存内容）">⚠</span> : null}
            <span className="art-tab-title">{t.title}</span>
            <button className="tab-x" title="关闭" onClick={(e) => {
              e.stopPropagation(); closeTab(t.key);
            }} onDoubleClick={(e) => e.stopPropagation()}>×</button>
          </span>
        ))}
        <button className="art-tab-btn" title="打开网址" onClick={() => setShowUrlBar(true)}><Icon name="globe" /></button>
      </div>
      {showUrlBar && (
        <div className="art-url-row">
          <input value={urlInput} placeholder="输入网址打开（如 example.com）" autoFocus
            onChange={(e) => setUrlInput(e.target.value)}
            list="url-history"
            onKeyDown={(e) => {
              if (e.key === "Enter") { openUrl(); setShowUrlBar(false); }
              if (e.key === "Escape") setShowUrlBar(false);
            }} />
          <button onClick={() => { openUrl(); setShowUrlBar(false); }} title="打开网页"><Icon name="globe" /></button>
        </div>
      )}
      {cur?.kind === "web" && !showUrlBar && (
        <div className="art-url-row" onClick={() => { setUrlInput(cur.url || ""); setShowUrlBar(true); }}>
          <input value={cur.url || ""} readOnly style={{ cursor: "pointer" }} />
          <button title="编辑地址"><Icon name="pencil" /></button>
        </div>
      )}
      <datalist id="url-history">
        {tabs.filter((t) => t.kind === "web").map((t) => (
          <option key={t.key} value={t.url} />
        ))}
      </datalist>
      {cur?.kind === "image" && (
        <div className="art-view"><img src={cur.dataurl} alt={cur.title} /></div>
      )}
      {cur?.kind === "md" && (
        <div className="art-view art-code">
          <div className="md-toolbar">
            <button className={`link ${cur.mdPreview ? "" : "on"}`} onClick={() => patchTab(cur.key, { mdPreview: false })}>编辑</button>
            <button className={`link ${cur.mdPreview ? "on" : ""}`} onClick={() => patchTab(cur.key, { mdPreview: true })}>预览</button>
            {cur.dirty && <button className="link" onClick={() => saveTab(cur.key)}>💾 保存</button>}
          </div>
          {cur.mdPreview ? (
            <div className="md-body" style={{ padding: "10px", overflow: "auto" }}><RichMarkdown text={cur.content ?? ""} raw /></div>
          ) : (
            <>
              {cur.conflict && (
                <div className="art-conflict-bar">
                  ⚠ 文件已被外部修改。你的编辑尚未保存，保存会覆盖对方的改动。
                  <button className="link" onClick={() => patchTab(cur.key, { conflict: false })}>继续编辑</button>
                </div>
              )}
              <CodeEditor
                value={cur.content ?? ""}
                ext="md"
                onChange={(v) => patchTab(cur.key, { content: v, dirty: true })}
                onBlur={() => cur.dirty && saveTab(cur.key)} />
            </>
          )}
        </div>
      )}
      {cur?.kind === "code" && (
        <div className="art-view art-code">
          {cur.conflict && (
            <div className="art-conflict-bar">
              ⚠ 这个文件已被外部修改（可能是 LLM 或其它工具）。你的编辑尚未保存，
              保存会覆盖对方的改动。
              <button className="link" onClick={() => patchTab(cur.key, { conflict: false })}>继续编辑</button>
            </div>
          )}
          <CodeEditor
            value={cur.content ?? ""}
            ext={cur.ext}
            onChange={(v) => patchTab(cur.key, { content: v, dirty: true })}
            onBlur={() => cur.dirty && saveTab(cur.key)} />
        </div>
      )}
      {cur?.kind === "text" && (
        <div className="art-view"><pre>{cur.content}</pre></div>
      )}
      {cur?.kind === "subagent" && (
        <div className="art-view"><div className="md-body">{subAgentView}</div></div>
      )}
      {cur?.kind === "workflow-run" && (
        <div className="art-view art-wfrun">{workflowRunView}</div>
      )}
      {cur?.kind === "web" && (
        <div className="art-view art-web">
          <iframe src={cur.url} title={cur.title} sandbox="allow-scripts allow-forms allow-same-origin allow-popups" />
        </div>
      )}
      {!cur && <div className="art-view dim pad8">暂无打开的标签，从左侧产出物列表点击文件或输入网址打开</div>}
    </>
  );
}
