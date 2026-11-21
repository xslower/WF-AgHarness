import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { AttnBadges, attnTitle } from "./AttnBadges";
import { EMPTY_ATTN, type Attn } from "../../kernel/attention/attn";

const html = (a: Attn) => renderToStaticMarkup(<AttnBadges attn={a} />);
const attn = (over: Partial<Attn> = {}): Attn => ({ ...EMPTY_ATTN, ...over });

describe("侧栏徽标渲染", () => {
  it("没事时什么都不渲染（不留空 span 撑布局）", () => {
    expect(html(EMPTY_ATTN)).toBe("");
  });

  it("运行中只出一个 accent 色的点", () => {
    const h = html(attn({ running: 1 }));
    expect(h).toContain("sess-badge run");
    expect(h).not.toContain("sess-badge unread");
  });

  it("待审批用反色的「待」，数量大于 1 才带数字", () => {
    expect(html(attn({ approvals: 1 }))).toContain("待</span>");
    const h2 = html(attn({ approvals: 3 }));
    expect(h2).toContain("sess-badge wait");
    expect(h2).toContain("待3");
  });

  it("既有待办又有新结果时，只显示待办（别用两个点糊住用户）", () => {
    const h = html(attn({ approvals: 1, fresh: 1 }));
    expect(h).toContain("sess-badge wait");
    expect(h).not.toContain("sess-badge unread");
  });

  it("单纯有新结果时出 danger 色的点", () => {
    const h = html(attn({ fresh: 2 }));
    expect(h).toContain("sess-badge unread");
    expect(h).not.toContain("sess-badge wait");
  });

  it("排队数量单独显示", () => {
    expect(html(attn({ queued: 4 }))).toContain("sess-badge queue");
  });

  it("tooltip 把「在等什么」说清楚，不是只有个图标", () => {
    const t = attnTitle(attn({ approvals: 2, human: 1, plan: true, running: 1, queued: 1, fresh: 1 }));
    expect(t).toContain("2 个工具审批");
    expect(t).toContain("工作流人工闸门");
    expect(t).toContain("计划已出");
    expect(t).toContain("正在运行");
    expect(t).toContain("排队 1 条");
    expect(t).toContain("有新结果");
  });
});
