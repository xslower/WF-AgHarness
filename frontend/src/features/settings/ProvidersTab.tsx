
import { Fragment, useState, type Dispatch, type SetStateAction } from "react";
import type { AppConfig, Provider, TestResult } from "../../kernel/api";
import { DAYS, mSchedLabel, patchMId, patchP, patchSchedules } from "./modelEdit";
import { TestBadge } from "./TestBadge";
import { removeModelFromDraft, type ProviderEditor } from "./useProviderEditor";
import { kToTokens, tokensToK } from "../../kernel/ui/format";
import { InlineValue } from "../../kernel/ui/InlineValue";

interface Props {
  draft: AppConfig;
  setDraft: Dispatch<SetStateAction<AppConfig>>;
  flash: (t: string) => void;
  adoptConfig: (c: AppConfig) => void;
  provider: ProviderEditor;
}

type Tests = Record<string, TestResult | "pending">;

export function ProvidersTab({ draft, setDraft, flash, provider }: Props) {
  const { editingId, editingNew, savingKey, modelEdit, setModelEdit,
          beginEdit, cancelEdit, addProvider, saveProvider, pullModels,
          removeProvider, importEnv, saveModelSettings, tests, test } = provider;

  return (
    <div className="panel">
      <div className="row">
        <button onClick={() => void importEnv()}>
          从环境变量导入（OpenRouter/硅基/DeepSeek/Gemini/Groq…）
        </button>
      </div>
      {draft.providers.map((p, idx) => {
        
        
        
        const isEditing = p.id ? editingId === p.id : editingNew;
        const busy = savingKey !== null && savingKey === (p.id || "new");
        return isEditing ? (
          <ProviderEditorCard key={p.id || `new-${idx}`} p={p} idx={idx} busy={busy}
            setDraft={setDraft} saveProvider={saveProvider} pullModels={pullModels}
            removeProvider={removeProvider} onCancelEdit={cancelEdit} />
        ) : (
          <ProviderCard key={p.id} p={p} idx={idx}
            modelEdit={modelEdit} setModelEdit={setModelEdit}
            onEdit={beginEdit} pullModels={pullModels} flash={flash}
            setDraft={setDraft} tests={tests} test={test}
            saveModelSettings={saveModelSettings} />
        );
      })}
      <button onClick={addProvider}>+ 添加 Provider</button>
    </div>
  );
}


function ProviderEditorCard({ p, idx, busy, setDraft, saveProvider, pullModels, removeProvider, onCancelEdit }: {
  p: Provider; idx: number; busy: boolean;
  setDraft: Dispatch<SetStateAction<AppConfig>>;
  saveProvider: (idx: number) => Promise<Provider | null>;
  pullModels: (idx: number) => Promise<void>;
  removeProvider: (idx: number) => Promise<void>;
  onCancelEdit: () => void;
}) {
  return (
    <div className="provider-card editing">
      <div className="row">
        <input value={p.name} placeholder="名称" autoFocus
          onChange={(e) => patchP(setDraft, idx, { name: e.target.value })} />
        <input value={p.baseUrl} placeholder="https://host/v1"
          onChange={(e) => patchP(setDraft, idx, { baseUrl: e.target.value })} />
      </div>
      <input value={p.apiKey} placeholder="API Key" type="password"
        onChange={(e) => patchP(setDraft, idx, { apiKey: e.target.value })} />
      <input value={p.dailyFreeQuota ?? 1_000_000} type="number"
        title="免费模型每日 token 保护上限（按模型计，达到即停用防静默扣费，0=不限）"
        placeholder="免费每日保护上限 tokens（默认 1000000）"
        onChange={(e) => patchP(setDraft, idx, { dailyFreeQuota: +e.target.value })} />
      <input value={p.cooldownSec ?? 60} type="number" min={0}
        title="命中限流(429)后这个 provider 冷却多少秒。分钟级限流填 60；几小时限流的（如局域网 wb-*）填 14400"
        placeholder="限流冷却秒数（默认 60，小时级填 14400）"
        onChange={(e) => patchP(setDraft, idx, { cooldownSec: +e.target.value })} />
      <div className="row">
        {}
        <button className="primary" disabled={busy} onClick={() => void saveProvider(idx)}>
          {busy ? "保存中…" : "保存"}
        </button>
        <button disabled={busy} onClick={onCancelEdit}>取消</button>
        <button disabled={busy} onClick={() => void pullModels(idx)}>拉取模型</button>
        {p.id && <button className="danger" disabled={busy} onClick={() => void removeProvider(idx)}>删除</button>}
      </div>
    </div>
  );
}


