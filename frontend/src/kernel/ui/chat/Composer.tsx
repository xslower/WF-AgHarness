
import { useEffect, useState } from "react";
import type { AppConfig } from "../../api";
import { contextStats, isQueueSpec, modelOptions, specLabel } from "../../model/modelSpec";
import { fmtTokens } from "../format";
import { Icon } from "../icons";
import { useScopedWidth } from "../useScopedState";
import { viewScope } from "../../chat/chatSessionStore";
import { MAX_QUEUE, isQueueFull, type QueueItem } from "./queueOps";
import { useFileAttachments } from "./useFileAttachments";
import { useGhostCompletion } from "./useGhostCompletion";
import { useProjectPolicy } from "./useProjectPolicy";
import { useTextUndo } from "./useTextUndo";
import { useVoiceInput } from "./useVoiceInput";

interface Props {
  input: string;
  setInput: (v: string) => void;
  busy: boolean;
  canChat: boolean;
  config: AppConfig | null;
  ctxState: { used: number; model: string; estimated?: boolean } | null;
  modelSel: string;
  
  activeSpec?: string;
  setModelSel: (v: string) => void;
  onSend: (text: string, images: string[], audio: string, attachments: { name: string; text: string }[], wfSel: string) => Promise<boolean>;
  onStop: () => void;
  stopping?: boolean;
  selectedWf: string;
  sessionId: string | null;
  showArtifacts: boolean;
  setShowArtifacts: (v: boolean) => void;
  
  planOn: boolean;
  setPlanOn: (v: boolean) => void;
  
  queue?: QueueItem[];
  
  compact?: boolean;
}

