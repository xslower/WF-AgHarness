
import { memo } from "react";
import type { AppConfig, ChatMessage } from "../../api";
import { specLabel } from "../../model/modelSpec";
import { Icon } from "../icons";
import { CopyButton } from "../CopyButton";
import { extractText, RichMarkdown } from "../markdown";
import { toolLabel } from "./toolLabel";
import { runIdFromResult } from "../../chat/workflowRunTab";
import { OpenRunButton } from "./OpenRunButton";


function userCopyText(m: ChatMessage): string {
  const raw = typeof m.content === "string" ? m.content : extractText(m.content);
  return raw.replace(
    /^\s*now[:：]\s*(?:\d{4}年\d{1,2}月\d{1,2}日\s*)?\d{1,2}时\d{1,2}分[ \t]*\n*/, "");
}


function parseToolArgs(raw: unknown): unknown {
  if (typeof raw !== "string") return raw ?? {};
  try { return JSON.parse(raw); } catch { return {}; }
}

export const MessageRow = memo(function MessageRow({
  m, config, toolResults, onEdit,
}: {
  m: ChatMessage;
  config: AppConfig | null;
  toolResults: Map<string, ChatMessage>;
  
  onEdit: (m: ChatMessage) => void;
}) {
  
  if (m.role === "tool") return null;
  
  if (m.role === "assistant" && !m.reasoning && !m.tool_calls?.length) {
    const text = typeof m.content === "string" ? m.content.trim()
      : Array.isArray(m.content) ? extractText(m.content).trim() : "";
    if (!text) return null;
  }
  return (
    <div className={`msg ${m.role}${m._sys === "resume" ? " msg-sys" : ""}`}>
      <div className="msg-role">
        {m.role === "user"
          ? (m._sys === "resume" ? "计划" : "你")
          : `助手${m.model ? ` · ${specLabel(config, m.model)}` : ""}`}
        {m.role === "user" && !m._sys && (
          <>
            <CopyButton text={userCopyText(m)} className="link copy-btn"
              label="复制我发的消息" />
            <button className="link edit-btn" title="编辑并回滚上下文到此处"
              onClick={() => onEdit(m)}>✎</button>
          </>
        )}
      </div>

      {m.role === "assistant" && m.reasoning ? (
        <details className="tool-block reasoning-block">
          <summary><Icon name="thought" /> 思考过程</summary>
          <pre className="wrap">{m.reasoning}</pre>
        </details>
      ) : null}
      {m.role === "assistant" && m.tool_calls?.length ? (
        <div className="tool-blocks">
          {m.tool_calls.map((tc) => {
            
            
            const label = toolLabel(tc.function.name, parseToolArgs(tc.function.arguments));
            const tr = toolResults.get(tc.id);
            const out = tr
              ? (typeof tr.content === "string" ? tr.content : JSON.stringify(tr.content))
              : "";
            
            
            const wfRunId = tc.function.name === "workflow" ? runIdFromResult(out) : "";
            return (
              <details key={tc.id} className="tool-block">
                <summary><Icon name="wrench" /> {label.title}
                  {label.detail && <span className="tool-detail"> {label.detail}</span>}
                  {wfRunId ? (
                    <OpenRunButton runId={wfRunId}
                      workflow={(parseToolArgs(tc.function.arguments) as { name?: string })?.name || ""} />
                  ) : null}
                </summary>
                <pre>{tc.function.arguments}</pre>
                {}
                {tr ? <pre className="tool-result">{out}</pre> : null}
              </details>
            );
          })}
        </div>
      ) : null}
      {m._sys === "resume" ? (
        
        
        <div className="notice">
          ⇄ {(typeof m.content === "string" ? m.content : extractText(m.content))
            .replace(/^\[[^\]]+\]\s*/, "")}
        </div>
      ) : m.role === "user" && Array.isArray(m.content) ? (

        <div className="msg-body">
          <pre className="wrap">{extractText(m.content)}</pre>
          <div className="att-imgs">
            {m.content.filter((p) => p.type === "image_url")
              .map((p, k) => <img key={k} src={p.image_url!.url} className="att-img" />)}
          </div>
        </div>
      ) : m.content && typeof m.content === "string" && (
        <div className="msg-body md-body">
          {(() => {
            
            const parts = m.content.split(/(?=\[附件 [^\]]+\])/g);
            if (parts.length === 1) {
              return <RichMarkdown text={m.content} />;
            }
            return parts.map((p, k) => {
              const m2 = p.match(/^\[附件 ([^\]]+)\]\n?([\s\S]*)$/);
              if (!m2) {
                return p.trim() ? <RichMarkdown key={k} text={p} /> : null;
              }
              return (
                <details key={k} className="tool-block">
                  <summary><Icon name="paperclip" /> {m2[1]}</summary>
                  <pre className="wrap">{m2[2]}</pre>
                </details>
              );
            });
          })()}
        </div>
      )}
    </div>
  );
});
