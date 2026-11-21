
import { useEffect, useMemo, useRef, useState } from "react";
import type { WfAvailable, WfRun } from "../../kernel/api";
import { normalizeNodeModel, QUEUE_LABELS, type ModelOption } from "../../kernel/model/modelSpec";
import { useModelOptions } from "../../kernel/model/useModelOptions";
import { RichMarkdown } from "../../kernel/ui/markdown";
import { itemOf } from "./dsl";
import { PanelClose } from "./PanelClose";
import type { PaletteItem } from "./Palette";


const PREV_TOKEN = "${" + "prev}";


function NodeOutput({ out }: { out: string }) {
  const t = (out ?? "").trim();
  
  if (/^data:image\
    return <img src={t} alt="节点产物" className="gnode-out-img" />;
  }
  
  if ((t.startsWith("{") && t.endsWith("}")) || (t.startsWith("[") && t.endsWith("]"))) {
    try {
      return <pre className="gnode-out-json">{JSON.stringify(JSON.parse(t), null, 2)}</pre>;
    } catch {  }
  }
  
  if (/^#{1,6} \S|```|^[-*] \S|^\s*\|.*\|/m.test(t)) {
    return <div className="gnode-out-md"><RichMarkdown text={t} /></div>;
  }
  return <pre>{out}</pre>;
}

interface Props {
  selDsl: Record<string, string> | null;
  items: PaletteItem[];
  run: WfRun | null;
  onPatch: (key: string, value: string) => void;
  onDelete: () => void;
  
  vars?: string[];
  
  onTestRun?: () => void;
  
  onRunFrom?: () => void;
  
  available?: WfAvailable[];
  
  onOpenWorkflow?: (name: string) => void;
  
  onExtract?: () => void;
  
  onClose?: () => void;
}

