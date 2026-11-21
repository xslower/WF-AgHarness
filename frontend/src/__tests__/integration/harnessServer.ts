
import { spawn, type ChildProcess } from "node:child_process";
import { createServer, type Server } from "node:http";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { api } from "../../kernel/api";

const REPO = path.resolve(__dirname, "../../../..");
const PY = path.join(REPO, ".venv/bin/python");

export interface Harness {
  baseUrl: string;
  
  fport: number;
  
  project: string;
  upstream: { path: string; body: Record<string, unknown> }[];
  replyWith: (text: string) => void;
  restart: () => Promise<void>;
  
  bindFetch: () => void;
  close: () => Promise<void>;
}

async function waitHealthy(url: string, timeoutMs = 60_000): Promise<void> {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    try { if ((await fetch(`${url}/api/config`)).ok) return; } catch {  }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`后端 ${timeoutMs}ms 内未就绪`);
}

async function startFakeUpstream(upstream: Harness["upstream"]) {
  let reply = "假模型回复";
  const server: Server = createServer((req, res) => {
    let raw = "";
    req.on("data", (c) => { raw += c; });
    req.on("end", () => {
      let body: Record<string, unknown> = {};
      try { body = JSON.parse(raw || "{}") as Record<string, unknown>; } catch {  }
      upstream.push({ path: String(req.url), body });
      if (String(req.url).endsWith("/models")) {
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ data: [{ id: "mock-lm" }] }));
      }
      res.writeHead(200, { "Content-Type": "text/event-stream" });
      const chunk = (o: unknown) => res.write(`data: ${JSON.stringify(o)}\n\n`);
      const base = { id: "x", object: "chat.completion.chunk", created: 0, model: "mock-lm" };
      chunk({ ...base, choices: [{ index: 0, delta: { role: "assistant", content: reply.slice(0, 3) } }] });
      chunk({ ...base, choices: [{ index: 0, delta: { content: reply.slice(3) } }] });
      chunk({ ...base, choices: [{ index: 0, delta: {}, finish_reason: "stop" }],
              usage: { prompt_tokens: 1, completion_tokens: 2, total_tokens: 3 } });
      res.write("data: [DONE]\n\n");
      res.end();
    });
  });
  await new Promise<void>((r) => server.listen(0, "127.0.0.1", r));
  return { server, port: (server.address() as { port: number }).port,
           setReply: (t: string) => { reply = t; } };
}

export async function startHarness(): Promise<Harness> {
  const upstream: Harness["upstream"] = [];
  const fake = await startFakeUpstream(upstream);
  const dataDir = await mkdtemp(path.join(tmpdir(), "harness-chat-e2e-"));
  let proc: ChildProcess | null = null;
  let baseUrl = "";
  const realFetch = globalThis.fetch;

  const pointFetchTo = (url: string) => {
    globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
      const u = typeof input === "string" ? input : String(input);
      return realFetch(u.startsWith("/") ? `${url}${u}` : u, init);
    }) as typeof fetch;
  };
  const start = async () => {
    const port = 18000 + Math.floor(Math.random() * 2000);
    proc = spawn(PY, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
      "--port", String(port), "--log-level", "error"], {
      cwd: path.join(REPO, "backend"),
      env: { ...process.env, HARNESS_DATA_DIR: dataDir },
      stdio: "ignore",
    });
    baseUrl = `http://127.0.0.1:${port}`;
    await waitHealthy(baseUrl);
    pointFetchTo(baseUrl);
  };
  const stop = () => {
    if (proc && !proc.killed) proc.kill("SIGTERM");
    proc = null;
  };
  await start();
  
  
  const project = path.join(dataDir, "proj");
  await mkdir(path.join(project, ".agent"), { recursive: true });
  await writeFile(path.join(project, ".agent", "marker"), "e2e", "utf8");
  const registered = await api.projectRegister(project);
  return {
    get baseUrl() { return baseUrl; },
    fport: fake.port,
    project: registered.path,
    upstream,
    replyWith: fake.setReply,
    restart: async () => { stop(); await start(); },
    bindFetch: () => pointFetchTo(baseUrl),
    close: async () => {
      stop();
      globalThis.fetch = realFetch;
      await new Promise<void>((r) => fake.server.close(() => r()));
      await rm(dataDir, { recursive: true, force: true });
    },
  };
}


export async function wireFakeModel(fport: number): Promise<string> {
  const p = await api.addProvider({
    name: "e2e-fake",
    baseUrl: `http://127.0.0.1:${fport}/v1`,
    apiKey: "k",
    models: [{ id: "mock-lm", kind: "lm", free: true, contextLength: 4096,
               supportsThinking: false, supportsImages: false,
               inputPrice: 0, outputPrice: 0 }],
  });
  await api.setQueue(["e2e-fake/mock-lm"], []);
  return `${p.name}/mock-lm`;
}
