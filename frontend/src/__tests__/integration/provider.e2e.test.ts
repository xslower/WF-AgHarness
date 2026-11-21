
import { spawn, type ChildProcess } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { api } from "../../kernel/api";
import type { AppConfig, Provider } from "../../kernel/api/types";
import { cloneConfig, patchMId, patchP } from "../../features/settings/modelEdit";


const REPO = path.resolve(__dirname, "../../../..");
const PY = path.join(REPO, ".venv/bin/python");

let dataDir = "";
let proc: ChildProcess | null = null;
let baseUrl = "";
let realFetch: typeof fetch;

async function waitHealthy(url: string, timeoutMs = 60000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    try {
      if ((await fetch(`${url}/api/config`)).ok) return;
    } catch {
      
    }
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error("后端 60s 内未就绪");
}

async function startBackend(): Promise<string> {
  const port = 18000 + Math.floor(Math.random() * 2000);
  proc = spawn(PY, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
    "--port", String(port)], {
    cwd: path.join(REPO, "backend"),
    env: { ...process.env, HARNESS_DATA_DIR: dataDir },
    stdio: "ignore",
  });
  const url = `http://127.0.0.1:${port}`;
  await waitHealthy(url);
  return url;
}

function stopBackend() {
  if (proc && !proc.killed) {
    proc.kill("SIGTERM");
    proc = null;
  }
}


function pointFetchTo(url: string) {
  globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
    const u = typeof input === "string" ? input : String(input);
    return realFetch(u.startsWith("/") ? `${url}${u}` : u, init);
  }) as typeof fetch;
}

beforeAll(async () => {
  realFetch = globalThis.fetch;
  dataDir = await mkdtemp(path.join(tmpdir(), "harness-e2e-"));
  baseUrl = await startBackend();
  pointFetchTo(baseUrl);
}, 120000);

afterAll(async () => {
  stopBackend();
  globalThis.fetch = realFetch;
  if (dataDir) await rm(dataDir, { recursive: true, force: true });
});


async function restart() {
  stopBackend();
  baseUrl = await startBackend();
  pointFetchTo(baseUrl);
}

const getConfig = () => api.getConfig();
const findP = (cfg: AppConfig, id: string) =>
  cfg.providers.find((p) => p.id === id)!;


function asSaveBody(p: Provider): Omit<Provider, "id"> {
  const body = { ...p };
  delete (body as { id?: string }).id;
  return body;
}

