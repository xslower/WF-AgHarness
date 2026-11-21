

const PREFIX = "skill__";


export function skillLabel(name: string): string {
  const n = String(name || "");
  return n.startsWith(PREFIX) ? n.slice(PREFIX.length) : n;
}
