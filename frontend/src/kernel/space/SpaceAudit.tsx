
import { useEffect, useState } from "react";
import { auditSpace, SpaceIssue } from "./space";

export function useSpaceAudit(): { issues: SpaceIssue[] | null; close: () => void } {
  const [issues, setIssues] = useState<SpaceIssue[] | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && (e.key === "U" || e.key === "u")) {
        e.preventDefault();
        setIssues((cur) => (cur === null ? auditSpace() : null));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return { issues, close: () => setIssues(null) };
}

export function SpaceAuditPanel({ issues, onClose }: { issues: SpaceIssue[]; onClose: () => void }) {
  return (
    <div className="space-audit">
      <div className="space-audit-head">
        <b>空间审计（{issues.length} 个问题）</b>
        <button className="link" onClick={onClose}>关闭</button>
      </div>
      {issues.length === 0 && <div className="dim pad8">未发现溢出/换行/裁切问题</div>}
      {issues.slice(0, 50).map((s, i) => (
        <div key={i} className="space-audit-item">
          <span
            className={`sev sev-${s.issue === "clipped" ? "high" : s.issue === "overflow-x" ? "medium" : "low"}`}>
            {s.issue}
          </span>
          <code>{s.selector.slice(0, 60)}</code>
          <span className="dim">{s.detail}</span>
        </div>
      ))}
    </div>
  );
}