describe("设置 · Provider（用前端真实 client + 真实 patch 函数）", () => {
  it("新建 → 刷新可见 → 重启后端仍在", async () => {
    const created = await api.addProvider({
      name: "我的中转", baseUrl: "https://api.x.com/v1", apiKey: "sk-1", models: [],
    });
    expect(created.id).toBeTruthy();
    expect(findP(await getConfig(), created.id).name).toBe("我的中转");

    await restart();
    expect(findP(await getConfig(), created.id).name).toBe("我的中转");
  }, 120000);

  it("编辑页保存（真实 saveProvider 形状）不会丢掉 kind/adapter", async () => {
    
    const created = await api.addProvider({
      name: "网页", baseUrl: "https://chat.x.com", apiKey: "",
      kind: "custom", adapter: "openai-compatible", models: [],
    } as Partial<Provider>);

    
    
    const draft = await getConfig();
    const p = findP(draft, created.id);
    const body = asSaveBody({ ...p, name: "网页（改名）" });
    await api.updateProvider(created.id, body);

    const after = findP(await getConfig(), created.id);
    expect(after.name).toBe("网页（改名）");
    expect(after.kind).toBe("custom");           
    expect(after.adapter).toBe("openai-compatible");

    await restart();                              
    const p2 = findP(await getConfig(), created.id);
    expect(p2.kind).toBe("custom");
    expect(p2.adapter).toBe("openai-compatible");
  }, 120000);

  it("改名 + 加模型 → 重启后是新值", async () => {
    const created = await api.addProvider({
      name: "旧名", baseUrl: "https://old/v1", apiKey: "k", models: [],
    });
    const cfg = await getConfig();
    const p = findP(cfg, created.id);
    await api.updateProvider(created.id, asSaveBody({
      ...p, name: "新名", baseUrl: "https://new/v1",
      models: [{ id: "m1" }, { id: "m2" }] as Provider["models"],
    }));

    await restart();
    const p2 = findP(await getConfig(), created.id);
    expect(p2.name).toBe("新名");
    expect(p2.models.map((m) => m.id)).toEqual(["m1", "m2"]);
  }, 120000);

  it("模型设置页：筛选后点开关只改中那一个模型（真实 patchMId）", async () => {
    const created = await api.addProvider({
      name: "多模型", baseUrl: "https://m/v1", apiKey: "k",
      models: [{ id: "free-a", free: true }, { id: "paid-b", free: false }],
    } as Partial<Provider>);

    
    
    const cfg = await getConfig();
    let draft = cloneConfig(cfg);
    const pi = draft.providers.findIndex((x) => x.id === created.id);
    const visible = draft.providers[pi].models.filter(
      (m) => !(created.models ?? []).length || m.free);
    expect(visible.map((m) => m.id)).toEqual(["free-a"]);

    
    const setDraft = (fn: (d: AppConfig) => AppConfig) => { draft = fn(draft); };
    patchMId(setDraft as never, pi, visible[0].id, { supportsThinking: true });
    await api.updateProvider(created.id, asSaveBody(draft.providers[pi]));

    const after = findP(await getConfig(), created.id);
    const byId = Object.fromEntries(after.models.map((m) => [m.id, m]));
    expect(byId["free-a"].supportsThinking).toBe(true);
    expect(byId["paid-b"].supportsThinking).toBe(false);   
  }, 120000);

  it("通用设置行内编辑只 PUT 一个字段，不抹未渲染字段", async () => {
    
    await api.putSettings({
      commandDenyPatterns: ["xx"], commandAllowPatterns: ["^git "], wfMaxConcurrency: 8,
    } as unknown as AppConfig["settings"]);
    await api.putSettings({ trashRetentionDays: 30 } as unknown as AppConfig["settings"]);

    const s = (await getConfig()).settings as unknown as Record<string, unknown>;
    expect(s.trashRetentionDays).toBe(30);
    expect(s.commandDenyPatterns).toEqual(["xx"]);   
    expect(s.commandAllowPatterns).toEqual(["^git "]);
    expect(s.wfMaxConcurrency).toBe(8);
  }, 120000);

  it("设置页保存不会抹掉前端未渲染的字段（命令白/黑名单、并发）", async () => {
    const full = {
      policy: "yolo", workspaceRoot: "", defaultEffort: "medium",
      contextWarnRatio: 0.5, envPython: "", envNode: "",
      commandDenyPatterns: ["xx"],
      commandAllowPatterns: ["^git "],
      wfMaxConcurrency: 8,
    } as unknown as AppConfig["settings"];
    await api.putSettings(full);

    
    await api.putSettings({
      policy: "yolo", workspaceRoot: "", defaultEffort: "medium",
      contextWarnRatio: 0.5, envPython: "", envNode: "",
    } as unknown as AppConfig["settings"]);

    const s = (await getConfig()).settings as unknown as Record<string, unknown>;
    expect(s.commandDenyPatterns).toEqual(["xx"]);   
    expect(s.commandAllowPatterns).toEqual(["^git "]);
    expect(s.wfMaxConcurrency).toBe(8);
  }, 120000);

  it("删模型 → 队列里指向它的项一起清掉 → 重启不复现", async () => {
    const created = await api.addProvider({
      name: "q", baseUrl: "https://q/v1", apiKey: "k",
      models: [{ id: "a" }, { id: "b" }],
    });
    
    await api.setQueue([`${created.name}/a`], []);
    await api.removeModel(created.id, "a");

    let cfg = await getConfig();
    expect(findP(cfg, created.id).models.map((m) => m.id)).toEqual(["b"]);
    expect(cfg.queues.parent).not.toContain(`${created.name}/a`);

    await restart();
    cfg = await getConfig();
    expect(findP(cfg, created.id).models.map((m) => m.id)).toEqual(["b"]);
  }, 120000);

  it("删除 Provider → 刷新与重启都不再出现", async () => {
    const created = await api.addProvider({
      name: "要删", baseUrl: "https://d/v1", apiKey: "k", models: [],
    });
    await api.deleteProvider(created.id);
    expect((await getConfig()).providers.some((x) => x.id === created.id)).toBe(false);

    await restart();
    expect((await getConfig()).providers.some((x) => x.id === created.id)).toBe(false);
  }, 120000);

  it("老客户端只发 name/baseUrl（不带 models）→ 模型不能被清空", async () => {
    
    const created = await api.addProvider({
      name: "p", baseUrl: "https://a/v1", apiKey: "k",
      models: [{ id: "m1" }, { id: "m2" }],
    } as Partial<Provider>);
    await api.updateProvider(created.id, {
      name: "改名", baseUrl: "https://a/v1", apiKey: "k",
    } as unknown as Omit<Provider, "id">);

    const p = findP(await getConfig(), created.id);
    expect(p.name).toBe("改名");
    expect(p.models.map((m) => m.id)).toEqual(["m1", "m2"]);   
  }, 120000);

  it("模型设置页只改了筛选后的一个模型 → 其它模型不会被删", async () => {
    const created = await api.addProvider({
      name: "partial", baseUrl: "https://pm/v1", apiKey: "k",
      models: [{ id: "keep-1" }, { id: "keep-2" }, { id: "seen" }],
    } as Partial<Provider>);

    const cfg = await getConfig();
    let draft = cloneConfig(cfg);
    const pi = draft.providers.findIndex((x) => x.id === created.id);
    const setDraft = (fn: (d: AppConfig) => AppConfig) => { draft = fn(draft); };
    
    patchMId(setDraft as never, pi, "seen", { supportsThinking: true });
    const onlySeen = draft.providers[pi].models.filter(
      (m) => m.id === "seen" && m.supportsThinking);
    expect(onlySeen).toHaveLength(1);   
    await api.updateProvider(created.id, asSaveBody({
      ...draft.providers[pi], models: onlySeen,
    }));

    const p = findP(await getConfig(), created.id);
    expect(p.models.map((m) => m.id).sort()).toEqual(["keep-1", "keep-2", "seen"]);
    expect(p.models.find((m) => m.id === "seen")!.supportsThinking).toBe(true);
  }, 120000);

  it("对生图/语音模型点「🧪」→ 立刻返回不适用（不卡 30 秒超时）", async () => {
    const created = await api.addProvider({
      name: "multi", baseUrl: "https://mm/v1", apiKey: "k",
      models: [{ id: "dall-e-3", kind: "image" }],
    } as Partial<Provider>);
    const t0 = Date.now();
    const r = await api.testModel(`${created.name}/dall-e-3`);
    expect(Date.now() - t0).toBeLessThan(5000);          
    expect(r.ok).toBeNull();
    expect(r.skipped).toBe(true);
    expect(r.error).toContain("不支持对话测试");
  }, 120000);
});
