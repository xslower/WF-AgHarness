
import { useState } from "react";

import type { WfWhy, WfWhyDigest } from "../../kernel/api";
import { Icon } from "../../kernel/ui/icons";
import type { WhyController, WhyQuery } from "./useRunWhy";


function DigestRow({ d, onPick }: { d: WfWhyDigest; onPick: (nid: string) => void }) {
  return (
    <button type="button" className={`wfwhy-row ${d.empty ? "empty" : ""}`}
      title={d.error || (d.empty ? "这一跳完成了但产出为空（静默少一块）" : "看这一跳的血缘")}
      onClick={() => onPick(d.node)}>
      <code className="wfwhy-node">{d.node}</code>
      <span className="wfwhy-status">{d.status}</span>
      <span className="wfwhy-chars">{d.chars} 字</span>
      {d.empty && <span className="wfwhy-warn"><Icon name="alert" /> 空产出</span>}
      <span className="flex1" />
      <span className="wfwhy-meta" title={`读：${d.reads.join(", ") || "（无）"}`}>
        ← {d.reads.length || 0}
      </span>
    </button>
  );
}


function VarChips({ names, onPick }: { names: string[]; onPick: (n: string) => void }) {
  if (!names.length) return <span className="dim">（无）</span>;
  return (
    <span className="wfwhy-chips">
      {names.map((n) =>
        n.startsWith("inputs.") ? (
          <code key={n} className="wfwhy-chip dim">{n}</code>
        ) : (
          <button key={n} type="button" className="wfwhy-chip"
            title={`看节点 ${n} 的血缘`} onClick={() => onPick(n)}>{n}</button>
        ))}
    </span>
  );
}

export function RunWhyPanel({ wf, runId, onRedo }: {
  wf: WhyController;
  
  runId: string;
  
  onRedo?: (nodeId: string) => void;
}) {
  const [mode, setMode] = useState<WhyQuery["mode"]>("overview");
  const [value, setValue] = useState("");

  const submit = () => {
    const v = value.trim();
    if (mode !== "overview" && !v) return;
    void wf.ask({ mode, value: mode === "overview" ? "" : v });
  };
  const pickNode = (nid: string) => {
    setMode("node");
    setValue(nid);
    void wf.ask({ mode: "node", value: nid });
  };

  return (
    <div className="wfwhy">
      <div className="wfwhy-bar">
        <select className="wfwhy-mode" value={mode}
          onChange={(e) => { setMode(e.target.value as WhyQuery["mode"]); setValue(""); }}>
          <option value="overview">概览（哪一跳是空的）</option>
          <option value="node">这一跳</option>
          <option value="key">谁用这个变量</option>
          <option value="grep">哪一跳提到</option>
        </select>
        {mode !== "overview" && (
          <input className="wfwhy-input" value={value} placeholder={
            mode === "node" ? "节点 id（如 s2）"
              : mode === "key" ? "变量名（如 s1 或 inputs.q）" : "关键词"}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") submit(); }} />
        )}
        <button className="link" onClick={submit}
          disabled={!runId || wf.loading}>{
          wf.loading ? "查询中…" : mode === "overview" ? "刷新概览" : "查询"}</button>
        <span className="flex1" />
        {wf.error && <span className="wfwhy-err">{wf.error}</span>}
      </div>
      {!runId && <div className="wf-run-empty">先打开一条运行再看出处</div>}
      {runId && <WhyBody data={wf.data} loading={wf.loading} onPick={pickNode}
        onRedo={onRedo} />}
    </div>
  );
}


function WhyBody({ data, loading, onPick, onRedo }: {
  data: WfWhy | null;
  loading: boolean;
  onPick: (nid: string) => void;
  onRedo?: (nid: string) => void;
}) {
  if (!data) {
    return <div className="wf-run-empty">{loading ? "读取中…" : "选一种问法看血缘"}</div>;
  }
  if (data.query === "overview") {
    if (!data.nodes.length) return <div className="wf-run-empty">这次运行还没有节点产出</div>;
    return (
      <div className="wfwhy-list">
        {data.nodes.map((d) => <DigestRow key={d.node} d={d} onPick={onPick} />)}
      </div>
    );
  }
  if (data.query === "node") {
    return (
      <div className="wfwhy-detail">
        <div className="wfwhy-line">
          <span className="wfwhy-label">节点</span>
          <code>{data.node}</code>
          <span className="dim">{data.status} · {data.chars} 字
            {data.ms != null ? ` · ${data.ms}ms` : ""}</span>
          <span className="flex1" />
          {onRedo && <button className="link"
            title="从这一跳重跑，上游回放不重算"
            onClick={() => onRedo(data.node)}>↻ 重跑这一跳</button>}
        </div>
        <div className="wfwhy-line">
          <span className="wfwhy-label">读了</span><VarChips names={data.reads} onPick={onPick} />
        </div>
        <div className="wfwhy-line">
          <span className="wfwhy-label">写了</span><VarChips names={data.writes} onPick={onPick} />
        </div>
        {data.path && (
          <div className="wfwhy-line">
            <span className="wfwhy-label">原文</span>
            <code className="wfwhy-path" title={data.path}>{data.path}</code>
          </div>
        )}
        {data.preview && <pre className="wfwhy-preview">{data.preview}</pre>}
      </div>
    );
  }
  if (data.query === "key") {
    return (
      <div className="wfwhy-detail">
        <div className="wfwhy-line">
          <span className="wfwhy-label">写了</span>
          <VarChips names={data.writers} onPick={onPick} />
        </div>
        <div className="wfwhy-line">
          <span className="wfwhy-label">读了</span>
          <VarChips names={data.readers} onPick={onPick} />
        </div>
        {!data.writers.length && !data.readers.length && (
          <div className="wf-run-empty">没人写过也没人读过 {data.key}</div>
        )}
      </div>
    );
  }
  if (!data.hits.length) {
    return <div className="wf-run-empty">没有节点产出里出现「{data.grep}」</div>;
  }
  return (
    <div className="wfwhy-list">
      {data.hits.map((h) => (
        <button key={h.node} type="button" className="wfwhy-hit"
          title={`看节点 ${h.node} 的血缘`} onClick={() => onPick(h.node)}>
          <code className="wfwhy-node">{h.node}</code>
          <span className="dim">{h.chars} 字 · 第 {h.at} 字处</span>
          <pre className="wfwhy-snippet">{h.snippet}</pre>
        </button>
      ))}
    </div>
  );
}
