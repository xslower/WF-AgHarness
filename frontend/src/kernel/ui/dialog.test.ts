
import { beforeEach, describe, expect, it } from "vitest";

import {
  _resetDialogsForTest, alertDialog, confirmDialog,
  resolveDialog, subscribeDialogs,
} from "./dialog";
import type { DialogItem } from "./dialog";

function snapshot(): DialogItem[] {
  let got: DialogItem[] = [];
  const off = subscribeDialogs((list) => { got = list; });
  off();
  return got;
}

beforeEach(() => _resetDialogsForTest());

describe("dialog 队列防堆积", () => {
  it("相同 message 的 alert 只入队一次", async () => {
    void alertDialog("浏览失败: 超时");
    void alertDialog("浏览失败: 超时");
    void alertDialog("浏览失败: 超时");
    expect(snapshot()).toHaveLength(1);
  });

  it("不同 message 可以各自入队，但不超过上限 5", () => {
    for (let i = 0; i < 20; i++) void alertDialog(`错误 #${i}`);
    expect(snapshot()).toHaveLength(5);
  });

  it("被去重/超限丢弃的 confirm 立即结算为 false，不挂起调用方", async () => {
    void confirmDialog({ message: "删除？" });
    const dup = await confirmDialog({ message: "删除？" });
    expect(dup).toBe(false);
    
    const ok = confirmDialog({ message: "另一件事" });
    const mine = snapshot().find((d) => d.message === "另一件事")!;
    resolveDialog(mine.id, true);
    expect(await ok).toBe(true);
  });

  it("队列结算后能继续接收新的相同 message", () => {
    void alertDialog("同样的话");
    resolveDialog(snapshot()[0].id, true);
    void alertDialog("同样的话");
    expect(snapshot()).toHaveLength(1);
  });
});
