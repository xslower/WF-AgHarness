
import { useEffect, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { HumanGateView, WfInputDecl, WfRun, WfRunFile,
  WfRunSummary } from "../../kernel/api";
import { fmtSize, shortTime } from "../../kernel/ui/format";
import { Icon } from "../../kernel/ui/icons";
import { useScopedWidth } from "../../kernel/ui/useScopedState";
import { PanelClose } from "./PanelClose";


export function HumanGateCard({ gate, onDecide }: {
  gate: HumanGateView;
  
  onDecide: (choice: string, comment: string) => void;
}) {
  const [comment, setComment] = useState("");
  return (
    <div className="wf-gate">
      <div className="wf-gate-head">⏸ 等待确认 · {gate.title || gate.node_id}</div>
      {gate.ask && <div className="wf-gate-ask">{gate.ask}</div>}
      {gate.show && <pre className="wf-gate-show">{gate.show}</pre>}
      <input className="wf-gate-comment" value={comment} placeholder="备注（可选）"
        onChange={(e) => setComment(e.target.value)} />
      <div className="wf-gate-actions">
        {gate.options.map((opt, i) => (
          <button key={opt} className={i === 0 ? "primary" : ""}
            onClick={() => onDecide(opt, comment)}>{opt}</button>
        ))}
      </div>
    </div>
  );
}

interface InputDialogProps {
  open: boolean;
  inputs: WfInputDecl[];
  values: Record<string, string>;
  setValues: Dispatch<SetStateAction<Record<string, string>>>;
  onCancel: () => void;
  onStart: () => void;
}


export function RunInputDialog({ open, inputs, values, setValues, onCancel, onStart }: InputDialogProps) {
  if (!open) return null;
  return (
    <div className="wf-runask-mask" onClick={onCancel}>
      <div className="wf-runask" onClick={(e) => e.stopPropagation()}>
        <div className="palette-title">▶ 运行输入</div>
        {inputs.length === 0 && <div className="dim pad8">无输入，直接启动</div>}
        {inputs.map((inp) => (
          <label key={inp.name} className="wf-input">
            {inp.desc || inp.name}
            {inp.type === "image" || inp.type === "file" ? (
              <input type="file" accept={inp.type === "image" ? "image/*" : undefined}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (!f) return;
                  const rd = new FileReader();
                  rd.onload = () => setValues((v) => ({ ...v, [inp.name]: String(rd.result) }));
                  if (inp.type === "image") rd.readAsDataURL(f); else rd.readAsText(f);
                }} />
            ) : (
              <input value={values[inp.name] ?? ""}
                onChange={(e) => setValues((v) => ({ ...v, [inp.name]: e.target.value }))} />
            )}
          </label>
        ))}
        <div className="wf-runask-actions">
          <button onClick={onCancel}>取消</button>
          <button className="primary" onClick={onStart}>▶ 启动</button>
        </div>
      </div>
    </div>
  );
}


const STATUS_TEXT: Record<string, string> = {
  running: "进行中", done: "完成", failed: "失败", cancelled: "已中止",
};


export function useLogHeight(scope: string) {
  return useScopedWidth(scope, "wf.logH", 260, MIN_LOG_H, MAX_LOG_H);
}

const MIN_LOG_H = 120;

const MAX_LOG_H = Math.max(240, (typeof window !== "undefined" ? window.innerHeight : 900) - 260);


