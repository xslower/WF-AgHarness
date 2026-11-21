


export function normSlashes(p: unknown): string {
  return String(p ?? "").replace(/\\/g, "/").replace(/\/+$/, "");
}


export function normPath(p: unknown): string {
  return normSlashes(p).toLowerCase();
}


export function isProjectEvent(payload: Record<string, any> | undefined | null,
                               project: string): boolean {
  if (!project) return false;
  const mine = normPath(project);
  if (!mine) return false;
  const p = payload ?? {};
  return normPath(p.project) === mine;
}

export interface Coalescer {
  
  fire: () => void;
  
  cancel: () => void;
}


export function createCoalescer(delay: number, run: () => void): Coalescer {
  let timer: ReturnType<typeof setTimeout> | undefined;
  return {
    fire() {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        timer = undefined;
        run();
      }, delay);
    },
    cancel() {
      if (timer) clearTimeout(timer);
      timer = undefined;
    },
  };
}
