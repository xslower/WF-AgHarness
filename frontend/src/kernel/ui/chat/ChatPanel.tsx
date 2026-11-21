
import { useEffect, useRef, useState } from "react";
import { api } from "../../api";
import { NEW_SESSION_KEY, readField, writeField } from "../../chat/chatSessionStore";
import type { AppConfig } from "../../api";
import { confirmDialog } from "../dialog";
import { Icon } from "../icons";
import { MessageList } from "../chat/MessageList";
import type { SessionPrefs } from "../../chat/sessionPrefs";
import { Composer } from "./Composer";
import { ChatFloat } from "./ChatFloat";
import { QueuePanel } from "./QueuePanel";
import { lostOnEdit, mergeForEdit, type QueueItem } from "./queueOps";
import { useChatStream, type ChatStream } from "./useChatStream";
import { readInput, saveInput } from "./chatStorage";
import { useOwnConfig } from "./useOwnConfig";
import { useSessionModel } from "./useSessionModel";
import { useSessionPlan } from "./useSessionPlan";
import { useEmbeddedHistory } from "./useEmbeddedHistory";
import type { SendOptions } from "./chatTypes";
import {
  armPlanAutoReturn, isApproval, noteUserMessage, resetPlanAutoReturn,
} from "./planAutoReturn";


export interface ChatPanelProps {
  
  project: string;
  
  chat?: ChatStream;
  
  sessionId?: string | null;
  
  storeKey?: string;
  
  onSessionChange?: (id: string | null) => void;
  
  sessionMeta?: { kind?: string; origin?: string };
  
  title?: string;
  
  compact?: boolean;
  
  maxWidth?: number;
  
  workflow?: string;
  
  modelSel?: string;
  setModelSel?: (v: string) => void;
  
  prefs?: SessionPrefs;
  showArtifacts?: boolean;
  setShowArtifacts?: (v: boolean) => void;
  className?: string;
  
  outerConfig?: AppConfig | null;
  
  onPlanChange?: (v: boolean) => void;
  
  fillRequest?: { text: string; seq: number };
}

