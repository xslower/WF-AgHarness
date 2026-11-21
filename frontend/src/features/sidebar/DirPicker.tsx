
import { useEffect, useState } from "react";

import { Icon } from "../../kernel/ui/icons";
import { useDirBrowse } from "./useDirBrowse";

export function DirPicker({
  onClose, onConfirm, base,
}: {
  onClose: () => void;
  onConfirm: (path: string) => void;
  
  base?: string;
}) {
  
  
  const b = useDirBrowse();
  const { open } = b;
  
  const [root, setRoot] = useState("");
  useEffect(() => {
    void open(base || "").then((d) => { if (d) setRoot(base ? d.current : ""); });
  }, [open, base]);
  
  
  const rootReady = !base || !!root;
  const canUp = rootReady && !!b.parent && (!root || (b.current !== root && b.parent.startsWith(root)));
  const canConfirm = rootReady && !!b.current && !b.loading && !b.error && (!root || b.current !== root);

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal dir-picker" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <b>{base ? "选择子目录" : "选择目录"}</b>
          <button className="link" onClick={onClose}>关闭</button>
        </div>
        <div className="dir-current">
          <button className="link" disabled={!canUp}
            onClick={() => canUp && void open(b.parent)}>↑ 上级</button>
          <span className="dir-path" title={b.current}>{b.current || "加载中…"}</span>
        </div>
        <div className="dir-list">
          {b.loading && <div className="dim pad8">加载中…</div>}
          {b.error && <div className="dim pad8" style={{ color: "var(--warn, #c96)" }}>浏览失败: {b.error}</div>}
          {!b.loading && !b.error && b.dirs.length === 0 && <div className="dim pad8">没有子目录</div>}
          {b.dirs.map((d) => (
            <div key={d.path} className="dir-item" onClick={() => void open(d.path)}>
              <Icon name="folder" /> {d.name}
            </div>
          ))}
        </div>
        <div className="dir-footer">
          <span className="dim" title={b.current}>
            {base ? `项目子目录: ${b.current || "无"}` : `当前: ${b.current || "无"}`}
          </span>
          {}
          <button className="primary" disabled={!canConfirm}
            onClick={() => onConfirm(b.current)}>{base ? "添加为子项目" : "确定"}</button>
        </div>
      </div>
    </div>
  );
}
