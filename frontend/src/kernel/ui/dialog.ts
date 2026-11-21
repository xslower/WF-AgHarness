

export interface DialogOptions {
  
  title?: string;
  
  message: string;
  
  okText?: string;
  
  cancelText?: string;
  
  danger?: boolean;
}

export interface DialogItem extends DialogOptions {
  id: string;
  kind: "confirm" | "alert";
}

type Resolver = (ok: boolean) => void;

let seq = 0;
let items: DialogItem[] = [];
const resolvers = new Map<string, Resolver>();
const listeners = new Set<(list: DialogItem[]) => void>();


const MAX_DIALOGS = 5;

function emit(): void {
  const snapshot = items;
  listeners.forEach((fn) => fn(snapshot));
}


export function subscribeDialogs(fn: (list: DialogItem[]) => void): () => void {
  listeners.add(fn);
  fn(items);
  return () => {
    listeners.delete(fn);
  };
}

function push(item: DialogItem): Promise<boolean> {
  
  
  if (items.some((i) => i.kind === item.kind && i.message === item.message)) {
    return Promise.resolve(false);
  }
  if (items.length >= MAX_DIALOGS) {
    return Promise.resolve(false);   
  }
  items = [...items, item];
  emit();
  return new Promise<boolean>((resolve) => resolvers.set(item.id, resolve));
}


export function resolveDialog(id: string, ok: boolean): void {
  const resolve = resolvers.get(id);
  resolvers.delete(id);
  items = items.filter((i) => i.id !== id);
  emit();
  resolve?.(ok);
}


export function confirmDialog(opts: DialogOptions): Promise<boolean> {
  return push({ ...opts, id: `dlg${++seq}`, kind: "confirm" });
}


export function alertDialog(opts: DialogOptions | string): Promise<void> {
  const o = typeof opts === "string" ? { message: opts } : opts;
  return push({ ...o, id: `dlg${++seq}`, kind: "alert" }).then(() => undefined);
}


export function _resetDialogsForTest(): void {
  items = [];
  resolvers.clear();
  emit();
}
