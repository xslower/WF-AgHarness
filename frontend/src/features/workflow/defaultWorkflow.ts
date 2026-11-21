
import type { WorkflowDef } from "../../kernel/api";


const NODES = [
  { id: "s1", type: "llm", prompt: "围绕以下主题列出3个关键点：${inputs.input}", next: "c1" },
  { id: "c1", type: "condition", expr: "len(${s1}) > 50", true: "w1", false: "s2" },
  { id: "w1", type: "write", path: "out/report.md", content: "${s1}", next: "h1" },
  { id: "s2", type: "llm", prompt: "把内容扩写到50字以上：${s1}", next: "w1" },
  { id: "h1", type: "handoff" },
] as never;  


export function newWorkflow(name = ""): WorkflowDef {
  return {
    name,
    desc: "",
    inputs: [{ name: "input", desc: "输入文本", type: "string" }],
    nodes: NODES,
  };
}
