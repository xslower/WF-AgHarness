


import { MAX_QUEUE, type QueueItem } from "../../chat/chatTypes";
export { MAX_QUEUE, type QueueItem };

export function isQueueFull(items: QueueItem[], max: number = MAX_QUEUE): boolean {
  return items.length >= max;
}


export function mergeForEdit(itemContent: string, input: string): string {
  const head = String(itemContent || "").trim();
  const tail = String(input || "").trim();
  if (!tail) return head;
  if (!head) return tail;
  return `${head}\n${tail}`;
}


export function markInterjecting(items: QueueItem[], id: string): QueueItem[] {
  const it = items.find((x) => x.id === id);
  if (!it || it.interjecting) return items;
  return [{ ...it, interjecting: true }, ...items.filter((x) => x.id !== id)];
}

export function cancelInterject(items: QueueItem[], id: string): QueueItem[] {
  return items.map((x) => (x.id === id ? { ...x, interjecting: false } : x));
}

export function removeItem(items: QueueItem[], id: string): QueueItem[] {
  return items.filter((x) => x.id !== id);
}


export function previewOf(text: string, max = 80): string {
  const s = String(text || "").replace(/\s+/g, " ").trim();
  if (!s) return "（空消息）";
  return s.length > max ? `${s.slice(0, max)}…` : s;
}


export function queueLabel(items: QueueItem[], max: number = MAX_QUEUE): string {
  return `${items.length}/${max}${isQueueFull(items, max) ? "（已满）" : ""}`;
}


export function lostOnEdit(item: QueueItem): string {
  const parts: string[] = [];
  if (item.images > 0) parts.push(`${item.images} 张图片`);
  if (item.attachments.length) parts.push(`${item.attachments.length} 个附件`);
  return parts.join("、");
}