export function Inspector({ selDsl, items, run, onPatch, onDelete, vars = [],
  onTestRun, onRunFrom, available = [], onOpenWorkflow, onExtract, onClose }: Props) {
  
  const taRefs = useRef<Record<string, HTMLTextAreaElement | null>>({});
  const insertVar = (key: string, v: string) => {
    if (!v) return;
    const token = "${" + v + "}";
    const cur = selDsl?.[key] ?? "";
    const ta = taRefs.current[key];
    if (ta) {
      const s = ta.selectionStart ?? cur.length;
      const e = ta.selectionEnd ?? s;
      onPatch(key, cur.slice(0, s) + token + cur.slice(e));
      requestAnimationFrame(() => {
        ta.focus();
        ta.setSelectionRange(s + token.length, s + token.length);
      });
    } else {
      onPatch(key, `${cur}${cur ? " " : ""}${token}`);
    }
  };
  
  const varGroups = useMemo(() => {
    const g = [
      { label: "输入变量", items: [] as string[] },
      { label: "节点输出", items: [] as string[] },
      { label: "上一节点", items: [] as string[] },
    ];
    for (const v of vars) {
      if (v === "prev") g[2].items.push(v);
      else if (v.startsWith("inputs.")) g[0].items.push(v);
      else g[1].items.push(v);
    }
    return g.filter((x) => x.items.length > 0);
  }, [vars]);
  
  const varPreview = (v: string): string => {
    const st = run?.nodes?.[v];
    const val = st?.output ?? "";
    return val ? `上次运行值: ${val.slice(0, 80)}${val.length > 80 ? "…" : ""}` : "（尚未运行，无值）";
  };
  
  const modelOpts = useModelOptions();
  const selItem = selDsl ? itemOf(selDsl.type, items) : null;
  return (
    <div className="wf-inspector">
      {onClose && <PanelClose onClose={onClose} title="收起属性面板" />}
      {selDsl && selItem ? (
        <>
          <div className="q-title">{selItem.icon} {selItem.label}</div>
          <div className="dim pad-b8">id: {selDsl.id} · type: {selDsl.type}</div>
          {selDsl.type === "workflow" && (
            <div className="wf-subflow-bar">
              <label className="wf-field">引用已有子工作流（本项目 + 全局复用库）
                <select value={available.some((w) => w.name === selDsl.name) ? selDsl.name : ""}
                  onChange={(e) => {
                    const w = available.find((x) => x.name === e.target.value);
                    onPatch("name", w ? w.name : "");
                    
                    if (w?.inputs?.length) {
                      const tpl: Record<string, string> = {};
                      for (const n of w.inputs) tpl[n] = PREV_TOKEN;
                      onPatch("inputsJson", JSON.stringify(tpl));
                    }
                  }}>
                  <option value="">（当前值不在列表里 / 手写名称）</option>
                  {available.map((w) => (
                    <option key={`${w.scope}:${w.name}`} value={w.name}>
                      {w.scope === "global" ? "🌐 " : ""}{w.name}
                      {w.desc ? ` — ${w.desc}` : ""}
                    </option>
                  ))}
                </select>
              </label>
              {selDsl.name && onOpenWorkflow && (
                <button className="link" title="打开这个子工作流的画布"
                  onClick={() => onOpenWorkflow(String(selDsl.name))}>↗ 打开子工作流</button>
              )}
            </div>
          )}
          {selItem.fields.map((f) => (
            <label key={f.key} className="wf-field">
              {f.label}
              {f.kind !== "select" && f.kind !== "boolean" && f.kind !== "model" && varGroups.length > 0 && (
                <select className="wf-varsel" value=""
                  onChange={(e) => insertVar(f.key, e.target.value)}
                  title="插入变量（textarea 在光标处插入）">
                  <option value="">＋变量</option>
                  {varGroups.map((g) => (
                    <optgroup key={g.label} label={g.label}>
                      {g.items.map((v) => (
                        <option key={v} value={v} title={varPreview(v)}>{`\${${v}}`}</option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              )}
              {f.kind === "model" ? (
                <select value={normalizeNodeModel(selDsl[f.key])}
                  onChange={(e) => onPatch(f.key, e.target.value)}>
                  {}
                  {modelOpts.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>))}
                  {}
                  {!modelOpts.some((o) => o.value === normalizeNodeModel(selDsl[f.key])) && (
                    <option value={normalizeNodeModel(selDsl[f.key])}>
                      {QUEUE_LABELS[normalizeNodeModel(selDsl[f.key]) as keyof typeof QUEUE_LABELS]
                        ?? normalizeNodeModel(selDsl[f.key])}
                      {!!selDsl[f.key] ? "（已失效）" : "（默认，队列为空时回退）"}
                    </option>
                  )}
                </select>
              ) : f.kind === "textarea" || f.kind === "code" ? (                <textarea ref={(el) => { taRefs.current[f.key] = el; }}
                  rows={f.kind === "code" ? 10 : 4} value={selDsl[f.key] ?? ""} placeholder={f.ph}
                  onChange={(e) => onPatch(f.key, e.target.value)} />
              ) : f.kind === "select" ? (
                <select value={selDsl[f.key] ?? f.opts?.[0] ?? ""}
                  onChange={(e) => onPatch(f.key, e.target.value)}>
                  {(f.opts ?? []).map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              ) : f.kind === "number" ? (
                <input type="number" value={selDsl[f.key] ?? ""} placeholder={f.ph}
                  onChange={(e) => onPatch(f.key, e.target.value)} />
              ) : f.kind === "boolean" ? (
                <select value={selDsl[f.key] ?? "false"}
                  onChange={(e) => onPatch(f.key, e.target.value)}>
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
              ) : (
                <input value={selDsl[f.key] ?? ""} placeholder={f.ph}
                  onChange={(e) => onPatch(f.key, e.target.value)} />
              )}
            </label>
          ))}
          <details className="wf-advanced">
            <summary>高级：重试 / 超时</summary>
            <label className="wf-field">重试次数（失败后重跑）
              <input type="number" min={0} value={selDsl.retry ?? ""} placeholder="0"
                onChange={(e) => onPatch("retry", e.target.value)} />
            </label>
            <label className="wf-field">超时（秒，0 不限）
              <input type="number" min={0} value={selDsl.timeout ?? ""} placeholder="0"
                onChange={(e) => onPatch("timeout", e.target.value)} />
            </label>
          </details>
          <div className="wf-run-actions">
            {onTestRun && <button onClick={onTestRun} title="只执行该节点，不推进后续">▶ 试运行</button>}
            {onRunFrom && <button onClick={onRunFrom} title="从该节点开始运行到结束">⏩ 从此运行</button>}
            {onExtract && (
              <button onClick={onExtract} title="把从该节点起的整段链抽成独立子工作流，原位置换成一个子工作流节点">
                ⤴ 抽成子工作流
              </button>
            )}
          </div>
          <button className="danger" onClick={onDelete}>删除节点</button>
          {run?.nodes[selDsl.id] && (
            <details className="gnode-out" open>
              <summary>运行产物 · {run.nodes[selDsl.id].status}</summary>
              <NodeOutput out={run.nodes[selDsl.id].output ?? ""} />
            </details>
          )}
        </>
      ) : <div className="dim pad8">点击画布节点编辑属性；从左侧节点库点击添加节点；拖动端口连线决定执行顺序。</div>}
    </div>
  );
}
