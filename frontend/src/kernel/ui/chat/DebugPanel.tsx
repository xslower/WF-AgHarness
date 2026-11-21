
import { useState } from "react";
import { startDrag } from "../drag";
import type { DebugLog } from "./useChatStream";

interface Props {
  logs: DebugLog[];
  onClear: () => void;
  onClose: () => void;
}

export function DebugPanel({ logs, onClear, onClose }: Props) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);

  const onDrag = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const rect = (e.currentTarget.closest(".debug-panel") as HTMLElement)?.getBoundingClientRect();
    const baseX = rect?.left ?? 0;
    const baseY = rect?.top ?? 0;
    startDrag({
      startX: e.clientX,
      startY: e.clientY,
      cursor: "move",
      onMove: (dx, dy) => setPos({ x: Math.max(0, baseX + dx), y: Math.max(0, baseY + dy) }),
    });
  };

  return (
    <div className="debug-panel" style={pos ? { left: pos.x, top: pos.y, right: "auto" } : undefined}>
      <div className="debug-head" onMouseDown={onDrag} style={{ cursor: "move" }}>
        <b>Debug 信息</b>
        <span className="dim">{logs.length} 条记录</span>
        <span className="flex1" />
        <button className="link" onClick={onClear}>清空</button>
        <button className="link" onClick={onClose}>关闭</button>
      </div>
      <div className="debug-body">
        {logs.map((d, i) => (
          <details key={i} className="debug-item">
            <summary>
              <span className={`debug-tag ${d.event === "request" ? "req" : "res"}`}>
                {d.event === "request" ? "→" : "←"}
              </span>
              {d.event === "request" ? `R${d.round} 请求` : `R${d.round} 响应`}
              {d.model && <span className="dim"> · {d.model}</span>}
              {d.usage && (
                <span className="dim"> · {d.usage.prompt_tokens + d.usage.completion_tokens} tokens</span>
              )}
              {d.has_tool_calls && <span className="dim"> · 工具调用</span>}
            </summary>
            <pre className="debug-pre">{JSON.stringify(d, null, 2)}</pre>
          </details>
        ))}
        {!logs.length && <div className="dim pad8">暂无 debug 记录</div>}
      </div>
    </div>
  );
}
