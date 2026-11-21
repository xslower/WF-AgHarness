
import { useState } from "react";

import { Icon } from "../icons";
import { RichMarkdown } from "../markdown";
import { toolLabel } from "./toolLabel";
import { mergeSubAgentEvents } from "./subAgentEvents";
import type { SubAgent } from "../../chat/chatTypes";


interface SubMsg {
  role?: string;
  content?: unknown;
  reasoning?: string;
  tool_calls?: { id: string; function?: { name?: string; arguments?: string } }[];
  tool_call_id?: string;
}

function parseArgs(raw: unknown): unknown {
  if (typeof raw !== "string") return raw ?? {};
  try { return JSON.parse(raw); } catch { return {}; }
}


function msgText(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .filter((p): p is { type: string; text: string } =>
        !!p && typeof p === "object" && (p as { type?: string }).type === "text")
      .map((p) => p.text)
      .join("\n");
  }
  return "";
}


function SubMsgView({ m, results }: { m: SubMsg; results: Map<string, SubMsg> }) {
  if (m.role === "tool") return null;    
  const isUser = m.role === "user";
  const text = msgText(m.content);
  const calls = m.tool_calls ?? [];
  if (!isUser && !text.trim() && !calls.length && !m.reasoning) return null;

  return (
    <div className={`msg ${isUser ? "user" : "assistant"} sub-agent-msg`}>
      <div className="msg-role">{isUser ? "指令" : "子 Agent"}</div>
      {m.reasoning ? (
        <details className="tool-block reasoning-block">
          <summary><Icon name="thought" /> 思考过程</summary>
          <pre className="wrap">{m.reasoning}</pre>
        </details>
      ) : null}
      {text.trim() ? (
        <div className="msg-body md-body"><RichMarkdown text={text} /></div>
      ) : null}
      {calls.map((c) => {
        const { title, detail } = toolLabel(c.function?.name ?? "", parseArgs(c.function?.arguments));
        const res = results.get(c.id);
        const out = res ? msgText(res.content) : "";
        return (
          <details key={c.id} className="tool-block">
            <summary>
              <Icon name="wrench" /> {title}{detail ? <span className="dim"> {detail}</span> : null}
            </summary>
            {out ? <pre className="wrap">{out}</pre> : <div className="dim">（无输出）</div>}
          </details>
        );
      })}
    </div>
  );
}

export function SubAgentCard({
  sa, active, onToggle, onOpenTab, onQuery, onMessage, onStop,
}: {
  sa: SubAgent;
  active: boolean;
  onToggle: () => void;
  
  onOpenTab?: () => void;
  onQuery?: (id: string) => void | Promise<void>;
  onMessage?: (id: string, text: string) => void | Promise<boolean>;
  onStop?: (id: string) => void | Promise<void>;
}) {
  const [instruction, setInstruction] = useState("");
  const [loading, setLoading] = useState(false);
  const run = async (fn?: () => void | Promise<unknown>) => {
    if (!fn) return;
    setLoading(true);
    try { await fn(); } finally { setLoading(false); }
  };

  const msgs = (sa.messages ?? []) as SubMsg[];
  const hasDetail = !!(msgs.length || sa.events?.length);
  
  
  const eventBlocks = mergeSubAgentEvents(sa.events ?? []);
  
  const results = new Map<string, SubMsg>();
  for (const m of msgs) if (m.role === "tool" && m.tool_call_id) results.set(m.tool_call_id, m);

  return (
    <div className={`sub-agent-card ${sa.status}`}>
      <div className="sub-agent-header" onClick={onOpenTab || onToggle}>
        <span className="sub-agent-icon">
          {sa.status === "running" ? <Icon name="loop" />
            : sa.status === "done" ? <Icon name="check" /> : <Icon name="stop" />}
        </span>
        <span className="sub-agent-task">{sa.task}</span>
        <button className="link">{onOpenTab ? "打开会话" : active ? "收起" : "展开"}</button>
      </div>
      {active && (
        <div className="sub-agent-body">
          {sa.error && <div className="error">{sa.error}</div>}
          {hasDetail ? (
            <details open>
              <summary>子 Agent 会话</summary>
              <div className="sub-agent-log">
                {msgs.map((m, i) => <SubMsgView key={`m${i}`} m={m} results={results} />)}
                {eventBlocks.map((b, i) => b.kind === "text" ? (
                  <div className="msg assistant sub-agent-msg" key={`e${i}`}>
                    <div className="msg-body md-body"><RichMarkdown text={b.text} /></div>
                  </div>
                ) : b.kind === "reason" ? (
                  <details className="tool-block reasoning-block" key={`e${i}`}>
                    <summary><Icon name="thought" /> 思考过程</summary>
                    <pre className="wrap">{b.text}</pre>
                  </details>
                ) : (
                  <details className="tool-block" key={`e${i}`}>
                    <summary><Icon name="wrench" /> {b.name || "工具"}</summary>
                    {b.text ? <pre className="wrap">{b.text}</pre> : null}
                  </details>
                ))}
              </div>
            </details>
          ) : (
            <div className="dim">会话尚未加载，点击"查询会话"。</div>
          )}
          <div className="row gap4">
            <button disabled={loading} onClick={() => void run(() => onQuery?.(sa.id))}>
              查询会话
            </button>
            {sa.status === "running" && (
              <button className="danger" disabled={loading}
                onClick={() => void run(() => onStop?.(sa.id))}>中止</button>
            )}
          </div>
          {sa.status === "running" && (
            <div className="row gap4">
              <input value={instruction} placeholder="给子 Agent 追加指令"
                onChange={(e) => setInstruction(e.target.value)} />
              <button disabled={loading || !instruction.trim()}
                onClick={() => void run(async () => {
                  const ok = await onMessage?.(sa.id, instruction.trim());
                  if (ok) setInstruction("");
                })}>追加</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
