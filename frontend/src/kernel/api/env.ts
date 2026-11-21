

const DEFAULT_BACKEND_PORT = "8001";


export const BACKEND_PORT =
  (import.meta.env.VITE_BACKEND_PORT as string | undefined) || DEFAULT_BACKEND_PORT;


export function resolveBackendPort(): string {
  if (typeof location === "undefined") return BACKEND_PORT;
  const port = location.port;
  if (port) return port;                       
  return location.protocol === "https:" ? "443" : "80";
}


export function backendWsUrl(path: string): string {
  const local = location.hostname === "localhost" || location.hostname === "127.0.0.1";
  const host = local ? "127.0.0.1" : location.hostname;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const port = resolveBackendPort();
  return `${proto}://${host}:${port}${path}`;
}
