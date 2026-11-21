
import { useState } from "react";

import { FloatPanel } from "../../kernel/ui/FloatPanel";
import { fmtStamp } from "../../kernel/ui/format";
import { Icon } from "../../kernel/ui/icons";
import { ChatPanel } from "../../kernel/ui/chat/ChatPanel";
import { chatCtl } from "../../kernel/ui/chat/chatController";
import { PanelClose } from "./PanelClose";
import { useWorkflowChatSessions } from "./useWorkflowChatSessions";

interface Props {
  project: string;
  
  name: string;
  title?: string;
  
  onClose?: () => void;
}

export function WorkflowChat({ project, name, title, onClose }: Props) {
  const c = useWorkflowChatSessions({
    project, name, dropChat: chatCtl.dropSession,
  });
  const [open, setOpen] = useState(false);

  const openHistory = async () => { await c.reload(); setOpen(true); };

  return (
    <div className="wf-chat wf-chat-full">
      <div className="wf-chat-bar">
        <span className="wf-chat-bar-title" title={title}>
          <Icon name="workflow" />
          <span className="wf-chat-bar-text">{title || "AI 助手"}</span>
        </span>
        <button className="icon-btn" title="新建会话（空会话，直接开聊）"
          onClick={() => void c.newSession()} disabled={c.creating}>
          <Icon name="plus" />
        </button>
        <button className="icon-btn" title="历史会话（可切换/删除）"
          onClick={() => void openHistory()}>
          <Icon name="chat" />
        </button>
        {onClose && <PanelClose onClose={onClose} title="收起 AI 对话" />}
      </div>

      <ChatPanel
        project={project}
        sessionId={c.sid}
        onSessionChange={c.select}
        sessionMeta={{ kind: "workflow", origin: name }}
        compact
        className="chat-panel wf-chat-inner"
      />

      {open && (
        <FloatPanel storeKey="wfchat.history.workflow" title={
          <span className="wf-sess-title">
            <Icon name="chat" /> 本工作流的会话
            <span className="wf-sess-sub">{c.sessions.length} 条</span>
          </span>
        } onClose={() => setOpen(false)}>
          {c.sessions.length === 0 ? (
            <div className="float-hint">还没有会话，点上方 ＋ 新建一条。</div>
          ) : (
            <div className="wf-sess-list">
              {c.sessions.map((s) => (
                <div key={s.id}
                  className={`wf-sess-item ${s.id === c.sid ? "active" : ""}`}
                  onClick={() => { c.select(s.id); setOpen(false); }}>
                  <div className="wf-sess-main">
                    <div className="wf-sess-name">{s.title}</div>
                    <div className="wf-sess-meta">
                      {fmtStamp(s.created_at)} · {s.message_count} 条消息
                    </div>
                  </div>
                  <button className="icon-btn" title="删除这条会话"
                    onClick={(e) => { e.stopPropagation(); void c.remove(s); }}>
                    <Icon name="trash" />
                  </button>
                </div>
              ))}
              <div className="float-hint">
                超过保留期（设置里的「画布会话保留天数」，默认 7 天）会自动清理。
              </div>
            </div>
          )}
        </FloatPanel>
      )}
    </div>
  );
}
