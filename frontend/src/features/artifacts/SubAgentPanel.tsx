
import type { SubAgentSummary } from "../../kernel/api/domains/subagents";
import { fmtTime } from "../../kernel/ui/format";
import { Icon } from "../../kernel/ui/icons";
import { openSubAgentTab } from "../../kernel/chat/subAgentTab";
import type { SubAgentList } from "./useSubAgents";

const STATUS_LABEL: Record<string, string> = {
  running: "运行中",
  done: "完成",
  failed: "失败",
  stopped: "已中止",
};


function row(it: SubAgentSummary) {
  return (
    <div key={it.id} className="art-subagent-row">
      <div className="art-item" title={`${it.task}\n${STATUS_LABEL[it.status] ?? it.status}`}
        onClick={() => openSubAgentTab({ id: it.id, task: it.task })}>
        <span className="art-name">
          {it.status === "running" ? "⏳" : it.status === "done" ? "✓" : "✕"} {it.task}
        </span>
        <span className="dim">{fmtTime(it.created_at)}</span>
      </div>
    </div>
  );
}

export function SubAgentPanel({ ctl }: {
  
  ctl: SubAgentList;
}) {

  return (
    <div className="art-subagents">
      <div className="q-title">
        <Icon name="robot" /> 子 Agent
        <button className="link" title="刷新列表" onClick={() => void ctl.reload()}>🔄</button>
      </div>
      {ctl.error && <div className="dim pad8">读取失败：{ctl.error}</div>}
      {!ctl.list && !ctl.error && <div className="dim pad8">加载中…</div>}
      {ctl.list && ctl.list.length === 0 && <div className="dim pad8">本会话还没有子 Agent</div>}
      {(ctl.list ?? []).map((it) => row(it))}
    </div>
  );
}
