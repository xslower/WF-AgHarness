import { useState } from "react";
import type { ApprovalItem } from "../../api";
import { useApprovalDecide } from "./useApprovalDecide";

interface Props {
  item: ApprovalItem;
  onDone: () => void;
}


export function ApprovalCard({ item, onDone }: Props) {
  const [checked, setChecked] = useState<Set<number>>(
    new Set(item.file_diff?.hunks.map((h) => h.id) ?? []),
  );
  const decide = useApprovalDecide(item, onDone);

  const toggle = (id: number) => {
    setChecked((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id); else n.add(id);
      return n;
    });
  };

  const isFile = item.kind === "file" && item.file_diff;

  return (
    <div className="approval-card">
      <div className="modal-head">
        <b>{isFile ? "⚠ 文件修改待审批" : "⚠ 命令待审批"}</b>
      </div>
      {isFile ? (
        <>
          <div className="approval-file"><code>{item.file_diff!.path}</code></div>
          <div className="approval-hunks">
            {item.file_diff!.hunks.map((h) => (
              <div key={h.id} className={`hunk ${checked.has(h.id) ? "on" : ""}`}>
                <label className="hunk-head">
                  <input type="checkbox" checked={checked.has(h.id)}
                    onChange={() => toggle(h.id)} />
                  <span className="hunk-tag">#{h.id} {h.tag}</span>
                  <span className="dim">{checked.has(h.id) ? "应用此块" : "跳过此块"}</span>
                </label>
                <div className="hunk-diff">
                  <pre className="hunk-old">{-h.old}</pre>
                  <pre className="hunk-new">{+h.new}</pre>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <pre className="approval-cmd">{item.command}</pre>
      )}
      {item.risks.length ? (
        <div className="approval-risks">
          {item.risks.map((r, i) => (
            <div key={i} className="risk-item">
              <span className={`sev sev-${r.severity}`}>{r.severity}</span>
              {r.target && <code>{r.target}</code>}
              <span>{r.description}</span>
            </div>
          ))}
        </div>
      ) : <p className="dim">评审原因: {item.reason || "AI 评审未通过/不可用"}</p>}
      <div className="row">
        <button className="primary" onClick={() => void decide(true, [...checked])}>
          {isFile ? `批准应用（${checked.size}/${item.file_diff!.hunks.length} 块）` : "批准执行"}
        </button>
        <button className="danger" onClick={() => void decide(false, [...checked])}>拒绝</button>
      </div>
    </div>
  );
}
