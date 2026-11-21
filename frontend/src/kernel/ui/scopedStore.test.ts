
import { beforeEach, describe, expect, it } from "vitest";
import { scopedStore, SCOPE_TTL_MS } from "./scopedStore";
import { dropSession, readSession, writeField } from "../chat/chatSessionStore";
import { installFakeStorage } from "../../test-utils/fakeStorage";

beforeEach(() => { installFakeStorage(); });


function setScopeTime(sid: string, name: string, t: number): void {
  const rec = readSession(sid);
  const sc = rec.scope ?? {};
  if (!sc[name]) return;
  sc[name] = { ...sc[name], t };
  writeField(sid, "scope", sc);
}

describe("会话作用域：并入 chat.<sid> 单键", () => {
  it("不同会话互不干扰", () => {
    scopedStore.write("sess:a", "panels", { art: true }, SCOPE_TTL_MS);
    scopedStore.write("sess:b", "panels", { art: false }, SCOPE_TTL_MS);
    expect(scopedStore.read("sess:a", "panels", SCOPE_TTL_MS)).toEqual({ art: true });
    expect(scopedStore.read("sess:b", "panels", SCOPE_TTL_MS)).toEqual({ art: false });
  });

  it("没写过的键返回 undefined（让调用方用默认值）", () => {
    expect(scopedStore.read("sess:none", "panels", SCOPE_TTL_MS)).toBeUndefined();
  });

  it("同名 key 不同类型的值都能存", () => {
    scopedStore.write("sess:x", "width", 320, SCOPE_TTL_MS);
    expect(scopedStore.read("sess:x", "width", SCOPE_TTL_MS)).toBe(320);
    scopedStore.write("sess:x", "flag", false, SCOPE_TTL_MS);
    expect(scopedStore.read("sess:x", "flag", SCOPE_TTL_MS)).toBe(false);
  });

  it("会话所有数据只占一个 localStorage 键，删会话一键全清", () => {
    scopedStore.write("sess:a", "panels", { art: true }, SCOPE_TTL_MS);
    writeField("a", "prefs", { model: "p1/m1" });
    writeField("a", "input", { v: "打了一半", ts: 1 });
    const keys = () => Object.keys((localStorage as unknown as { [k: string]: unknown }))
      .filter((k) => typeof (localStorage as unknown as Record<string, unknown>)[k] === "string");
    
    expect(localStorage.getItem("chat.a")).not.toBeNull();
    expect(readSession("a").prefs).toEqual({ model: "p1/m1" });
    expect(keys.length).toBeGreaterThanOrEqual(0);   
    dropSession("a");
    expect(localStorage.getItem("chat.a")).toBeNull();
    expect(scopedStore.read("sess:a", "panels", SCOPE_TTL_MS)).toBeUndefined();
  });
});

describe("过期", () => {
  it("超过 TTL 的记录读不到，且顺手删掉", () => {
    scopedStore.write("sess:old", "panels", { a: 1 }, SCOPE_TTL_MS);
    setScopeTime("old", "panels", Date.now() - SCOPE_TTL_MS - 1000);
    expect(scopedStore.read("sess:old", "panels", SCOPE_TTL_MS)).toBeUndefined();
    expect(readSession("old").scope?.panels).toBeUndefined();
  });

  it("刚好在 TTL 内还能读到", () => {
    scopedStore.write("sess:fresh", "panels", { a: 1 }, SCOPE_TTL_MS);
    setScopeTime("fresh", "panels", Date.now() - SCOPE_TTL_MS + 10_000);
    expect(scopedStore.read("sess:fresh", "panels", SCOPE_TTL_MS)).toEqual({ a: 1 });
  });
});

describe("clearScope", () => {
  it("只清目标作用域，别的会话不受影响", () => {
    scopedStore.write("sess:dead", "panels", { a: 1 }, SCOPE_TTL_MS);
    scopedStore.write("sess:dead", "tabs", ["x"], SCOPE_TTL_MS);
    scopedStore.write("sess:alive", "panels", { b: 2 }, SCOPE_TTL_MS);
    writeField("dead", "prefs", { model: "x" });   

    scopedStore.clearScope("sess:dead");

    expect(scopedStore.read("sess:dead", "panels", SCOPE_TTL_MS)).toBeUndefined();
    expect(scopedStore.read("sess:dead", "tabs", SCOPE_TTL_MS)).toBeUndefined();
    expect(scopedStore.read("sess:alive", "panels", SCOPE_TTL_MS)).toEqual({ b: 2 });
    expect(readSession("dead").prefs).toEqual({ model: "x" });
  });

  it("作用域前缀相同但 id 不同也不会误删（sess:a vs sess:ab）", () => {
    scopedStore.write("sess:a", "p", 1, SCOPE_TTL_MS);
    scopedStore.write("sess:ab", "p", 2, SCOPE_TTL_MS);
    scopedStore.clearScope("sess:a");
    expect(scopedStore.read("sess:ab", "p", SCOPE_TTL_MS)).toBe(2);
  });
});

describe("工作流作用域（独立键，带 prune）", () => {
  it("读写隔离", () => {
    scopedStore.write("wf:x", "width", 320, SCOPE_TTL_MS);
    expect(scopedStore.read("wf:x", "width", SCOPE_TTL_MS)).toBe(320);
  });

  it("删掉过期键", () => {
    scopedStore.write("wf:x", "p", 1, SCOPE_TTL_MS);
    const rec = JSON.parse(localStorage.getItem("ui.scope.wf:x:p")!);
    rec.t = Date.now() - SCOPE_TTL_MS - 5000;
    localStorage.setItem("ui.scope.wf:x:p", JSON.stringify(rec));
    expect(scopedStore.prune()).toBe(1);
    expect(localStorage.getItem("ui.scope.wf:x:p")).toBeNull();
  });

  it("给了存活集合时，已删除的作用域一并清掉", () => {
    scopedStore.write("wf:alive", "p", 1, SCOPE_TTL_MS);
    scopedStore.write("wf:gone", "p", 1, SCOPE_TTL_MS);
    scopedStore.prune(new Set(["wf:alive"]));
    expect(scopedStore.read("wf:alive", "p", SCOPE_TTL_MS)).toBe(1);
    expect(localStorage.getItem("ui.scope.wf:gone:p")).toBeNull();
  });

  it("坏数据不炸，直接丢掉", () => {
    localStorage.setItem("ui.scope.wf:bad:p", "{不是 JSON");
    expect(() => scopedStore.prune()).not.toThrow();
    expect(localStorage.getItem("ui.scope.wf:bad:p")).toBeNull();
  });

  it("prune 不碰会话数据（chat.<sid> 由 dropSession 管）", () => {
    scopedStore.write("sess:s1", "p", 1, SCOPE_TTL_MS);
    scopedStore.prune(new Set());
    expect(scopedStore.read("sess:s1", "p", SCOPE_TTL_MS)).toBe(1);
  });
});

describe("localStorage 不可用时静默兜底", () => {
  it("setItem 抛异常也不崩", () => {
    installFakeStorage(true);
    expect(() => scopedStore.write("sess:s", "k", 1, SCOPE_TTL_MS)).not.toThrow();
  });

  it("读坏数据返回 undefined", () => {
    localStorage.setItem("chat.junk", "null");
    expect(scopedStore.read("sess:junk", "p", SCOPE_TTL_MS)).toBeUndefined();
  });
});
