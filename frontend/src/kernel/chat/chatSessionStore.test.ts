
import { beforeEach, describe, expect, it } from "vitest";
import {
  dropSession, initSession, keyOf, listSessionIds, migrateLegacyKeys,
  readField, readSession, resetNewSessionSlot, writeField,
} from "./chatSessionStore";
import { installFakeStorage } from "../../test-utils/fakeStorage";

beforeEach(() => { installFakeStorage(); });

describe("单键形状", () => {
  it("所有分区都在 chat.<sid> 一个键里", () => {
    writeField("a", "prefs", { model: "p1/m1" });
    writeField("a", "input", { v: "打了一半", ts: 1 });
    writeField("a", "scroll", 320);
    const raw = localStorage.getItem("chat.a")!;
    expect(JSON.parse(raw)).toMatchObject({
      prefs: { model: "p1/m1" }, input: { v: "打了一半" }, scroll: 320,
    });
  });

  it("default 由调用方给，没记录时不会串到别的会话", () => {
    writeField("a", "prefs", { model: "p1/m1" });
    expect(readField("a", "prefs", {})).toEqual({ model: "p1/m1" });
    expect(readField("b", "prefs", {})).toEqual({});
    expect(readField("b", "scroll", 0)).toBe(0);
  });

  it("sid 为 null 走 __new__ 槽位", () => {
    writeField(null, "prefs", { model: "child" });
    expect(keyOf(null)).toBe("chat.__new__");
    expect(readField(null, "prefs", {})).toEqual({ model: "child" });
  });

  it("坏数据当没存过，不抛", () => {
    localStorage.setItem("chat.x", "{oops");
    expect(readSession("x")).toEqual({});
    expect(readField("x", "prefs", {})).toEqual({});
  });
});

describe("initSession / dropSession", () => {
  it("initSession 建一条空记录，且不覆盖已有数据", () => {
    initSession("new");
    expect(localStorage.getItem("chat.new")).toBe("{}");
    writeField("new", "prefs", { model: "child" });
    initSession("new");
    expect(readField("new", "prefs", {})).toEqual({ model: "child" });
  });

  it("dropSession 一个 removeItem 清掉全部分区", () => {
    writeField("a", "prefs", { model: "x" });
    writeField("a", "partial", { text: "p", reason: "", ts: 1 });
    writeField("a", "input", { v: "i", ts: 1, sent: true });
    writeField("a", "scroll", 100);
    writeField("a", "planAuto", { armed: true, count: 2 });
    writeField("a", "scope", { p: { v: 1, t: 1 } });
    writeField("a", "seen", 999);
    dropSession("a");
    expect(localStorage.getItem("chat.a")).toBeNull();
    expect(readSession("a")).toEqual({});
  });

  it("dropSession 不影响别的会话", () => {
    writeField("a", "prefs", { model: "a" });
    writeField("b", "prefs", { model: "b" });
    dropSession("a");
    expect(readField("b", "prefs", {})).toEqual({ model: "b" });
  });
});

describe("切会话模型不串（用户 2026-11-08 报的 bug）", () => {
  it("新会话用默认值 → 切到选过模型的老会话读到老值 → 切回新会话仍是默认值", () => {
    
    initSession("new");
    const defaultModel = readField("new", "prefs", {}).model ?? "parent";
    expect(defaultModel).toBe("parent");

    
    writeField("old", "prefs", { model: "p1/m1" });
    expect(readField("old", "prefs", {}).model).toBe("p1/m1");

    
    expect(readField("new", "prefs", {}).model ?? "parent").toBe("parent");
  });

  it("按 sid 写入不会跨会话（每条 chat.<sid> 独立）", () => {
    writeField("a", "prefs", { model: "child" });
    writeField("b", "prefs", { model: "summary" });
    expect(readField("a", "prefs", {}).model).toBe("child");
    expect(readField("b", "prefs", {}).model).toBe("summary");
  });

  it("删掉旧会话只影响它自己，其它会话的数据原样保留", () => {
    writeField("a", "prefs", { model: "child" });
    writeField("a", "input", { v: "A 的草稿", ts: 1, sent: true });
    writeField("b", "prefs", { model: "summary" });
    writeField("b", "input", { v: "B 的输入", ts: 1 });
    dropSession("a");
    expect(readSession("a")).toEqual({});
    expect(readField("b", "prefs", {}).model).toBe("summary");
    expect(readSession("b").input).toEqual({ v: "B 的输入", ts: 1 });
  });
});

