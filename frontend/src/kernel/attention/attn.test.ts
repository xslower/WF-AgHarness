import { beforeEach, describe, expect, it } from "vitest";
import type { PendingHumanItem, SessionAttentionRow } from "../api";
import {
  EMPTY_ATTN, flowAttn, hasAny, mergeAttn, sessionAttn, waitingCount,
} from "./attn";
import { isFresh, markSeen, readSeen } from "./seen";
import { installFakeStorage } from "../../test-utils/fakeStorage";


const row = (over: Partial<SessionAttentionRow> = {}): SessionAttentionRow => ({
  id: "s1", title: "任务", project: "/p", kind: "", origin: "",
  message_count: 3, running: false, queued: 0, approvals: 0, plan: false,
  updated_at: 100, ...over,
});

const human = (over: Partial<PendingHumanItem> = {}): PendingHumanItem => ({
  project: "/p", workflow: "wf1", run: "r1", node: "n1", title: "确认",
  ask: "", options: ["批准", "驳回"], created: 1, scope: "workflow", ...over,
});

beforeEach(() => { installFakeStorage(); });

describe("已读位点", () => {
  it("updated_at 比已读位点新 = 有新结果", () => {
    const seen = { s1: 100 };
    expect(isFresh(row({ updated_at: 200 }), seen)).toBe(true);
    expect(isFresh(row({ updated_at: 100 }), seen)).toBe(false);
    expect(isFresh(row({ updated_at: 50 }), seen)).toBe(false);
  });

  it("正在跑的、当前打开的、空会话都不算「有新结果」", () => {
    const seen = { s1: 0 };
    expect(isFresh(row({ running: true, updated_at: 200 }), seen)).toBe(false);
    expect(isFresh(row({ updated_at: 200 }), seen, "s1")).toBe(false);
    expect(isFresh(row({ message_count: 0, updated_at: 200 }), seen)).toBe(false);
  });

  it("位点只增不减（来回切会话不会把已读退回旧版本）", () => {
    markSeen("s1", 500);
    markSeen("s1", 300);
    expect(readSeen().s1).toBe(500);
  });

  it("坏数据读回空表，不抛", () => {
    localStorage.setItem("chat.s1", "{oops");
    expect(readSeen()).toEqual({});
  });
});

describe("会话徽标", () => {
  it("没数据时是空徽标", () => {
    expect(sessionAttn(undefined, {})).toBe(EMPTY_ATTN);
    expect(hasAny(EMPTY_ATTN)).toBe(false);
  });

  it("把后端的四个字段如实映射过来", () => {
    const a = sessionAttn(row({ running: true, queued: 2, approvals: 1, plan: true }), {});
    expect(a.running).toBe(1);
    expect(a.queued).toBe(2);
    expect(a.approvals).toBe(1);
    expect(a.plan).toBe(true);
  });

  it("等你动手的口径：审批 + 计划确认 + 人工闸门（运行/排队/未读不算）", () => {
    expect(waitingCount({ ...EMPTY_ATTN, approvals: 2 })).toBe(2);
    expect(waitingCount({ ...EMPTY_ATTN, plan: true })).toBe(1);
    expect(waitingCount({ ...EMPTY_ATTN, human: 1 })).toBe(1);
    expect(waitingCount({ ...EMPTY_ATTN, running: 3, fresh: 5 })).toBe(0);
  });
});

describe("工作流徽标", () => {
  it("聚合该工作流下所有助手会话（不只最后一条）", () => {
    const rows = [
      row({ id: "a", kind: "workflow", origin: "wf1", approvals: 1 }),
      row({ id: "b", kind: "workflow", origin: "wf1", running: true }),
      row({ id: "c", kind: "workflow", origin: "wf2", approvals: 5 }),   
      row({ id: "d", kind: "", origin: "", approvals: 9 }),              
    ];
    const a = flowAttn(rows, [], "/p", "wf1", {});
    expect(a.approvals).toBe(1);
    expect(a.running).toBe(1);
  });

  it("项目要对得上：同名工作流分属不同项目时不串", () => {
    const rows = [row({ id: "a", kind: "workflow", origin: "wf1", project: "/other", approvals: 3 })];
    expect(flowAttn(rows, [], "/p", "wf1", {}).approvals).toBe(0);
    expect(flowAttn(rows, [], "/other", "wf1", {}).approvals).toBe(3);
  });

  it("挂起的人工闸门算「等你拍板」，不属于本工作流的不算", () => {
    const rows: SessionAttentionRow[] = [];
    expect(flowAttn(rows, [human()], "/p", "wf1", {}).human).toBe(1);
    expect(flowAttn(rows, [human({ scope: "global" })], "/p", "wf1", {}).human).toBe(1);
    expect(flowAttn(rows, [human({ workflow: "wf2" })], "/p", "wf1", {}).human).toBe(0);
    expect(flowAttn(rows, [human({ project: "/x" })], "/p", "wf1", {}).human).toBe(0);
  });

  it("mergeAttn 求和、plan 取或", () => {
    const a = mergeAttn([
      { ...EMPTY_ATTN, running: 1, approvals: 2 },
      { ...EMPTY_ATTN, running: 2, plan: true, fresh: 1 },
    ]);
    expect(a.running).toBe(3);
    expect(a.approvals).toBe(2);
    expect(a.plan).toBe(true);
    expect(a.fresh).toBe(1);
  });
});
