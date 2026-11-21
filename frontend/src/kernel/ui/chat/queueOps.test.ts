
import { describe, expect, it } from "vitest";
import {
  MAX_QUEUE, cancelInterject, isQueueFull, lostOnEdit, markInterjecting,
  mergeForEdit, previewOf, queueLabel, removeItem, type QueueItem,
} from "./queueOps";

const item = (id: string, over: Partial<QueueItem> = {}): QueueItem => ({
  id, content: `内容${id}`, images: 0, attachments: [],
  workflow: "", interjecting: false, ...over,
});

describe("isQueueFull / queueLabel", () => {
  it("上限 3 条", () => {
    expect(MAX_QUEUE).toBe(3);
    expect(isQueueFull([])).toBe(false);
    expect(isQueueFull([item("1"), item("2")])).toBe(false);
    expect(isQueueFull([item("1"), item("2"), item("3")])).toBe(true);
    expect(isQueueFull([item("1")], 1)).toBe(true);
  });

  it("角标文案带已满标记", () => {
    expect(queueLabel([])).toBe("0/3");
    expect(queueLabel([item("1"), item("2")])).toBe("2/3");
    expect(queueLabel([item("1"), item("2"), item("3")])).toBe("3/3（已满）");
  });
});

describe("mergeForEdit", () => {
  it("该条内容在前，输入框内容在后", () => {
    expect(mergeForEdit("队列里的", "输入框里的")).toBe("队列里的\n输入框里的");
  });

  it("输入框为空时纯回填", () => {
    expect(mergeForEdit("队列里的", "")).toBe("队列里的");
    expect(mergeForEdit("队列里的", "   \n ")).toBe("队列里的");
  });

  it("该条为空时保留输入框内容", () => {
    expect(mergeForEdit("", "输入框")).toBe("输入框");
  });

  it("两侧都空返回空串", () => {
    expect(mergeForEdit("", "")).toBe("");
  });

  it("保留多行与首尾空白被裁掉", () => {
    expect(mergeForEdit("  a\nb  ", " c ")).toBe("a\nb\nc");
  });
});

describe("markInterjecting", () => {
  it("移到队首并打标记", () => {
    const q = [item("1"), item("2"), item("3")];
    const out = markInterjecting(q, "3");
    expect(out.map((x) => x.id)).toEqual(["3", "1", "2"]);
    expect(out[0].interjecting).toBe(true);
    expect(out[1].interjecting).toBe(false);
  });

  it("已经是插队中则不重复处理（保持原引用）", () => {
    const q = [item("1", { interjecting: true }), item("2")];
    expect(markInterjecting(q, "1")).toBe(q);
  });

  it("id 不存在时原样返回", () => {
    const q = [item("1")];
    expect(markInterjecting(q, "zz")).toBe(q);
  });

  it("不改动原数组", () => {
    const q = [item("1"), item("2")];
    markInterjecting(q, "2");
    expect(q.map((x) => x.id)).toEqual(["1", "2"]);
  });
});

describe("cancelInterject", () => {
  it("只清标记，位置不变", () => {
    const q = [item("1", { interjecting: true }), item("2")];
    const out = cancelInterject(q, "1");
    expect(out[0].interjecting).toBe(false);
    expect(out.map((x) => x.id)).toEqual(["1", "2"]);
  });

  it("id 不存在时无变化", () => {
    const q = [item("1")];
    expect(cancelInterject(q, "zz")).toEqual(q);
  });
});

describe("removeItem", () => {
  it("删除指定条目", () => {
    expect(removeItem([item("1"), item("2")], "1").map((x) => x.id)).toEqual(["2"]);
  });

  it("不存在时不变", () => {
    expect(removeItem([item("1")], "zz")).toHaveLength(1);
  });
});

describe("previewOf", () => {
  it("压平换行与多余空白", () => {
    expect(previewOf("第一行\n\n第二行   第三行")).toBe("第一行 第二行 第三行");
  });

  it("超长截断并加省略号", () => {
    const out = previewOf("啊".repeat(100), 10);
    expect(out).toBe(`${"啊".repeat(10)}…`);
  });

  it("空内容给占位文案", () => {
    expect(previewOf("")).toBe("（空消息）");
    expect(previewOf("   \n ")).toBe("（空消息）");
  });

  it("正好等于上限时不截断", () => {
    expect(previewOf("a".repeat(10), 10)).toBe("a".repeat(10));
  });
});

describe("lostOnEdit", () => {
  it("列出撤回后会丢的图片与附件", () => {
    expect(lostOnEdit(item("1"))).toBe("");
    expect(lostOnEdit(item("1", { images: 2 }))).toBe("2 张图片");
    expect(lostOnEdit(item("1", { attachments: ["a.md", "b.txt"] }))).toBe("2 个附件");
    expect(lostOnEdit(item("1", { images: 1, attachments: ["a.md"] })))
      .toBe("1 张图片、1 个附件");
  });
});