function ProviderCard(props: {
  p: Provider; idx: number;
  modelEdit: string | null; setModelEdit: (v: string | null) => void;
  onEdit: (p: Provider) => void; pullModels: (idx: number) => Promise<void>;
  flash: (t: string) => void; setDraft: Dispatch<SetStateAction<AppConfig>>;
  tests: Tests; test: (spec: string) => Promise<void>;
  saveModelSettings: (p: Provider) => Promise<boolean>;
}) {
  const { p, idx, modelEdit, setModelEdit, onEdit, pullModels } = props;
  return (
    <div className="provider-card saved">
      <div className="saved-head" onClick={() => onEdit(p)}>
        <span className="saved-name">{p.name}</span>
        <span className="dim">{p.baseUrl} · {p.models.length} 个模型</span>
        <span onClick={(e) => e.stopPropagation()}>
          <button className="link" onClick={() => onEdit(p)}>编辑</button>
          <button className="link" onClick={() => void pullModels(idx)}>拉取模型</button>
          <button className="link" onClick={() => setModelEdit(modelEdit === p.id ? null : p.id)}>模型设置</button>
        </span>
      </div>
      {p.note && <div className="provider-note" title={p.note}>{p.note}</div>}
      {modelEdit === p.id && <ModelEditPanel {...props} />}
    </div>
  );
}


function ModelEditPanel({ p, idx, setDraft, flash, tests, test, saveModelSettings, setModelEdit }: {
  p: Provider; idx: number;
  setDraft: Dispatch<SetStateAction<AppConfig>>;
  flash: (t: string) => void;
  tests: Tests;
  test: (spec: string) => Promise<void>;
  saveModelSettings: (p: Provider) => Promise<boolean>;
  setModelEdit: (v: string | null) => void;
}) {
  
  const [schedEdit, setSchedEdit] = useState<string | null>(null);
  const [mFilter, setMFilter] = useState<{ kind: string; freeOnly: boolean }>({ kind: "", freeOnly: false });


  const shown = p.models.filter((m) => (!mFilter.kind || (m.kind || "lm") === mFilter.kind)
    && (!mFilter.freeOnly || m.free));

  return (
    <div className="model-edit">
      <div className="row model-filter">
        <select value={mFilter.kind} onChange={(e) => setMFilter((f) => ({ ...f, kind: e.target.value }))}>
          <option value="">全部类型</option>
          <option value="lm">LM 对话</option>
          <option value="image">生图/视频</option>
          <option value="asr">语音</option>
          <option value="embedding">向量/检索</option>
          <option value="ocr">OCR</option>
          <option value="mt">翻译</option>
        </select>
        <label className="chk-row">
          <input type="checkbox" checked={mFilter.freeOnly}
            onChange={(e) => setMFilter((f) => ({ ...f, freeOnly: e.target.checked }))} />
          只看免费
        </label>
        <span className="dim">{p.models.length} 个模型</span>
      </div>
      {shown.map((m) => (
        <Fragment key={m.id}>
          <ModelRow m={m} p={p} idx={idx} setDraft={setDraft} flash={flash}
            tests={tests} test={test}
            schedEdit={schedEdit} setSchedEdit={setSchedEdit} />
          {schedEdit === m.id && <ScheduleEditor m={m} idx={idx} setDraft={setDraft} />}
        </Fragment>
      ))}
      <div className="row">
        <button className="primary" onClick={async () => {
          if (await saveModelSettings(p)) setModelEdit(null); 
        }}>保存模型设置</button>
      </div>
    </div>
  );
}

const KIND_CYCLE: Record<string, string> = {
  lm: "image", image: "asr", asr: "embedding", embedding: "ocr", ocr: "mt", mt: "lm",
};


