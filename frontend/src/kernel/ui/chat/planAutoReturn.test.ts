
import { beforeEach, describe, expect, it } from "vitest";
import {
  PLAN_RETURN_AFTER, armPlanAutoReturn, isApproval, noteUserMessage,
  resetPlanAutoReturn, wantsPlan,
} from "./planAutoReturn";
import { installFakeStorage } from "../../../test-utils/fakeStorage";

beforeEach(() => { installFakeStorage(); });

describe("wantsPlan：只在用户明确要计划时才回切", () => {
  it.each([
    "出个方案", "给我一个计划", "来份方案", "重新规划一下",
    "方案", "计划", "切回计划模式", "要不要先给个方案",
    "plan mode", "make a plan", "give me a plan",
  ])("命中：%s", (text) => { expect(wantsPlan(text)).toBe(true); });

  it.each([
    "", "按计划执行", "按计划继续做完", "我要按计划执行",
    "请照上面的方案实施", "计划执行得怎么样", "这个计划不错",
    "把这个函数改一下", "继续", "再改一下",
  ])("不误切：%s", (text) => { expect(wantsPlan(text)).toBe(false); });
});

describe("isApproval：打字拍板（只在计划待确认时由调用方使用）", () => {
  it.each(["确认", "同意", "执行", "开始", "没问题", "可以", "好的", "ok", "yes",
    "go", "行", "干", "搞", "来吧", "按计划执行", "直接开始操作"])(
    "识别为放行：%s", (text) => { expect(isApproval(text)).toBe(true); });

  it.each(["取消", "算了", "不做了", "先别", "第二步改成", "给个方案",
    "今天天气不错", "这个计划不错"])(
    "不误判：%s", (text) => { expect(isApproval(text)).toBe(false); });
});

describe("noteUserMessage：观察期计数与复位", () => {
  it("没 arm 过 → 一直 idle，发多少条都不计数", () => {
    for (let i = 0; i < 8; i++) expect(noteUserMessage("s1", "继续")).toBe("idle");
  });

  it(`arm 后前 ${PLAN_RETURN_AFTER - 1} 条 stay，第 ${PLAN_RETURN_AFTER} 条 reached`, () => {
    armPlanAutoReturn("s1");
    for (let i = 1; i < PLAN_RETURN_AFTER; i++) {
      expect(noteUserMessage("s1", "继续改")).toBe("stay");
    }
    expect(noteUserMessage("s1", "继续改")).toBe("reached");
  });

  it("reached 之后观察期结束，不再自动回切", () => {
    armPlanAutoReturn("s1");
    for (let i = 0; i < PLAN_RETURN_AFTER; i++) noteUserMessage("s1", "继续");
    expect(noteUserMessage("s1", "再一条")).toBe("idle");
  });

  it("观察期内明说要计划 → 本条 keyword 并清观察期（不等满 5 条）", () => {
    armPlanAutoReturn("s1");
    noteUserMessage("s1", "继续");
    noteUserMessage("s1", "继续");
    expect(noteUserMessage("s1", "先给个方案")).toBe("keyword");
    expect(noteUserMessage("s1", "继续")).toBe("idle");
  });

  it("手动拨开关 = 状态刷新：无论到没到 5 条都从零开始", () => {
    armPlanAutoReturn("s1");
    noteUserMessage("s1", "一");
    noteUserMessage("s1", "二");
    noteUserMessage("s1", "三");
    resetPlanAutoReturn("s1");           
    expect(noteUserMessage("s1", "四")).toBe("idle");
    armPlanAutoReturn("s1");             
    for (let i = 1; i < PLAN_RETURN_AFTER; i++) {
      expect(noteUserMessage("s1", "继续")).toBe("stay");
    }
    expect(noteUserMessage("s1", "继续")).toBe("reached");
  });

  it("arm 幂等：重复放开只把计数归零", () => {
    armPlanAutoReturn("s1");
    noteUserMessage("s1", "一");
    noteUserMessage("s1", "二");
    armPlanAutoReturn("s1");
    for (let i = 1; i < PLAN_RETURN_AFTER; i++) {
      expect(noteUserMessage("s1", "继续")).toBe("stay");
    }
    expect(noteUserMessage("s1", "继续")).toBe("reached");
  });
});

describe("按 sid 隔离与降级", () => {
  it("两条会话各数各的，不会串", () => {
    armPlanAutoReturn("a");
    armPlanAutoReturn("b");
    noteUserMessage("a", "一");
    noteUserMessage("a", "二");
    expect(noteUserMessage("b", "一")).toBe("stay");
    expect(localStorage.getItem("chat.a")).toContain('"count":2');
    expect(localStorage.getItem("chat.b")).toContain('"count":1');
  });

  it("sid 为空：arm/note 不抛、不计数", () => {
    armPlanAutoReturn(null);
    expect(noteUserMessage(null, "给个方案")).toBe("idle");
  });

  it("localStorage 坏数据 / 写满都不抛，退化为没有观察期", () => {
    localStorage.setItem("chat.x", "{oops");
    expect(noteUserMessage("x", "给个方案")).toBe("idle");
    installFakeStorage(true);
    expect(() => armPlanAutoReturn("y")).not.toThrow();
    expect(noteUserMessage("y", "给个方案")).toBe("idle");
  });
});