export function Composer({
  input, setInput, busy, canChat, config, ctxState, modelSel, setModelSel, onSend,
  activeSpec,
  onStop, stopping = false,
  selectedWf, sessionId, showArtifacts, setShowArtifacts,
  planOn, setPlanOn, queue = [], compact = false,
}: Props) {
  const { images, setImages, docs: attachments, setDocs: setAttachments,
    addFiles, clear: clearAttachments } = useFileAttachments();
  const { recording, audio: audioAttach, setAudio: setAudioAttach,
    toggleRecord } = useVoiceInput();
  const { record: pushUndo, handleKey: handleUndoKey } = useTextUndo();
  
  const [taH, setTaH] = useScopedWidth(viewScope(sessionId), "ui.composerH", 72, 48, 600);
  const [modelTitle, setModelTitle] = useState("");
  const [dragOver, setDragOver] = useState(false);

  const modelOpts = modelOptions(config);

  const ctx = contextStats(config, modelSel, ctxState);
  
  
  
  const selSpec = isQueueSpec(modelSel) ? "" : modelSel;
  const selLabel = modelOpts.find((o) => o.value === modelSel)?.label ?? "父队列";

  
  const hasContent = !!input.trim() || images.length > 0 || attachments.length > 0 || !!audioAttach;
  const showStop = busy && !hasContent;
  const queueFull = isQueueFull(queue);

  
  
  const { ghost, request: requestGhost, clear: clearGhost } = useGhostCompletion({
    sessionId,
    enabled: !!config?.utility?.completion?.length,
  });

  const acceptGhost = () => {
    if (!ghost) return;
    setInput(input + ghost);
    clearGhost();
  };

  
  useEffect(() => { if (queue.length) clearGhost(); }, [queue.length]);
  
  const policyCtl = useProjectPolicy(sessionId);
  const policyMode = policyCtl.mode;

  const submit = async () => {
    const ok = await onSend(input, images, audioAttach, attachments, selectedWf);
    if (!ok) return;
    setInput("");
    clearAttachments();
    setAudioAttach("");
    
    clearGhost();
  };

  return (
    <div className={`input-bar${dragOver ? " drag-over" : ""}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={(e) => { if (e.currentTarget === e.target) setDragOver(false); }}
      onDrop={(e) => {
        e.preventDefault(); setDragOver(false);
        addFiles(Array.from(e.dataTransfer?.files ?? []));
      }}>
      <div className="img-tray">
        {images.map((u, i) => (
          <span key={i} className="img-chip">
            <img src={u} />
            <button className="link del" onClick={() => setImages((a) => a.filter((_, x) => x !== i))}>×</button>
          </span>
        ))}
        {attachments.map((at, i) => (
          <span key={`at${i}`} className="chip on" title={`附件：${at.name}（内容将随消息发送）`}>
            📄 {at.name}
            <button className="link del" onClick={() => setAttachments((a) => a.filter((_, x) => x !== i))}>×</button>
          </span>
        ))}
      </div>
      {}
      <div className="composer-resize" title="拖动调整输入框高度"
        onMouseDown={(e) => {
          e.preventDefault();
          const startY = e.clientY, startH = taH;
          let last = startH;
          const move = (ev: MouseEvent) => {
            last = Math.min(600, Math.max(48, startH - (ev.clientY - startY)));
            setTaH(last);
          };
          const up = () => {
            window.removeEventListener("mousemove", move);
            window.removeEventListener("mouseup", up);
            setTaH(last);   
          };
          window.addEventListener("mousemove", move);
          window.addEventListener("mouseup", up);
        }} />
      <textarea disabled={!canChat}
        value={input}
        placeholder={config?.queues.parent.length
          ? (busy ? `回复中…按发送进入队列（${queue.length}/${MAX_QUEUE}）(Enter)` : "输入任务… (Enter 发送, Shift+Enter 换行)")
          : "请先在设置中配置父模型队列…"}
        onChange={(e) => { pushUndo(e.target.value); setInput(e.target.value); clearGhost(); requestGhost(e.target.value); }}
        onKeyDown={(e) => {
          
          if (handleUndoKey(e, setInput)) { clearGhost(); return; }
          if (e.key === "Tab" && ghost) { e.preventDefault(); acceptGhost(); return; }
          if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
        }}
        style={{ height: taH, maxHeight: "70vh" }}
      />
      <div className="input-toolbar">
        <button className={`icon-btn ${recording ? "on" : ""}`}
          title={recording ? "停止录音" : "录音输入（转文字/ASR）"}
          onClick={toggleRecord}><Icon name={recording ? "stop" : "mic"} /></button>
        {audioAttach && (
          <span className="chip on" title="已录语音，随下一条消息发送"
            onClick={() => setAudioAttach("")}><Icon name="mic" /> 语音 ×</span>
        )}
        <label className="img-btn" title="添加附件（图片直接给模型；文档读全文随消息发送）">
          <Icon name="paperclip" /><input type="file" multiple hidden
            onChange={(e) => {
              addFiles(Array.from(e.target.files ?? []));
              e.target.value = "";
            }} />
        </label>
        <label className="model-select">
          模型
          <select value={modelSel} title={modelTitle || selLabel}
            onMouseEnter={(e) => setModelTitle(e.currentTarget.selectedOptions[0]?.textContent || "")}
            onChange={(e) => setModelSel(e.target.value)}>
            {}
            {modelOpts.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          {}
          {activeSpec && activeSpec !== selSpec && (
            <span className="dim" style={{ fontSize: 11, whiteSpace: "nowrap" }}
              title={`你选的是「${selLabel}」，本轮实际用的是这个`}>
              实际：{specLabel(config, activeSpec)}
            </span>
          )}
        </label>
        {!compact && (
          <label className="model-select"
            title={policyCtl.policy?.always || "本会话的安全级别：决定命令与文件操作的审核强度"}>
            安全
            <select value={policyMode}
              onChange={(e) => policyCtl.change(e.target.value)}
              onFocus={() => { void policyCtl.reload(); }}>
              {(policyCtl.policy?.modes ?? []).map((m) => (
                <option key={m.value} value={m.value} title={m.hint}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
        )}
        <span className="ctx-ring-wrap"
          title={`上下文 ${ctx.estimated ? "~" : ""}${ctx.used ? ctx.used.toLocaleString() : "—"} / ${ctx.limit.toLocaleString()} tokens (${ctx.pct.toFixed(0)}%)`
            + `${ctx.estimated ? "（按字数估算，回复中途每个工具调用后都会更新）" : ""}`
            + `${ctx.pct >= ctx.warnRatio * 100 ? " ⚠ 建议开新任务" : ""}`}>
          {}
          <span className="ctx-num">{ctx.used
            ? `${ctx.estimated ? "~" : ""}${fmtTokens(ctx.used)}`
            : "—"}</span>
          <svg width="26" height="26" viewBox="0 0 26 26" className="ctx-ring">
            <circle cx="13" cy="13" r="10" fill="none" stroke="var(--border2)" strokeWidth="3" />
            <circle cx="13" cy="13" r="10" fill="none"
              stroke={ctx.pct >= ctx.warnRatio * 100 ? "var(--warn)" : "var(--accent)"}
              strokeWidth="3" strokeLinecap="round"
              strokeDasharray={`${(ctx.pct / 100) * 62.8} 62.8`}
              transform="rotate(-90 13 13)" />
          </svg>
        </span>
        <button className={`icon-btn ${planOn ? "on" : ""}`}
          title={planOn
            ? "计划模式（只读）：要改文件时先出计划，确认后才动手。点击关闭 = 不限制"
            : "计划模式已关闭：Agent 可直接改文件（不限制）。点击开启只读计划模式"}
          onClick={() => setPlanOn(!planOn)}><Icon name="plan" /></button>
        <button className={`icon-btn ${showArtifacts ? "on" : ""}`} title="产出物面板"
          onClick={() => setShowArtifacts(!showArtifacts)} hidden={compact}><Icon name="artifacts" /></button>
        <span className="flex1" />
        {showStop ? (
          <button className="primary stop" disabled={stopping} onClick={onStop}
            title="中止当前回复（队列里的消息会继续按序发送；要全停请先删掉队列）">
            {stopping ? "中止中…" : <><Icon name="stop" /> 中止</>}
          </button>
        ) : (
          <button className="primary send" disabled={!canChat || !hasContent} onClick={submit}
            title={busy ? "加入队列，等本轮结束后依次发送" : "发送"}>
            {busy ? (queueFull ? "队列已满" : `加入队列 ${queue.length}/${MAX_QUEUE}`) : "发送"}
          </button>
        )}
      </div>
      {}
      {ghost && !queue.length && (
        <div className="ghost-popup" onClick={acceptGhost} title="Tab 接受">
          <span className="ghost-current">{input}</span><span className="ghost-rest">{ghost}</span>
        </div>
      )}
    </div>
  );
}
