
import { useCallback, useEffect, useState } from "react";
import type { AppConfig, WfRun } from "../../kernel/api";
import { MessageList } from "../../kernel/ui/chat/MessageList";
import { resizeWidth } from "../../kernel/ui/drag";
import { shortTime } from "../../kernel/ui/format";
import { Icon } from "../../kernel/ui/icons";
import { readStored, writeStored } from "../../kernel/ui/useLocalState";
import { useLlmSessions } from "./useLlmSessions";

export interface LlmSessionDrawerProps {
  project: string;
  workflow: string;
  config: AppConfig | null;
  
  run: WfRun | null;
  
  onNewSession: () => void;
  
  onPickSession: (sid: string) => void;
  
  selected: string;
  
  focusNode: string | null;
  onClose: () => void;
  
  maximized: boolean;
  onToggleMax: () => void;
  
  width: number;
  onWidth: (w: number) => void;
  
  embedded?: boolean;
}

export function LlmSessionDrawer(p: LlmSessionDrawerProps) {
  
  const storeKey = `wf.llmLog.${p.project}/${p.workflow}`;
  
  
  const [sel, setSelState] = useState<{ session: string; node: string }>(
    () => readStored(storeKey, { session: "", node: "" }));
  const setSel = useCallback((upd: (s: { session: string; node: string }) =>
    { session: string; node: string }) => {
    setSelState((prev) => {
      const next = upd(prev);
      if (next.session === prev.session && next.node === prev.node) return prev;
      writeStored(storeKey, next);
      return next;
    });
  }, [storeKey]);
  useEffect(() => { setSelState(readStored(storeKey, { session: "", node: "" })); }, [storeKey]);
  

  const ctl = useLlmSessions({
    project: p.project, workflow: p.workflow,
    runSession: p.run?.session ?? null,
    session: sel.session, node: sel.node,
    running: p.run?.status === "running",
  });

  
  useEffect(() => {
    const sid = p.run?.session;
    if (sid) setSel((s) => (s.session === sid ? s : { ...s, session: sid }));
  }, [p.run?.session, setSel]);

  
  useEffect(() => {
    const nid = p.focusNode;
    if (!nid) return;
    const hit = ctl.nodes.find((n) => (n.title || "") === nid);
    if (hit) setSel((s) => (s.node === hit.id ? s : { ...s, node: hit.id }));
  }, [p.focusNode, ctl.nodes, setSel]);

  
  const inner = (
    <div className="wf-llm-body">
      <aside className="wf-llm-pick">
        <div className="wf-run-side-head">
          会话
          <button className="link" title="新建会话：下次运行从干净上下文开始"
            onClick={() => { p.onNewSession(); }}>+ 新建</button>
        </div>
        <div className="wf-run-side-list">
          {!ctl.sessions.length && <div className="wf-run-empty">还没有会话记录</div>}
          {ctl.sessions.map((s) => (
            <button key={s.id} type="button"
              className={`wf-run-item ${sel.session === s.id ? "active" : ""}`}
              title={`${s.id}${p.selected === s.id ? "（下次运行续用）" : ""}`}
              onClick={() => { setSel((v) => ({ ...v, session: s.id, node: "" })); p.onPickSession(s.id); }}>
              <Icon name="chat" />
              <span className="wf-run-time">{shortTime(s.created_at)}</span>
              {p.selected === s.id && <span className="wf-run-dot done" title="下次运行续用此会话" />}
            </button>
          ))}
        </div>

        <div className="wf-run-side-head split">LLM 节点</div>
        <div className="wf-run-side-list">
          {!ctl.nodes.length && <div className="wf-run-empty">该会话还没有 LLM 记录</div>}
          {ctl.nodes.map((n) => (
            <button key={n.id} type="button"
              className={`wf-run-item ${sel.node === n.id ? "active" : ""}`}
              title={n.title}
              onClick={() => setSel((s) => ({ ...s, node: n.id }))}>
              <Icon name="robot" />
              <span className="wf-run-time">{n.title}</span>
              <span className="wf-run-id">{n.message_count || 0}</span>
            </button>
          ))}
        </div>
      </aside>

      <div className="wf-llm-msgs">
        {!sel.node ? (
          <div className="dim pad8">
            选一个 LLM 节点，查看它收到的消息与回复记录。
            {p.selected ? "（下次运行会续用左侧选中的会话）" : ""}
          </div>
        ) : (
          <MessageList
            config={p.config}
            messages={ctl.msgs}
            live={[]}
            busy={false}
            subAgents={{}}
            activeSubAgent={null}
            setActiveSubAgent={() => {}}
            suggestions={[]}
            onSend={() => {}}
            onEdit={() => {}}
            maxWidth={0}
            sessionId={sel.node}
          />
        )}
      </div>
    </div>
  );

  
  
  if (p.embedded) return <div className="wf-llm-embedded">{inner}</div>;

  return (
    <div className={`wf-llm-drawer ${p.maximized ? "max" : ""}`}
      style={p.maximized ? undefined : { width: p.width }}>
      {!p.maximized && (
        <div className="wf-llm-edge" title="拖动调节宽度"
          onMouseDown={resizeWidth({ width: p.width, min: 360, max: 1400,
            edge: "left", setWidth: p.onWidth })}>
          <span className="art-drag-bar" />
        </div>
      )}
      <div className="wf-llm-bar">
        <span className="palette-title"><Icon name="robot" /> LLM 会话记录</span>
        <span className="flex1" />
        <button className="link" title={p.maximized ? "还原" : "最大化"}
          onClick={p.onToggleMax}>{p.maximized ? "❐ 还原" : "⛶ 最大化"}</button>
        <button className="link" title="收起（双击画布节点可再打开）"
          onClick={p.onClose}>× 收起</button>
      </div>
      {inner}
    </div>
  );
}
