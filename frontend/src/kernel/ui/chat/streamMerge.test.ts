
import { beforeEach, describe, expect, it } from "vitest";
import { chatCtl } from "./chatController";
import { streamStore } from "./sessionStore";



const ctl = chatCtl as any;

const SID = "test-stream-merge";


function kinds(): { kind: string; text: string }[] {
  return streamStore.get(SID).live
    .filter((e) => e.kind === "text" || e.kind === "reason")
    .map((e) => ({ kind: e.kind, text: e.text }));
}

beforeEach(() => {
  streamStore.drop(SID);
  ctl.dropPendingStream(SID);
});

describe("流式分片合并", () => {
  it("同 kind 的相邻分片合并；不同 kind 保持到达顺序", () => {
    
    ctl.queueStream(SID, "text", "第一段");
    ctl.queueStream(SID, "text", "正文");
    ctl.queueStream(SID, "reason", "想一下");
    ctl.queueStream(SID, "reason", "再想");
    
    expect(kinds()).toEqual([]);
    ctl.flushStream(SID);
    expect(kinds()).toEqual([
      { kind: "text", text: "第一段正文" },
      { kind: "reason", text: "想一下再想" },
    ]);
  });

  it("先正文后思考的窗口，提交后顺序不能颠倒", () => {
    ctl.queueStream(SID, "text", "先说话");
    ctl.queueStream(SID, "reason", "后思考");
    ctl.flushStream(SID);
    expect(kinds()).toEqual([
      { kind: "text", text: "先说话" },
      { kind: "reason", text: "后思考" },
    ]);
  });

  it("交替到达（text/reason/text）三段都保留", () => {
    ctl.queueStream(SID, "text", "A");
    ctl.queueStream(SID, "reason", "B");
    ctl.queueStream(SID, "text", "C");
    ctl.flushStream(SID);
    expect(kinds()).toEqual([
      { kind: "text", text: "A" },
      { kind: "reason", text: "B" },
      { kind: "text", text: "C" },
    ]);
  });

  it("提交后缓冲清空；重复 flush 不重复追加（幂等）", () => {
    ctl.queueStream(SID, "text", "只一次");
    ctl.flushStream(SID);
    ctl.flushStream(SID);
    ctl.flushStream(SID);
    expect(kinds()).toEqual([{ kind: "text", text: "只一次" }]);
  });

  it("空分片被忽略，不产生空块", () => {
    ctl.queueStream(SID, "text", "");
    ctl.flushStream(SID);
    expect(kinds()).toEqual([]);
  });

  it("『非流式事件』会先把攒着的文本落地（顺序正确）", () => {
    
    ctl.queueStream(SID, "text", "先说明");
    ctl.handleWsEventData(SID, { type: "tool_start", name: "read_file", args: {} });
    const live = streamStore.get(SID).live;
    expect(live[0]).toMatchObject({ kind: "text", text: "先说明" });
    expect(live[1]).toMatchObject({ kind: "tool", toolName: "read_file" });
  });
});
