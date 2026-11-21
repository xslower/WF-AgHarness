
import {
  MAX_QUEUE, isQueueFull, previewOf, type QueueItem,
} from "./queueOps";
import { Icon } from "../icons";

interface Props {
  items: QueueItem[];
  max?: number;
  onRemove: (id: string) => void;
  
  onEdit: (item: QueueItem) => void;
  onInterject: (id: string) => void;
  onCancelInterject: (id: string) => void;
}

export function QueuePanel({
  items, max = MAX_QUEUE, onRemove, onEdit, onInterject, onCancelInterject,
}: Props) {
  if (!items.length) return null;
  const full = isQueueFull(items, max);
  return (
    <div className="queue-panel">
      <div className="queue-head">
        <span className="queue-title">待发送</span>
        <span className={`queue-count${full ? " full" : ""}`}>{items.length}/{max}</span>
        {full && <span className="queue-tip">已满：先删除或撤回一条，把内容合并后再发</span>}
      </div>
      {items.map((it, i) => (
        <div className={`queue-row${it.interjecting ? " interjecting" : ""}`} key={it.id}>
          <span className="queue-idx">{i + 1}</span>
          <span className="queue-text" title={it.content}>{previewOf(it.content)}</span>
          {(it.images > 0 || it.attachments.length > 0 || it.workflow) && (
            <span className="queue-badges">
              {it.images > 0 && <span className="queue-badge">🖼{it.images}</span>}
              {it.attachments.map((n, j) => <span className="queue-badge" key={`${j}:${n}`}><Icon name="paperclip" />{n}</span>)}
              {it.workflow && <span className="queue-badge">工作流</span>}
            </span>
          )}
          <span className="queue-actions">
            {it.interjecting ? (
              <>
                <span className="queue-pending" title="等本轮工具调用结束时发送，不会截断当前输出">
                  插队中…
                </span>
                <button className="link" onClick={() => onCancelInterject(it.id)}>取消</button>
              </>
            ) : (
              <>
                <button className="link" onClick={() => onInterject(it.id)}
                  title="等本轮工具调用结束时插队发送（不打断当前输出）">插队</button>
                <button className="link" onClick={() => onEdit(it)}
                  title="撤回这条，把内容合并到输入框重新编辑">编辑</button>
                <button className="link danger" onClick={() => onRemove(it.id)}>删除</button>
              </>
            )}
          </span>
        </div>
      ))}
    </div>
  );
}