export function RunLogPanel({ run, history, height, onResizeStart,
  onCancel, onResume, onOpenRun, onHuman, onRedo, why,
  openFile = null, onOpenFile, onClose }: {
  run: WfRun | null;
  history?: WfRunSummary[];
  
  height?: number;
  
  onResizeStart?: (e: React.MouseEvent) => void;
  onCancel?: () => void;
  onResume?: () => void;
  onOpenRun?: (rid: string) => void;
  
  onHuman?: (choice: string, comment: string) => void;
  
  onRedo?: (nodeId: string) => void;
  
  why?: React.ReactNode;
  
  openFile?: string | null;
  onOpenFile?: (f: WfRunFile | null) => void;
  
  onClose?: () => void;
}) {
  const resumable = !!run && (run.status === "failed" || run.status === "cancelled");
  
  const [view, setView] = useState<"log" | "why">("log");
  
  const runPanel = (
    <>
        <div className="wf-log-head">
          <span className="palette-title">
            <Icon name="list" /> 运行状态 {!run ? "" : run.status === "running" ? "（进行中…）"
              : run.status === "done" ? "✓ 完成"
              : run.status === "cancelled" ? "⏹ 已中止" : `✗ ${run.error}`}
          </span>
          <span className="flex1" />
          {why && (
            <>
              <button className={`link ${view === "log" ? "on" : ""}`}
                onClick={() => setView("log")}>运行详情</button>
              <button className={`link ${view === "why" ? "on" : ""}`}
                title="这一跳读了什么、写了什么、哪一跳产出是空的"
                onClick={() => setView("why")}>出处</button>
            </>
          )}
          {onClose && <PanelClose onClose={onClose} title="收起运行日志" />}
          {run?.status === "running" && onCancel && (
            <button className="link" title="中止本次运行" onClick={onCancel}>⏹ 停止</button>
          )}
          {resumable && onResume && (
            <button className="link" title="从失败的节点继续，已成功的节点不重跑"
              onClick={onResume}>↻ 从失败处继续</button>
          )}
        </div>
        {run?.pending_human && onHuman && (
          <HumanGateCard gate={run.pending_human} onDecide={onHuman} />
        )}
        {}
        {!!run?.warnings?.length && (
          <div className="wf-run-warns">
            <div className="wf-run-warns-head">
              <Icon name="alert" /> {run.warnings.length} 条告警
            </div>
            {run.warnings.map((w, i) => (
              <div key={`${w.code}-${w.node}-${i}`} className="wf-run-warn">
                {w.node ? <code>{w.node}</code> : null} {w.message}
              </div>
            ))}
          </div>
        )}
        {run && Object.entries(run.nodes).map(([id, st]) => (
          <details key={id} className="tool-block"
            open={st.status === "running" || st.status === "failed"}>
            {}
            <summary>{id} · {STATUS_TEXT[st.status] || st.status}

              {st.error ? ` · ${st.error}` : ""}
              {st.truncated ? ` · ⚠ 输出被截断（原 ${st.original_chars} 字符）` : ""}
              {onRedo && st.status !== "running" && (
                <button className="link wf-node-redo"
                  title="从这一跳重跑：上游回放不重算，下游旧产出作废"
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); onRedo(id); }}>
                  ↻ 重跑</button>
              )}
            </summary>
            <pre>{st.output || (st.status === "running" ? "（还在跑，暂无输出）" : "")}</pre>
          </details>
        ))}
        {run?.final && (
          <details className="tool-block" open>
            <summary>最终输出</summary><pre>{run.final}</pre>
          </details>
        )}

    </>
  );
  return (
    <div className="wf-log" style={height ? { height, maxHeight: height } : undefined}>
      {onResizeStart && (
        <div className="wf-log-resize" onMouseDown={onResizeStart}
          title="上下拖动调节日志区高度"><span className="art-drag-bar" /></div>
      )}
      <div className="wf-run-main">{view === "why" && why ? why : runPanel}</div>

      {}
      {history && (
        <aside className="wf-run-hist">
          <div className="wf-run-side-head">
            历史运行{history.length ? ` · ${history.length}` : ""}
          </div>
          <div className="wf-run-side-list">
            {!history.length && <div className="wf-run-empty">还没有运行记录</div>}
            {history.map((h) => (
              <button key={h.id} type="button"
                className={`wf-run-item ${run?.id === h.id ? "active" : ""}`}
                title={`${h.id}\n${h.workflow || ""} · ${h.status}`}
                onClick={() => onOpenRun?.(h.id)}>
                <Icon name="bolt" />

                <span className="wf-run-time">{shortTime(h.started)}</span>

                <span className={`wf-run-dot ${h.status}`} title={h.status} />
              </button>
            ))}
          </div>
        </aside>
      )}


      {}
      <aside className="wf-run-files">
        <div className="wf-run-side-head">
          产出文件{run?.files?.length ? ` · ${run.files.length}` : ""}
        </div>
        <div className="wf-run-files-list">
          {!run?.files?.length && (
            <div className="wf-run-empty">
              {run ? "本次运行没有产出文件" : "还没有运行记录"}
            </div>
          )}
          {run?.files?.map((f) => (
            <button key={f.path} type="button"
              className={`wf-run-file ${openFile === f.path ? "active" : ""}`}
              title={`${f.path}${f.node ? `\n由节点 ${f.node} 写入` : ""}`}
              onClick={() => onOpenFile?.(openFile === f.path ? null : f)}>
              <Icon name="file-text" />
              <span className="wf-run-file-name">{f.rel || f.name}</span>
              <span className="wf-run-file-size">{fmtSize(f.size)}</span>
            </button>
          ))}
        </div>
      </aside>
    </div>
  );
}
