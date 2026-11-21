
import { useState, type Dispatch, type SetStateAction } from "react";
import type { AppConfig, TestResult } from "../../kernel/api";
import { QUEUE_NAMES } from "../../kernel/model/modelSpec";
import type { QueueKind } from "./modelEdit";
import { TestBadge } from "./TestBadge";

export const QUEUE_KINDS: QueueKind[] = [...QUEUE_NAMES];

const QUEUE_TITLE: Record<QueueKind, string> = {
  parent: "父队列（与你的主对话）",
  child: "子队列（子 Agent / 简单任务）",
  summary: "总结队列（上下文压缩，可放多个免费模型并发对冲）",
};

const QUEUE_EMPTY: Record<QueueKind, string> = {
  parent: "主对话将不可用",
  child: "未配置时子任务回退父队列",
  summary: "未配置时回退子队列 → 父队列",
};

interface Props {
  draft: AppConfig;
  setDraft: Dispatch<SetStateAction<AppConfig>>;
  tests: Record<string, TestResult | "pending">;
  test: (spec: string) => void;
  toggleQueue: (kind: QueueKind, spec: string) => void;
  moveQueue: (kind: QueueKind, i: number, dir: -1 | 1) => void;
}

const EMPTY_ADD = { parent: "", child: "", summary: "" };

export function QueuesTab({ draft, setDraft, tests, test, toggleQueue, moveQueue }: Props) {
  const [addProv, setAddProv] = useState<{ parent: string; child: string; summary: string }>(EMPTY_ADD);
  const [addModel, setAddModel] = useState<{ parent: string; child: string; summary: string }>(EMPTY_ADD);

  return (
    <div className="panel">
      <p className="dim">三个队列独立排序，限流/失败时各自降级。点击右侧全部模型加入/移出。
        总结队列前两个模型先发、超时后并发抢答（见设置 · 通用 · summaryHedgeMs）。</p>
      {QUEUE_KINDS.map((kind) => {
        const list = draft.queues[kind] ?? [];
        const addState = { provider: addProv[kind], model: addModel[kind] };
        return (
        <div key={kind} className="queue-group">
          <h4>{QUEUE_TITLE[kind]}</h4>
          <div className="queue-list">
            {list.map((s, i) => {
              const [pid, mid] = s.split("/");   
              const prov = draft.providers.find((x) => x.name === pid);
              const minfo = prov?.models.find((m) => m.id === mid);
              return (
              <div key={s} className="queue-item">
                <span className="queue-label">
                  {i + 1}. <b className="queue-prov">{prov?.name ?? pid}</b> · {mid}
                  {minfo?.description ? <span className="dim" title={minfo.description}> ⓘ</span> : null}
                </span>
                <span>
                  <TestBadge spec={s} tests={tests} />
                  <button className="link" onClick={() => moveQueue(kind, i, -1)}>↑</button>
                  <button className="link" onClick={() => moveQueue(kind, i, 1)}>↓</button>
                  <button className="link" onClick={() => test(s)}>测试</button>
                  <button className="link del" onClick={() => toggleQueue(kind, s)}>移除</button>
                </span>
              </div>
              );
            })}
            {list.length === 0 && <div className="dim">空（{QUEUE_EMPTY[kind]}）</div>}
          </div>
          {}
          <div className="row">
            <select value={addState.provider}
              onChange={(e) => {
                setAddProv((a) => ({ ...a, [kind]: e.target.value }));
                setAddModel((a) => ({ ...a, [kind]: "" }));
              }}>
              <option value="">＋ 选择 Provider…</option>
              {draft.providers.filter((p) => p.models.some((m) => (m.kind || "lm") === "lm" && !m.disabled))
                .map((p) => <option key={p.id} value={p.name}>{p.name}</option>)}
            </select>
            <select value={addState.model} disabled={!addState.provider}
              onChange={(e) => setAddModel((a) => ({ ...a, [kind]: e.target.value }))}>
              <option value="">选择模型…</option>
              {addState.provider && draft.providers.find((p) => p.name === addState.provider)
                ?.models.filter((m) => (m.kind || "lm") === "lm" && !m.disabled)
                .map((m) => <option key={m.id} value={m.id}
                  title={m.description}>{m.id}{m.free ? " ·free" : ""}</option>)}
            </select>
            <button disabled={!addState.provider || !addState.model}
              onClick={() => {
                const spec = `${addState.provider}/${addState.model}`;
                if (!(draft.queues[kind] ?? []).includes(spec)) toggleQueue(kind, spec);
              }}>加入</button>
          </div>
        </div>
        );
      })}
      <h4 className="q-title" style={{ marginTop: 10 }}>功能专用模型（各可选 2 个依序尝试；四项留空=禁用，不发请求不调模型、也不回退队列；只有显式选了模型才启用）</h4>
      {(["completion", "classify", "review", "suggest"] as const).map((kind) => {
        const label = { completion: "输入补全", classify: "轻量分类", review: "安全评审", suggest: "快捷建议" }[kind];
        const slots = draft.utility?.[kind] ?? ["", ""];
        const setSlot = (i: number, v: string) => {
          const arr = [...slots];
          arr[i] = v;
          setDraft((d) => ({
            ...d,
            utility: { ...(d.utility ?? { completion: [], classify: [], review: [], suggest: [] }), [kind]: arr.filter(Boolean) },
          }));
        };
        return (
          <div key={kind} className="row utility-row">
            <span className="dim utility-label">{label}</span>
            {[0, 1].map((i) => (
              <select key={i} value={slots[i] ?? ""}
                onChange={(e) => setSlot(i, e.target.value)}>
                <option value="">（禁用）</option>
                {draft.providers.map((p) => (
                  <optgroup key={p.id} label={p.name}>
                    {p.models.filter((m) => (m.kind || "lm") === "lm" && !m.disabled)
                      .map((m) => <option key={m.id} value={`${p.name}/${m.id}`}>{m.id}</option>)}
                  </optgroup>
                ))}
              </select>
            ))}
          </div>
        );
      })}
      <p className="dim">队列与功能模型的变更会自动保存</p>
    </div>
  );
}
