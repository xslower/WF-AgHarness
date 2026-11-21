
import { useState } from "react";

import type { AppConfig } from "../../kernel/api";
import { LlmSessionDrawer } from "./LlmSessionLog";
import { RunLogPanel } from "./RunPanel";
import { RunWhyPanel } from "./RunWhyPanel";
import { useWorkflowRunTab } from "./useWorkflowRunTab";
import { useRunWhy } from "./useRunWhy";

export function WorkflowRunTab({ runId, workflow, project }: {
  runId: string;
  
  workflow: string;
  project: string;
}) {
  const ctl = useWorkflowRunTab({ runId, project });
  const whyCtl = useRunWhy(ctl.run?.id ?? "", project);
  const [view, setView] = useState<"run" | "chat">("run");

  return (
    <div className="wfrun-tab">
      <div className="wfrun-bar">
        <button className={`link ${view === "run" ? "on" : ""}`}
          onClick={() => setView("run")}>运行详情</button>
        <button className={`link ${view === "chat" ? "on" : ""}`}
          onClick={() => setView("chat")}>LLM 节点会话</button>
        <span className="flex1" />
        {ctl.msg && <span className="dim">{ctl.msg}</span>}
        <button className="link" title="重新拉取运行状态" onClick={() => void ctl.reload()}>
          🔄
        </button>
      </div>
      {ctl.error && <div className="error pad8">{ctl.error}</div>}
      {view === "run" ? (
        <RunLogPanel run={ctl.run}
          onCancel={() => void ctl.cancel()}
          onResume={() => void ctl.resume()}
          onRedo={(nid) => void ctl.redo(nid)}
          why={<RunWhyPanel wf={whyCtl} runId={ctl.run?.id ?? ""}
            onRedo={(nid) => void ctl.redo(nid)} />}
          onHuman={(choice, comment) => void ctl.decide(choice, comment)} />
      ) : (
        <LlmSessionDrawer
          project={project}
          workflow={workflow}
          config={null as AppConfig | null}
          run={ctl.run}
          selected=""
          focusNode={null}
          onNewSession={() => {}}
          onPickSession={() => {}}
          onClose={() => setView("run")}
          maximized={false}
          onToggleMax={() => {}}
          width={0}
          onWidth={() => {}}
          embedded />
      )}
    </div>
  );
}
