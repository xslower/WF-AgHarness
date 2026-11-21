
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { usePaletteItem, type FlowNodeData } from "./dsl";

export function DslNode({ data, selected }: NodeProps) {
  const d = data as FlowNodeData;
  const item = usePaletteItem(String(d.dsl.type));
  const st = d.status as string | undefined;
  return (
    <div className={`rfnode t-${item.type} s-${st ?? "idle"} ${selected ? "sel" : ""}`}>
      <Handle type="target" position={Position.Top} />
      <div className="rfnode-head">{item.icon} <b>{String(d.dsl.id)}</b>
        <span className="rfnode-type">{item.label}</span></div>
      <div className="rfnode-body">{item.desc}</div>
      {item.type === "condition" || item.type === "human" ? (
        <>
          <Handle type="source" id="true" position={Position.Bottom} style={{ left: "25%" }} />
          <Handle type="source" id="false" position={Position.Bottom} style={{ left: "75%" }} />
          <div className="rfnode-ports"><span>◦{item.type === "human" ? "批准" : "true"}</span><span>{item.type === "human" ? "驳回" : "false"}◦</span></div>
        </>
      ) : item.type === "loop" || item.type === "map" ? (
        <>
          <Handle type="source" position={Position.Bottom} />
          <Handle type="source" id="body" position={Position.Right} style={{ right: -14 }} />
          <div className="rfnode-ports"><span>{String(d.dsl.body) || "◦body"}</span><span>next◦</span></div>
        </>
      ) : (
        <Handle type="source" position={Position.Bottom} />
      )}
    </div>
  );
}

export const nodeTypes = { dsl: DslNode };