function ModelRow({ m, p, idx, setDraft, flash, tests, test,
  schedEdit, setSchedEdit }: {
  m: Provider["models"][number]; p: Provider; idx: number;
  setDraft: Dispatch<SetStateAction<AppConfig>>;
  flash: (t: string) => void;
  tests: Tests; test: (spec: string) => Promise<void>;
  schedEdit: string | null; setSchedEdit: (v: string | null) => void;
}) {
  const spec = `${p.name}/${m.id}`;
  const kind = m.kind || "lm";
  return (
    <div className="model-edit-row">
      <span className={`kind-tag k-${kind}`} title={`类型 ${kind}（点击切换）`}
        onClick={() => patchMId(setDraft, idx, m.id, { kind: KIND_CYCLE[kind] })}>{kind}</span>
      <span className={`tgl t-free ${m.free ? "on" : ""}`} title="免费"
        onClick={() => patchMId(setDraft, idx, m.id, { free: !m.free })}>¥0</span>
      <span className={`tgl t-disable ${m.disabled ? "on" : ""}`}
        title={m.disabled ? "已禁用（队列中跳过，点击恢复）" : "禁用（模型保留但队列跳过，点击启用）"}
        onClick={() => patchMId(setDraft, idx, m.id, { disabled: !m.disabled })}>🚫</span>
      {kind === "lm" && <>
        <span className={`tgl ${m.supportsThinking ? "on" : ""}`} title="支持思考"
          onClick={() => patchMId(setDraft, idx, m.id, { supportsThinking: !m.supportsThinking })}>🧠</span>
        <span className={`tgl ${m.supportsImages ? "on" : ""}`} title="支持图片输入"
          onClick={() => patchMId(setDraft, idx, m.id, { supportsImages: !m.supportsImages })}>🖼</span>
        <InlineValue chipClass="ctx-chip" inputClass="ctx-input"
          kind="number" min={1} value={String(tokensToK(m.contextLength))}
          title="上下文长度（K tokens），点击编辑；回车确认，Esc 取消"
          display={(v) => `${v}K`}
          onCommit={(raw) => {
            const k = Math.round(+raw);
            if (Number.isFinite(k) && k >= 1)
              patchMId(setDraft, idx, m.id, { contextLength: kToTokens(k) });
          }} />
        <span className={`tgl ${m.schedules?.length ? "on" : ""}`}
          title={`可用时段：${mSchedLabel(m)}（点击编辑）`}
          onClick={() => setSchedEdit(schedEdit === m.id ? null : m.id)}>⏰</span>
      </>}
      <span className="model-name" title={kind !== "lm" ? (m.description || m.id) : m.id}>{m.id}</span>
      <TestBadge spec={spec} tests={tests} />
      <button className="link" title="测试模型" onClick={() => void test(spec)}>🧪</button>
      <button className="link del" title="移除" onClick={async () => {
        const ok = await removeModelFromDraft(setDraft, p.id, m.id);
        flash(ok ? "✓ 已移除" : "✗ 移除失败");
      }}>✕</button>
    </div>
  );
}


function ScheduleEditor({ m, idx, setDraft }: {
  m: Provider["models"][number]; idx: number;
  setDraft: Dispatch<SetStateAction<AppConfig>>;
}) {
  const scheds = m.schedules ?? [];
  const set = (v: Provider["models"][number]["schedules"]) =>
    patchSchedules(setDraft, idx, m.id, v ?? []);
  const patchAt = (si: number, patch: Partial<(typeof scheds)[number]>) =>
    set(scheds.map((x, xi) => (xi === si ? { ...x, ...patch } : x)));
  const toggleDay = (si: number, d: number) => {
    const days = scheds[si].days ?? [];
    patchAt(si, { days: days.includes(d) ? days.filter((v) => v !== d) : [...days, d] });
  };

  return (
    <div className="sched-editor">
      {scheds.map((s, si) => (
        <div key={si} className="sched-row">
          {[0, 1, 2, 3, 4, 5, 6].map((d) => (
            <span key={d} className={`tgl day-tgl ${(s.days ?? []).includes(d) ? "on" : ""}`}
              title={`周${DAYS[d]}`} onClick={() => toggleDay(si, d)}>{DAYS[d]}</span>
          ))}
          <input type="time" value={s.start}
            onChange={(e) => patchAt(si, { start: e.target.value })} />
          ~
          <input type="time" value={s.end}
            onChange={(e) => patchAt(si, { end: e.target.value })} />
          <button className="link del" onClick={() => set(scheds.filter((_, xi) => xi !== si))}>删</button>
        </div>
      ))}
      <button onClick={() => set([...scheds, { days: [0, 1, 2, 3, 4], start: "18:00", end: "09:00" }])}>
        + 添加时段
      </button>
      {scheds.length > 0 && (
        <button className="link del" onClick={() => set([])}>清除（全天可用）</button>
      )}
      <button onClick={() => set([...scheds, { days: [], start: "00:00", end: "23:59" }])}>+ 全天</button>
      <span className="dim"> 周几不选=每天；范围外自动跳过该模型，恢复后回到原排序。start&gt;end 表示到次日（如 22:00~07:00=次日凌晨7点）。</span>
    </div>
  );
}
