


async function errorText(r: Response): Promise<string> {
  const raw = await r.text().catch(() => "");
  try {
    const j = JSON.parse(raw) as Record<string, unknown>;
    const d = j.detail ?? j.error ?? j.message;
    if (typeof d === "string" && d.trim()) return d;
    if (d) return JSON.stringify(d);
  } catch {
    
  }
  const t = raw.trim();
  if (!t) return `请求失败（HTTP ${r.status}）`;
  if (t.startsWith("<")) return `请求失败（HTTP ${r.status}），服务端未返回原因`;
  return t.length > 300 ? `${t.slice(0, 300)}…` : t;
}


export async function parseJson<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(await errorText(r));
  return r.json() as Promise<T>;
}


export async function parseJsonLoose<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(await errorText(r));
  return r.json() as Promise<T>;
}

export const getJson = <T>(url: string): Promise<T> => fetch(url).then(parseJson<T>);

export const sendJson = <T>(
  url: string,
  method: "POST" | "PUT",
  body?: unknown,
): Promise<T> =>
  fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then(parseJson<T>);

export const delJson = <T>(url: string): Promise<T> =>
  fetch(url, { method: "DELETE" }).then(parseJson<T>);


export const patchJson = <T>(url: string, body?: unknown): Promise<T> =>
  fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then(parseJson<T>);


export const buildQuery = (params: Record<string, string | number | undefined>): string => {
  const q = Object.entries(params)
    .filter(([, v]) => v !== undefined)
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join("&");
  return q ? `?${q}` : "";
};
