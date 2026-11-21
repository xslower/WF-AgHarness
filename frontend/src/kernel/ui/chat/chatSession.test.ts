import { describe, expect, it } from "vitest";
import {
  isEmptyTurn, makePayload, makeQid, makeUserMessage, type TurnInput,
} from "./chatPayload";
import { isPartialStale, liveFromPartial, mergeStream, PARTIAL_TTL_MS,
  shouldRestorePartial, visibleMessages } from "./chatSession";
import type { ChatMessage } from "../../api";

const turn = (over: Partial<TurnInput> = {}): TurnInput => ({
  body: "你好", images: [], audio: "", attachments: [], ...over,
});

describe("请求体", () => {
  it("plan/workflow 只在显式给了才出现（后端按存在性判断语义）", () => {
    const plain = makePayload(turn(), "q1");
    expect("plan" in plain).toBe(false);
    expect("workflow" in plain).toBe(false);

    const full = makePayload(turn({ plan: true, workflow: "wf1" }), "q1");
    expect(full.plan).toBe(true);
    expect(full.workflow).toBe("wf1");
  });

  it("model 每次必带：后端以 payload 为准（不保存会话级模型）", () => {
    
    
    expect(makePayload(turn(), "q1").model).toBe("parent");       
    expect(makePayload(turn({ model: "child" }), "q1").model).toBe("child");
    expect(makePayload(turn({ model: "p1/m1" }), "q1").model).toBe("p1/m1");
    
    expect(makePayload(turn({ model: "" }), "q1").model).toBe("parent");
    expect(makePayload(turn({ model: undefined }), "q1").model).toBe("parent");
  });

  it("plan=false 也要带出去（表示「确认了，放行」）", () => {
    expect(makePayload(turn({ plan: false }), "q1").plan).toBe(false);
  });

  it("qid 每次都不一样", () => {
    expect(makeQid()).not.toBe(makeQid());
  });

  it("空消息（无文字/无图/无附件）不算一轮", () => {
    expect(isEmptyTurn(turn({ body: "   " }))).toBe(true);
    expect(isEmptyTurn(turn({ body: "", images: ["data:image/png;base64,x"] }))).toBe(false);
    expect(isEmptyTurn(turn({ body: "", attachments: [{ name: "a.txt", text: "x" }] }))).toBe(false);
  });

  it("附件只露文件名，全文不进会话显示", () => {
    const m = makeUserMessage("看这个", [], [{ name: "报告.pdf" }]);
    expect(m.content).toBe("看这个\n📎 报告.pdf");
  });

  it("没有正文时不留一个空行再跟附件", () => {
    expect(makeUserMessage("", [], [{ name: "a.png" }]).content).toBe("📎 a.png");
  });

  it("带图时转成 image_url 块", () => {
    const m = makeUserMessage("看", ["data:image/png;base64,AAA"], []);
    expect(Array.isArray(m.content)).toBe(true);
    const parts = m.content as { type: string; image_url?: { url: string } }[];
    expect(parts[0]).toEqual({ type: "text", text: "看" });
    expect(parts[1].image_url?.url).toBe("data:image/png;base64,AAA");
  });
});

describe("历史消息过滤", () => {
  it("丢掉还没落库的空壳 assistant，保留工具轮与思考", () => {
    const msgs = [
      { role: "user", content: "hi" },
      { role: "assistant", content: "  " },                                  
      { role: "assistant", content: "", tool_calls: [{ id: "1" }] },         
      { role: "assistant", content: "", reasoning: "想了想" },                
      { role: "assistant", content: "答案" },
    ] as unknown as ChatMessage[];
    const kept = visibleMessages(msgs);
    expect(kept).toHaveLength(4);
    expect(kept[0].role).toBe("user");
  });

  it("多模态内容里有非空文本也算有内容", () => {
    const msgs = [{
      role: "assistant",
      content: [{ type: "text", text: "看得见" }],
    }] as unknown as ChatMessage[];
    expect(visibleMessages(msgs)).toHaveLength(1);
  });

  it("多模态内容全是空白就算空壳", () => {
    const msgs = [{ role: "assistant", content: [{ type: "text", text: " " }] }] as unknown as ChatMessage[];
    expect(visibleMessages(msgs)).toHaveLength(0);
  });

  it("功能性注入消息按标记隐藏，用户自己的 [xxx] 指令照常显示", () => {
    const msgs = [
      { role: "user", content: "先跑构建" },
      { role: "user", content: "[后台命令完成] job=1 | done", _bg_job: "1" },
      { role: "user", content: "[父级追加指令]\n继续", _sys: "subagent" },
      
      { role: "user", content: "[重要] 先别改配置" },
      { role: "user", content: "[用户已确认实施计划] 请按上面的计划开始执行。", _sys: "resume" },
      { role: "assistant", content: "好了" },
    ] as unknown as ChatMessage[];
    const kept = visibleMessages(msgs);
    expect(kept).toHaveLength(4);
    expect(kept[0].content).toBe("先跑构建");
    expect(kept[1].content).toBe("[重要] 先别改配置");
    expect(kept[2]._sys).toBe("resume");
  });

  it("用户真连发两句一样的话，两条都保留（不做判重）", () => {
    const msgs = [
      { role: "user", content: "再来" },
      { role: "user", content: "再来" },
    ] as unknown as ChatMessage[];
    expect(visibleMessages(msgs)).toHaveLength(2);
  });
});

