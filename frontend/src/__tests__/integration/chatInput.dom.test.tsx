

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatPanel } from "../../kernel/ui/chat/ChatPanel";
import { readInput, saveInput, markInputSent, clearSentInput } from "../../kernel/ui/chat/chatStorage";
import { installFakeStorage } from "../../test-utils/fakeStorage";
import type { ChatStream } from "../../kernel/ui/chat/chatTypes";
import { IDLE_PLAN, initialStreamState } from "../../kernel/ui/chat/chatEvents";


function chatStub(onSend: (body: string) => Promise<boolean>): ChatStream {
  const s = initialStreamState();
  return {
    ...s,
    planState: IDLE_PLAN,
    send: onSend,
    sendPlanDecision: async () => {},
    stop: async () => {},
    queueAction: () => {},
    removeApproval: () => {},
    clearDebugLogs: () => {},
    setActiveSubAgent: () => {},
    querySubAgent: async () => {},
    messageSubAgent: async () => false,
    stopSubAgent: async () => {},
    editFrom: async () => null,
    loadOlder: async () => ({ added: 0, hasMore: false }),
    loadSession: () => {},
    refreshSession: async () => {},
    setNotifyOnDone: () => {},
  } as unknown as ChatStream;
}

const noop = () => {};


function mount(sessionId: string | null, onSend: (b: string) => Promise<boolean>) {
  return render(
    <ChatPanel
      project="/proj"
      chat={chatStub(onSend)}
      sessionId={sessionId}
      onSessionChange={noop}
      title="集成测试"
    />,
  );
}

const input = () => screen.getByRole("textbox") as HTMLTextAreaElement;

beforeEach(() => {
  installFakeStorage();
  
  
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
    providers: [], queues: { parent: [], child: [], summary: [] },
    settings: {},
  }), { status: 200, headers: { "Content-Type": "application/json" } })));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("真 DOM · 输入框草稿的用户操作序列", () => {
  it("打字 → 点发送 → 切到另一会话 → 切回来：输入框为空（原始 bug）", async () => {
    const user = userEvent.setup();
    
    const onSend = vi.fn(async () => {
      markInputSent("s-a", "发出去的话");
      return true;
    });

    const view = mount("s-a", onSend);
    await user.type(input(), "发出去的话");
    expect(input().value).toBe("发出去的话");
    expect(readInput("s-a")).toBe("发出去的话");

    
    await user.click(screen.getByTitle("发送"));
    await waitFor(() => expect(onSend).toHaveBeenCalledWith(
      "发出去的话", expect.objectContaining({ plan: expect.any(Boolean) })));
    
    await waitFor(() => expect(input().value).toBe(""));
    expect(readInput("s-a")).toBe("");

    
    view.rerender(
      <ChatPanel project="/proj" chat={chatStub(onSend)} sessionId="s-b"
                 onSessionChange={noop} title="集成测试" />);
    expect(input().value).toBe("");

    
    view.rerender(
      <ChatPanel project="/proj" chat={chatStub(onSend)} sessionId="s-a"
                 onSessionChange={noop} title="集成测试" />);
    expect(input().value).toBe("");
  });

  it("打字没发送 → 切会话 → 切回来：内容原样还在（草稿不能丢）", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn(async () => true);
    const view = mount("s-a", onSend);

    await user.type(input(), "打了一半没发");
    expect(readInput("s-a")).toBe("打了一半没发");

    view.rerender(
      <ChatPanel project="/proj" chat={chatStub(onSend)} sessionId="s-b"
                 onSessionChange={noop} title="集成测试" />);
    expect(input().value).toBe("");

    view.rerender(
      <ChatPanel project="/proj" chat={chatStub(onSend)} sessionId="s-a"
                 onSessionChange={noop} title="集成测试" />);
    expect(input().value).toBe("打了一半没发");
  });

  it("两条会话各自的草稿互不串台", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn(async () => true);
    const view = mount("s-a", onSend);
    await user.type(input(), "A 的内容");

    view.rerender(
      <ChatPanel project="/proj" chat={chatStub(onSend)} sessionId="s-b"
                 onSessionChange={noop} title="集成测试" />);
    await user.type(input(), "B 的内容");

    expect(readInput("s-a")).toBe("A 的内容");
    expect(readInput("s-b")).toBe("B 的内容");

    view.rerender(
      <ChatPanel project="/proj" chat={chatStub(onSend)} sessionId="s-a"
                 onSessionChange={noop} title="集成测试" />);
    expect(input().value).toBe("A 的内容");
  });

  it("发送失败（send 返回 false）→ 内容留在输入框，不用重敲", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn(async () => false);
    mount("s-a", onSend);

    await user.type(input(), "没发出去的话");
    await user.click(screen.getByTitle("发送"));
    await waitFor(() => expect(onSend).toHaveBeenCalled());
    expect(input().value).toBe("没发出去的话");
    expect(readInput("s-a")).toBe("没发出去的话");
  });

  it("后端确认后清掉已发送份，但回复期间新打的字不被误清", async () => {
    
    saveInput("s-a", "已发送的话");
    markInputSent("s-a", "已发送的话");
    expect(readInput("s-a")).toBe("");

    saveInput("s-a", "回复期间新打的一半");
    expect(readInput("s-a")).toBe("回复期间新打的一半");
    clearSentInput("s-a");              
    expect(readInput("s-a")).toBe("回复期间新打的一半");   

    clearSentInput("s-a");              
    expect(readInput("s-a")).toBe("回复期间新打的一半");
  });
});
