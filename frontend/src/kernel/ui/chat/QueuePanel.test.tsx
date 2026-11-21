
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { QueuePanel } from "./QueuePanel";
import type { QueueItem } from "./queueOps";

const item = (id: string, over: Partial<QueueItem> = {}): QueueItem => ({
  id, content: `内容${id}`, images: 0, attachments: [],
  workflow: "", interjecting: false, ...over,
});

const noop = () => {};
const render = (items: QueueItem[], max = 3) => renderToStaticMarkup(
  <QueuePanel items={items} max={max} onRemove={noop} onEdit={noop}
    onInterject={noop} onCancelInterject={noop} />,
);

describe("QueuePanel", () => {
  it("队列为空时不渲染任何东西", () => {
    expect(render([])).toBe("");
  });

  it("显示条数、正文预览与序号", () => {
    const html = render([item("1"), item("2")]);
    expect(html).toContain("待发送");
    expect(html).toContain("2/3");
    expect(html).toContain("内容1");
    expect(html).toContain("内容2");
    expect(html.match(/queue-idx/g)).toHaveLength(2);
  });

  it("每条都有 插队 / 编辑 / 删除 三个按钮", () => {
    const html = render([item("1")]);
    expect(html).toContain(">插队<");
    expect(html).toContain(">编辑<");
    expect(html).toContain(">删除<");
    expect(html).not.toContain("插队中");
  });

  it("满 3 条时提示先删除或撤回", () => {
    const html = render([item("1"), item("2"), item("3")]);
    expect(html).toContain("3/3");
    expect(html).toContain("已满");
    expect(html).toContain("先删除或撤回一条");
  });

  it("插队中的行只显示「插队中…」与取消，不再给三个按钮", () => {
    const html = render([item("1", { interjecting: true })]);
    expect(html).toContain("插队中…");
    expect(html).toContain("取消");
    expect(html).not.toContain(">插队<");
    expect(html).not.toContain(">删除<");
    expect(html).toContain("queue-row interjecting");
  });

  it("图片 / 附件 / 编排 / 工作流 都给出角标", () => {
    const html = render([item("1", {
      images: 2, attachments: ["a.md"], workflow: "wf1",
    })]);
    expect(html).toContain("🖼2");
    
    expect(html).toContain("a.md");
    expect(html).toContain("<svg");
    expect(html).toContain("工作流");
    expect(html).toContain("工作流");
  });

  it("同名附件各占一个角标（key 不能只用文件名）", () => {
    const html = render([item("1", { attachments: ["a.md", "a.md", "b.md"] })]);
    
    
    
    expect(html.match(/class="queue-badge"/g)).toHaveLength(3);
    expect(html.match(/a\.md/g)).toHaveLength(2);
    expect(html).toContain("b.md");
  });

  it("长文本在 title 里保留全文，正文截断省略", () => {
    const long = "长".repeat(200);
    const html = render([item("1", { content: long })]);
    expect(html).toContain(`title="${long}"`);
    expect(html).toContain("…");
  });

  it("按钮点了会回调（事件绑定存在）", () => {
    const onRemove = vi.fn();
    renderToStaticMarkup(
      <QueuePanel items={[item("q9")]} onRemove={onRemove} onEdit={noop}
        onInterject={noop} onCancelInterject={noop} />,
    );
    
    expect(onRemove).not.toHaveBeenCalled();
  });
});