describe("未完成快照", () => {
  it("超过 12 小时视为过期", () => {
    const now = Date.now();
    expect(isPartialStale({ text: "x", reason: "", ts: now - PARTIAL_TTL_MS - 1 }, now)).toBe(true);
    expect(isPartialStale({ text: "x", reason: "", ts: now - 1000 }, now)).toBe(false);
  });

  it("没有快照时不算过期（只是没有）", () => {
    expect(isPartialStale(null)).toBe(false);
  });

  it("还原时先放提示，再放思考与正文", () => {
    const live = liveFromPartial({ text: "答", reason: "想" });
    expect(live.map((x) => x.kind)).toEqual(["notice", "reason", "text"]);
  });

  it("空快照不弹任何东西（避免误报「上次未完成」）", () => {
    expect(liveFromPartial({ text: "  ", reason: "" })).toEqual([]);
  });

  it("还原块带 partial 标记，收尾时能精确撤掉", () => {
    const live = liveFromPartial({ text: "答", reason: "想" });
    expect(live.every((x) => x.tag === "partial" || x.kind !== "notice")).toBe(true);
    expect(live[0].tag).toBe("partial");
  });
});



describe("shouldRestorePartial（落库账本判据）", () => {
  const user = { role: "user", content: "问" } as unknown as ChatMessage;
  const assistant = { role: "assistant", content: "答" } as unknown as ChatMessage;
  const p = { text: "答", reason: "", ts: Date.now() };

  it("末条已是完整 assistant → 快照是残留，不还原", () => {
    expect(shouldRestorePartial([user, assistant], p)).toBe(false);
  });

  it("末条是 user（done 丢在断连窗口）→ 确实要还原半截", () => {
    expect(shouldRestorePartial([user], p)).toBe(true);
  });

  it("空会话 / 无快照 / 空快照 / 过期快照都不还原", () => {
    expect(shouldRestorePartial([], p)).toBe(false);
    expect(shouldRestorePartial([user], null)).toBe(false);
    expect(shouldRestorePartial([user], { text: " ", reason: "", ts: p.ts })).toBe(false);
    expect(shouldRestorePartial([user], { ...p, ts: p.ts - PARTIAL_TTL_MS - 1 })).toBe(false);
  });

  it("快照比账本末条还旧 → 不是这一轮的半截", () => {
    const oldUser = { role: "user", content: "问", ts: p.ts / 1000 + 60 } as unknown as ChatMessage;
    expect(shouldRestorePartial([oldUser], p)).toBe(false);
  });

  it("只有思考没有正文也照还原（reason 非空）", () => {
    expect(shouldRestorePartial([user], { text: "", reason: "想", ts: p.ts })).toBe(true);
  });
});


describe("断点续传：重放事件与流式快照合并（2026-11-02）", () => {
  it("本地文本比服务端快照长时不截短（重放已补齐更新的分片）", () => {
    
    const live = [{ kind: "text" as const, text: "已经写到这里了" }];
    const merged = mergeStream(live, { text: "已经写到", reason: "" });
    expect(merged[0].text).toBe("已经写到这里了");
  });

  it("服务端快照更长时用服务端的（本地落后了）", () => {
    const live = [{ kind: "text" as const, text: "写到" }];
    const merged = mergeStream(live, { text: "写到更长了", reason: "" });
    expect(merged[0].text).toBe("写到更长了");
  });

  it("思考与正文的顺序：先思考再正文", () => {
    const live: { kind: "text" | "reason"; text: string }[] = [];
    const merged = mergeStream(live, { text: "答案", reason: "思考" });
    expect(merged.map((e) => e.kind)).toEqual(["reason", "text"]);
  });

  it("服务端没内容时原样返回（引用不变）", () => {
    const live = [{ kind: "text" as const, text: "x" }];
    expect(mergeStream(live, { text: "", reason: "" })).toBe(live);
  });

  it("内容没变就不造新数组（避免多余渲染）", () => {
    const live = [{ kind: "text" as const, text: "同样的" }];
    expect(mergeStream(live, { text: "同样的", reason: "" })).toBe(live);
  });
});

describe("mergeStream：用后端「正在流的半截」重建 live 尾部", () => {
  const live = (...items: [("text" | "reason" | "tool" | "notice" | "error"), string][]) =>
    items.map(([kind, text]) => ({ kind, text }) as any);

  it("stream 为空时原样返回同一个引用", () => {
    const l = live(["text", "已经写了一半"]);
    expect(mergeStream(l, null)).toBe(l);
    expect(mergeStream(l, { text: "", reason: "" })).toBe(l);
  });

  it("替换尾部那段流式文本，不是追加（同一段不能渲染两遍）", () => {
    const l = live(["text", "第一段"]);
    const out = mergeStream(l, { text: "第一段第二段" });
    expect(out).toEqual([{ kind: "text", text: "第一段第二段" }]);
  });

  it("前面已闭合的工具块 / 提示保留不动（一轮里可能 text → tool → text）", () => {
    const l = live(["text", "看下文件"], ["tool", "read_file"], ["text", "半截"]);
    const out = mergeStream(l, { text: "半截写完了" });
    expect(out.map((e) => e.kind)).toEqual(["text", "tool", "text"]);
    expect(out[0].text).toBe("看下文件");
    expect(out[2].text).toBe("半截写完了");
  });

  it("思考在前、正文在后（与模型输出顺序一致）", () => {
    const out = mergeStream([], { text: "答案", reason: "想一想" });
    expect(out.map((e) => e.kind)).toEqual(["reason", "text"]);
  });

  it("内容没变时不造新数组（hydrate 每次切回都跑，避免多余渲染）", () => {
    const l = live(["text", "一样"]);
    expect(mergeStream(l, { text: "一样" })).toBe(l);
  });
});
