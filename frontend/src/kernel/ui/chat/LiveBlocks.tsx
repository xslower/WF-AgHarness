
import { Icon } from "../icons";
import { StreamingMarkdown } from "../markdown";
import { tailLine } from "./msgFormat";
import { SubAgentCard } from "./SubAgentCard";
import { toolLabel } from "./toolLabel";
import { openSubAgentTab } from "../../chat/subAgentTab";
import { runIdFromResult } from "../../chat/workflowRunTab";
import { OpenRunButton } from "./OpenRunButton";
import type { LiveEvent, SubAgent } from "../../chat/chatTypes";


export function wfRunIdOf(e: LiveEvent): string {
  if (e.toolName !== "workflow") return "";
  return e.wfRunId || runIdFromResult(e.result);
}


interface SubAgentCtx {
  reasonPreRef: React.RefObject<HTMLPreElement>;
  subAgents: Record<string, SubAgent>;
  activeSubAgent: string | null;
  setActiveSubAgent: (id: string | null) => void;
  onQuerySubAgent?: (id: string) => void | Promise<void>;
  onMessageSubAgent?: (id: string, text: string) => void | Promise<boolean>;
  onStopSubAgent?: (id: string) => void | Promise<void>;
}

export function LiveBlocks({ live, ...ctx }: { live: LiveEvent[] } & SubAgentCtx) {
  return (
    <>
      {live.map((e, i) => (
        <LiveBlock key={i} e={e} {...ctx} />
      ))}
    </>
  );
}

function LiveBlock({ e, ...ctx }: { e: LiveEvent } & SubAgentCtx) {
  const { reasonPreRef, subAgents, activeSubAgent, setActiveSubAgent,
    onQuerySubAgent, onMessageSubAgent, onStopSubAgent } = ctx;
  if (e.kind === "text") {
    return (
      <div className="msg assistant">
        <div className="msg-role">助手</div>
        <div className="msg-body md-body">
          {}
          <StreamingMarkdown text={e.text} streaming />
        </div>
      </div>
    );
  }
  if (e.kind === "reason") {
    return (
      <details className="tool-block reasoning-block" open>
        <summary><Icon name="thought" /> 思考中…</summary>
        <pre className="wrap" ref={reasonPreRef}
          style={{ maxHeight: "40vh", overflowY: "auto" }}>{e.text}</pre>
      </details>
    );
  }
  if (e.kind === "notice") return <div className="notice">⇄ {e.text}</div>;
  if (e.kind === "error") return <div className="error">✗ {e.text}</div>;

  
  if (e.kind === "subagent") {
    const sa = e.subagentId ? subAgents[e.subagentId] : undefined;
    if (!sa) return null;
    return (
      <SubAgentCard sa={sa} active={activeSubAgent === sa.id}
        onToggle={() => setActiveSubAgent(activeSubAgent === sa.id ? null : sa.id)}
        onOpenTab={() => openSubAgentTab({ id: sa.id, task: sa.task })}
        onQuery={onQuerySubAgent}
        onMessage={onMessageSubAgent}
        onStop={onStopSubAgent} />
    );
  }

  const label = toolLabel(e.toolName ?? "", e.args);
  const wfRunId = wfRunIdOf(e);
  return (
    <details className="tool-block live">
      <summary>
        <Icon name="wrench" /> {label.title}
        {label.detail && <span className="tool-detail"> {label.detail}</span>}
        {" "}{e.result ? "✓" : "运行中…"}
        {}
        {!e.result && e.output && <span className="tool-tail">{tailLine(e.output)}</span>}
        {}
        {wfRunId ? (
          <OpenRunButton runId={wfRunId}
            workflow={String((e.args as { name?: string } | undefined)?.name || "")} />
        ) : null}
      </summary>
      <pre>{JSON.stringify(e.args, null, 2)}</pre>
      {e.output && <pre className="tool-stream">{e.output}</pre>}
      {e.result && <pre className="tool-result">{e.result}</pre>}
    </details>
  );
}