export function ChatPanel({
  project, chat: external, sessionId, storeKey, onSessionChange, sessionMeta,
  title, compact = false,
  maxWidth = 0, workflow = "", showArtifacts = false,
  setShowArtifacts, className, modelSel: outerModel, setModelSel: outerSet,
  prefs, outerConfig, onPlanChange, fillRequest,
}: ChatPanelProps) {
  
  
  const config = useOwnConfig(outerConfig);
  const [input, setInput] = useState("");
  
  const [planFinal, setPlanFinal] = useState(false);
  
  
  
  
  
  
  
  const [innerSid, setInnerSid] = useState<string | null>(
    () => (storeKey ? readField(NEW_SESSION_KEY, "lastSid", "") || null : null));
  const controlled = !external && !storeKey && sessionId !== undefined;
  const sid = controlled ? (sessionId ?? null) : innerSid;
  const setSid = controlled ? (onSessionChange ?? (() => {})) : setInnerSid;

  useEffect(() => {
    if (storeKey && sid) writeField(NEW_SESSION_KEY, "lastSid", sid);
  }, [sid, storeKey]);
  const activeSid = external ? (sessionId ?? null) : sid;
  
  const model = useSessionModel({ outerModel, outerSet, activeSid });
  const modelSel = model.model;
  const setModelSel = model.setModel;


  
  const inner = useChatStream({
    project,
    sessionId: sid,
    setSessionId: setSid,
    refreshSessions: async () => {},
    modelSel,
    sessionMeta,
  });
  const chat = external ?? inner;
  
  const plan = useSessionPlan({
    outerPrefs: prefs, outerSet: onPlanChange, activeSid,
  });
  const planOn = plan.on;
  const setPlanOn = plan.setOn;

  useEmbeddedHistory({
    external: !!external, activeSid,
    loadSession: chat.loadSession, onModel: model.adopt,
  });

  
  
  
  const prevPlanRef = useRef<{ sid: string | null; status: string }>(
    { sid: null, status: "idle" });
  useEffect(() => {
    const status = chat.planState?.status ?? "idle";
    const prev = prevPlanRef.current;
    prevPlanRef.current = { sid: activeSid, status };
    
    
    if (status === "executing" && prev.sid === activeSid
        && prev.status !== "executing") {
      setPlanOn(false);                    
      armPlanAutoReturn(activeSid);        
    }
  }, [chat.planState?.status, activeSid, setPlanOn]);

  
  const onManualPlanToggle = (v: boolean) => {
    resetPlanAutoReturn(activeSid);
    setPlanOn(v);
  };

  
  const sendWithPlan = (text: string, opts: SendOptions = {}) => {
    
    
    
    if (chat.planState?.status === "awaiting_approval" && isApproval(text)) {
      void chat.sendPlanDecision("approve");
      return Promise.resolve(true);
    }
    const verdict = noteUserMessage(activeSid, text);
    if (verdict === "keyword") {
      
      setPlanOn(true);
      return chat.send(text, { ...opts, plan: true });
    }
    if (verdict === "reached") {
      
      setPlanOn(true);
      return chat.send(text, { ...opts, plan: false });
    }
    return chat.send(text, { ...opts, plan: opts.plan ?? planOn });
  };

  
  const editQueued = async (it: QueueItem) => {
    const lost = lostOnEdit(it);
    if (lost && !(await confirmDialog({
      title: "撤回队列消息",
      okText: "继续撤回",
      message: `这条包含 ${lost}，撤回后需要在输入框重新添加。继续？`,
    }))) return;
    applyInput(mergeForEdit(it.content, input));
    chat.queueAction("remove", it.id);
  };

  
  
  
  const applyInput = (v: string) => {
    setInput(v);
    saveInput(activeSid, v);
  };
  useEffect(() => {
    
    
    setInput(readInput(activeSid));
  }, [activeSid]);

  
  
  useEffect(() => {
    if (!fillRequest) return;
    applyInput(fillRequest.text);
    
    
  }, [fillRequest?.seq]);

  return (
    <div className={className ?? "chat-panel"}>
      {title ? <div className="palette-title">{title}</div> : null}
      <MessageList
        config={config}
        messages={chat.messages}
        live={chat.live}
        busy={chat.busy}
        subAgents={chat.subAgents}
        activeSubAgent={chat.activeSubAgent}
        setActiveSubAgent={chat.setActiveSubAgent}
        suggestions={chat.suggestions}
        onSend={(text) => { void sendWithPlan(text, { workflow }); }}
        onEdit={async (i) => {
          
          const t = await chat.editFrom(i);
          if (t !== null) applyInput(t);
        }}
        onQuerySubAgent={chat.querySubAgent}
        onMessageSubAgent={chat.messageSubAgent}
        onStopSubAgent={chat.stopSubAgent}
        maxWidth={maxWidth}
        sessionId={activeSid}
        msgOffset={chat.msgOffset}
        hasMore={chat.hasMore}
        onLoadOlder={chat.loadOlder}
      />
      <QueuePanel
        items={chat.queue}
        onRemove={(id) => chat.queueAction("remove", id)}
        onEdit={editQueued}
        onInterject={(id) => chat.queueAction("interject", id)}
        onCancelInterject={(id) => chat.queueAction("cancel_interject", id)}
      />
      {}
      <ChatFloat
        chat={chat}
        onEditPlan={(text) => { applyInput(text); setPlanFinal(true); }}
      />
      {planFinal && (
        <div className="plan-final-bar">
          <Icon name="plan" />
          <span>计划定稿：改完按发送，直接按这份计划执行（不再让模型重写一遍）</span>
          <button className="link" onClick={() => { setPlanFinal(false); applyInput(""); }}>
            放弃
          </button>
        </div>
      )}
      <Composer
        key={activeSid ?? "new"}
        input={input}
        setInput={applyInput}
        busy={chat.busy}
        canChat={!!project}
        config={config}
        ctxState={chat.ctxState}
        modelSel={modelSel}
        setModelSel={setModelSel}
        activeSpec={chat.activeSpec}
        onSend={async (text, images, audio, attachments, wfSel) => {
          const opts: SendOptions = { images, audio, attachments, workflow: wfSel };
          if (planFinal) {
            
            
            setPlanFinal(false);
            setPlanOn(false);
            armPlanAutoReturn(activeSid);
            return chat.send(text, { ...opts, plan: false });
          }
          return sendWithPlan(text, opts);
        }}
        onStop={() => { void chat.stop(); }}
        stopping={chat.stopping}
        queue={chat.queue}
        selectedWf={workflow}
        sessionId={activeSid}
        showArtifacts={showArtifacts}
        setShowArtifacts={setShowArtifacts ?? (() => {})}
        planOn={planOn}
        setPlanOn={onManualPlanToggle}
        compact={compact}
      />
    </div>
  );
}
