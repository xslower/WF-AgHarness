
import { useEffect, useRef, useState } from "react";
import type { TodoItem } from "./useChatStream";
import { Icon, type IconName } from "../icons";

interface Props {
  todos: TodoItem[];
}


export function todoCollapsed(
  todos: Pick<TodoItem, "status">[],
  manual: boolean | null,
): boolean {
  const total = todos.length;
  const allDone = total > 0 && todos.every((t) => t.status === "done");
  if (manual === null) return allDone;
  return !manual;
}

const ICON: Record<string, IconName> = {
  pending: "circle",
  in_progress: "dot",
  done: "check",
};

export function TodoPanel({ todos }: Props) {
  const total = todos?.length ?? 0;
  const done = (todos ?? []).filter((t) => t.status === "done").length;
  const allDone = total > 0 && done === total;
  
  const [manual, setManual] = useState<boolean | null>(null);
  
  const prevAllDone = useRef(allDone);

  useEffect(() => {
    
    if (allDone !== prevAllDone.current || !allDone) setManual(null);
    prevAllDone.current = allDone;
  }, [allDone]);

  if (total === 0) return null;

  
  const collapsed = todoCollapsed(todos ?? [], manual);

  return (
    <div className="todo-panel" style={{
      margin: "0 12px 8px",
      padding: "8px 12px",
      border: "1px solid var(--border, #333)",
      borderRadius: 8,
      fontSize: 13,
      background: "var(--bg2, #1a1a1a)",
      
      maxHeight: collapsed ? undefined : "30vh",
      overflowY: collapsed ? "visible" : "auto",
    }}>
      <div
        className="todo-head"
        style={{
          fontWeight: 600,
          display: "flex", alignItems: "center", gap: 8,
          cursor: allDone ? "pointer" : "default",
        }}
        onClick={() => { if (allDone) setManual(collapsed); }}
        title={allDone ? (collapsed ? "展开查看已完成的任务" : "收起任务清单") : undefined}
      >
        <Icon name="plan" /> 任务清单
        <span style={{ fontWeight: 400, opacity: 0.7 }}>{done}/{total} 完成</span>
        <span style={{
          flex: 1, height: 4, borderRadius: 2, background: "var(--border, #333)",
          overflow: "hidden", display: "inline-block",
        }}>
          <span style={{
            display: "block", height: "100%",
            width: `${(done / total) * 100}%`,
            background: "#4caf50", transition: "width .3s",
          }} />
        </span>
        {allDone && <span className="todo-toggle">{collapsed ? "▸" : "▾"}</span>}
      </div>
      {!collapsed && todos.map((t, i) => (
        <div key={i} style={{
          display: "flex", gap: 6, alignItems: "baseline",
          opacity: t.status === "done" ? 0.55 : 1,
          textDecoration: t.status === "done" ? "line-through" : "none",
          padding: "1px 0",
        }}>
          <span><Icon name={ICON[t.status] || "circle"} /></span>
          <span>{t.content}</span>
        </div>
      ))}
    </div>
  );
}
