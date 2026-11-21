
import { useEffect, useState } from "react";
import { FloatPanel } from "./FloatPanel";
import { resolveDialog, subscribeDialogs, type DialogItem } from "./dialog";

export function DialogHost() {
  const [items, setItems] = useState<DialogItem[]>([]);
  useEffect(() => subscribeDialogs(setItems), []);

  const cur = items[0];
  if (!cur) return null;
  const title = cur.title || (cur.kind === "alert" ? "提示" : "请确认");

  return (
    <FloatPanel storeKey="dialog" title={title} accent={cur.danger ? "warn" : "info"}>
      <div className="float-msg">{cur.message}</div>
      <div className="float-actions">
        {cur.kind === "confirm" && (
          <button onClick={() => resolveDialog(cur.id, false)}>
            {cur.cancelText || "取消"}
          </button>
        )}
        <button
          className={cur.danger ? "danger" : "primary"}
          onClick={() => resolveDialog(cur.id, true)}
        >
          {cur.okText || "确定"}
        </button>
      </div>
      {items.length > 1 && (
        <div className="float-hint">还有 {items.length - 1} 条待处理</div>
      )}
    </FloatPanel>
  );
}
