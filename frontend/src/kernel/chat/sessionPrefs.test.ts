
import { beforeEach, describe, expect, it } from "vitest";
import {
  NEW_SESSION_KEY, dropPrefs, patchPrefs, readPrefs, specStillValid, writePrefs,
} from "./sessionPrefs";
import { normalizeSpec } from "../model/modelSpec";
import { installFakeStorage } from "../../test-utils/fakeStorage";


const CFG = {
  providers: [
    { name: "p1", models: [{ id: "m1" }, { id: "m2", disabled: true }] },
    { name: "p2", models: [{ id: "m3" }] },
  ],
  queues: { parent: ["p1/m1"], child: ["p2/m3"], summary: [] },
};

beforeEach(() => { installFakeStorage(); });

describe("会话 prefs 本地存储", () => {
  it("按会话隔离：不同 sid 互不影响（不会串上一条会话的模型）", () => {
    writePrefs("a", { model: "p1/m1" });
    writePrefs("b", { model: "p2/m3" });
    expect(readPrefs("a").model).toBe("p1/m1");
    expect(readPrefs("b").model).toBe("p2/m3");
    expect(readPrefs("c")).toEqual({});          
  });

  it("patchPrefs 只改指定字段，其余保留", () => {
    writePrefs("a", { model: "p1/m1", plan: "1" });
    const next = patchPrefs("a", { model: "" });
    expect(next.model).toBe("");
    expect(next.plan).toBe("1");
  });

  it("dropPrefs 清掉该会话（新建会话时用）", () => {
    writePrefs("a", { model: "p1/m1" });
    dropPrefs("a");
    expect(readPrefs("a")).toEqual({});
  });

  it("坏数据/空 sid 不抛异常，退化为空", () => {
    localStorage.setItem("chat.x", "{oops");
    expect(readPrefs("x")).toEqual({});
  });

  it("新任务（sid=null）的选择暂存在独立槽位，建会话时再取", () => {
    
    writePrefs(null, { model: "p1/m1", workflow: "wf1" });
    expect(readPrefs(null).model).toBe("p1/m1");
    
    expect(readPrefs("real-sid")).toEqual({});
    
    expect(readPrefs(NEW_SESSION_KEY).workflow).toBe("wf1");
  });
});

describe("spec 本地失效校验（不发请求）", () => {
  it("空 spec（父队列）永远有效", () => {
    expect(specStillValid("", CFG)).toBe(true);
  });

  it("配置还没到时按有效处理（避免首帧闪成父队列）", () => {
    expect(specStillValid("p1/m1", null)).toBe(true);
  });

  it("provider+模型都在且未禁用 → 有效", () => {
    expect(specStillValid("p1/m1", CFG)).toBe(true);
  });

  it("模型被禁用 → 无效（回落父队列）", () => {
    expect(specStillValid("p1/m2", CFG)).toBe(false);
  });

  it("provider 或模型被删 → 无效", () => {
    expect(specStillValid("p9/m1", CFG)).toBe(false);
    expect(specStillValid("p1/deleted", CFG)).toBe(false);
  });

  it("队列名：队列非空才有效；parent 永远有效", () => {
    expect(specStillValid("child", CFG)).toBe(true);
    expect(specStillValid("summary", CFG)).toBe(true);   
    expect(specStillValid("child", { ...CFG, queues: { ...CFG.queues, child: [] } }))
      .toBe(false);
    expect(specStillValid("parent", { ...CFG, queues: { parent: [] } })).toBe(true);
  });

  it("空串/undefined 按父队列处理（2026-11-06 起没有「自动」这个值）", () => {
    expect(specStillValid("", CFG)).toBe(true);
    expect(normalizeSpec("")).toBe("parent");
    expect(normalizeSpec(undefined)).toBe("parent");
    expect(normalizeSpec(" child ")).toBe("child");
  });
});
