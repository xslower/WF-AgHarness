
import type { UsageBucket, UsageSummary } from "../../api";
import { fmtCostText, fmtTokens } from "../format";
import { useUsageSummary } from "./useUsageSummary";

type Row = UsageBucket;


function usageText(v: Row): string {
  return `${v.calls} 次 · ${fmtTokens(v.prompt)} in / ${fmtTokens(v.completion)} out`
    + (v.cost > 0 ? ` · ${fmtCostText(v.cost)}` : "");
}


export function UsageTable() {
  const { data, open, toggle } = useUsageSummary();

  if (!data) return <div className="dim">加载中…</div>;
  const entries = Object.entries(data.by_provider || {});
  const totalCalls = entries.reduce((s, [, v]) => s + v.calls, 0);
  return (
    <>
      <p className="dim">
        今日成本 ¥{data.today_cost} · 总成本 ¥{data.total_cost} · 共 {totalCalls} 次调用
        （单价在模型设置里配）
      </p>
      {entries.length === 0 && <div className="dim pad8">还没有用量记录</div>}
      {entries.map(([name, v]) => (
        <ProviderUsage key={name} name={name} v={v}
          expanded={open.has(name)} onToggle={() => toggle(name)} />
      ))}
    </>
  );
}


function ProviderUsage({ name, v, expanded, onToggle }: {
  name: string; v: UsageSummary["by_provider"][string];
  expanded: boolean; onToggle: () => void;
}) {
  const models = Object.entries(v.models || {});
  return (
    <div>
      <div className="queue-item usage-prov" onClick={onToggle} style={{ cursor: "pointer" }}>
        <span>
          <span className="usage-caret">{models.length ? (expanded ? "▾" : "▸") : "·"}</span>
          {name}
        </span>
        <span className="dim">{usageText(v)}</span>
      </div>
      {expanded && models.map(([m, mv]) => (
        <div key={m} className="queue-item usage-model">
          <span>{m}</span>
          <span className="dim">{usageText(mv)}</span>
        </div>
      ))}
    </div>
  );
}

export function UsagePanel({ onClose }: { onClose: () => void }) {
  return (
    <div className="modal-mask">
      <div className="modal">
        <div className="modal-head">
          <b>用量统计</b>
          <button className="link" onClick={onClose}>关闭</button>
        </div>
        <UsageTable />
      </div>
    </div>
  );
}
