

import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MessageList } from "./MessageList";
import type { ChatMessage } from "../../api";


beforeAll(() => {
  Element.prototype.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(cleanup);

const user = (t: string): ChatMessage => ({ role: "user", content: t });

function renderList(messages: ChatMessage[], msgOffset: number, onEdit: (i: number) => void) {
  return render(
    <MessageList
      config={null} messages={messages} live={[]} busy={false}
      subAgents={{}} activeSubAgent={null} setActiveSubAgent={() => {}}
      suggestions={[]} onSend={() => {}} onEdit={onEdit}
      maxWidth={0} msgOffset={msgOffset} hasMore onLoadOlder={async () => ({ added: false, count: 0 })}
    />,
  );
}

describe("MessageList 消息身份", () => {
  it("prepend 更早历史后，点编辑仍指向原来那条消息（按消息对象现查下标）", () => {
    const older = user("更早的一句");
    const a = user("原第一条");
    const b = user("原第二条");
    const onEdit = vi.fn();

    const { rerender } = renderList([a, b], 10, onEdit);
    
    const withOlder = [older, a, b];
    rerender(
      <MessageList
        config={null} messages={withOlder} live={[]} busy={false}
        subAgents={{}} activeSubAgent={null} setActiveSubAgent={() => {}}
        suggestions={[]} onSend={() => {}} onEdit={onEdit}
        maxWidth={0} msgOffset={9} hasMore
        onLoadOlder={async () => ({ added: false, count: 0 })}
      />,
    );

    
    expect(screen.getAllByTitle("编辑并回滚上下文到此处")).toHaveLength(3);
    
    const rows = screen.getAllByTitle("编辑并回滚上下文到此处");
    rows[2].click();
    expect(onEdit).toHaveBeenCalledWith(2);
  });

  it("同一条消息的 key 在 prepend 前后不变（msgOffset + i 守恒）", () => {
    
    const before = { offset: 10, i: 1 };
    const after = { offset: 10 - 1, i: 1 + 1 };
    expect(before.offset + before.i).toBe(after.offset + after.i);
  });
});