describe("新任务槽位复位", () => {
  it("清掉选择/输入草稿，保留 lastSid（非会话内容）", () => {
    writeField(null, "prefs", { model: "child" });
    writeField(null, "input", { v: "打了一半", ts: 1 });
    writeField(null, "lastSid", "wf-1");
    resetNewSessionSlot();
    const rec = readSession(null);
    expect(rec.prefs).toBeUndefined();
    expect(rec.input).toBeUndefined();
    expect(rec.lastSid).toBe("wf-1");
  });

  it("没有 lastSid 时整个键都不留", () => {
    writeField(null, "prefs", { model: "child" });
    resetNewSessionSlot();
    expect(localStorage.getItem("chat.__new__")).toBeNull();
  });
});

describe("listSessionIds", () => {
  it("只列真实会话，排除 __new__ 与旧 chat.draft.* 键", () => {
    writeField("a", "prefs", {});
    writeField(null, "prefs", {});
    localStorage.setItem("chat.draft.old", "{}");
    localStorage.setItem("chat.partial.old", "{}");
    expect(listSessionIds()).toEqual(["a"]);
  });
});

describe("旧键迁移", () => {
  it("散键搬进 chat.<sid>；旧发送草稿并入一份、只删不搬", () => {
    localStorage.setItem("ui.prefs.s1", '{"model":"p1/m1"}');
    localStorage.setItem("chat.draft.s1", '{"content":"d"}');
    localStorage.setItem("chat.partial.s1", '{"text":"p","reason":"","ts":1}');
    localStorage.setItem("ui.planAuto.s1", '{"armed":true,"count":2}');
    localStorage.setItem("ui.scroll.s1", "320");
    localStorage.setItem("ui.scope.sess:s1:panels", '{"v":{"art":true},"t":1}');
    localStorage.setItem("ui.inputs", JSON.stringify({ s1: { v: "i", ts: 2 } }));
    localStorage.setItem("ui.seen", JSON.stringify({ s1: 999 }));
    localStorage.setItem("ui.modelSel", "child");   

    migrateLegacyKeys();

    const rec = readSession("s1");
    expect(rec.prefs).toEqual({ model: "p1/m1" });
    
    expect(rec.partial).toEqual({ text: "p", reason: "", ts: 1 });
    expect(rec.planAuto).toEqual({ armed: true, count: 2 });
    expect(rec.scroll).toBe(320);
    expect(rec.scope?.panels?.v).toEqual({ art: true });
    expect(rec.input).toEqual({ v: "i", ts: 2 });   
    expect(rec.seen).toBe(999);
    for (const k of ["ui.prefs.s1", "chat.draft.s1", "chat.partial.s1", "ui.planAuto.s1",
                     "ui.scroll.s1", "ui.scope.sess:s1:panels", "ui.inputs", "ui.seen"]) {
      expect(localStorage.getItem(k)).toBeNull();
    }
  });

  it("幂等：第二次跑不覆盖新数据、不重复计数", () => {
    localStorage.setItem("ui.prefs.s1", '{"model":"old"}');
    migrateLegacyKeys();
    writeField("s1", "prefs", { model: "new" });
    migrateLegacyKeys();
    expect(readField("s1", "prefs", {})).toEqual({ model: "new" });
  });

  it("坏 JSON 不炸，旧键照样清掉", () => {
    localStorage.setItem("ui.prefs.bad", "{oops");
    expect(() => migrateLegacyKeys()).not.toThrow();
    expect(localStorage.getItem("ui.prefs.bad")).toBeNull();
  });

  it("新记录已有该字段时不覆盖", () => {
    writeField("s1", "prefs", { model: "new" });
    localStorage.setItem("ui.prefs.s1", '{"model":"old"}');
    migrateLegacyKeys();
    expect(readField("s1", "prefs", {})).toEqual({ model: "new" });
  });
});
