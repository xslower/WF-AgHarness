

import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MessageList } from "./MessageList";
import type { ChatMessage } from "../../api";
import { stubClipboard } from "../../../test-utils/clipboardMock";

beforeAll(() => {
  Element.prototype.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
});

beforeEach(() => {
  stubClipboard("ok");
});

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

function renderOne(m: ChatMessage) {
  return render(
    <MessageList config={null} messages={[m]} live={[]} busy={false}
      subAgents={{}} activeSubAgent={null} setActiveSubAgent={() => {}}
      suggestions={[]} onSend={() => {}} onEdit={() => {}}
      maxWidth={0} />,
  );
}

describe("用户消息的复制按钮", () => {
  it("我发的消息渲染复制按钮，且 title 说明会申请权限", () => {
    renderOne({ role: "user", content: "帮我改一下这个文件" });
    const btn = screen.getByTitle(/复制我发的消息/);
    expect(btn.getAttribute("title")).toContain("申请");
    expect(btn.getAttribute("aria-label")).toBe("复制我发的消息");
  });

  it("助手消息不加这个按钮（只加在我发的消息上）", () => {
    renderOne({ role: "assistant", content: "好的" });
    expect(screen.queryByTitle(/复制我发的消息/)).toBeNull();
  });

  it("权限被拒后点一次 → 出现可见的权限指引，不再静默失败", async () => {
    stubClipboard("denied", false);
    renderOne({ role: "user", content: "内容" });
    screen.getByTitle(/复制我发的消息/).click();
    
    await vi.waitFor(() => {
      expect(screen.getByRole("alert").textContent).toContain("剪贴板");
    });
  });
});
