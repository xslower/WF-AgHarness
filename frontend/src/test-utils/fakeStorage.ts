
export function installFakeStorage(fail = false): Map<string, string> {
  const map = new Map<string, string>();
  (globalThis as any).localStorage = {
    get length() { return map.size; },
    key: (i: number) => [...map.keys()][i] ?? null,
    getItem: (k: string) => (map.has(k) ? map.get(k)! : null),
    setItem: (k: string, v: string) => {
      if (fail) throw new Error("QuotaExceededError");
      map.set(k, v);
    },
    removeItem: (k: string) => { map.delete(k); },
    clear: () => { map.clear(); },
  };
  return map;
}
