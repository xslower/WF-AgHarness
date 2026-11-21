
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { RichMarkdown, StreamingMarkdown } from "..";

const html = (text: string) => renderToStaticMarkup(createElement(RichMarkdown, { text }));

const CHART = `\`\`\`mermaid
flowchart TD
  A[开始] --> B{判断}
  B -->|是| C[执行]
  B -->|否| D[结束]
  C --> D
\`\`\``;

describe("会话流里的 mermaid 流程图", () => {
  it("mermaid 围栏渲染成 svg，而不是代码块", () => {
    const h = html(CHART);
    expect(h).toContain("<svg");
    expect(h).toContain("md-mermaid");
    expect(h).not.toContain("md-copy"); 
  });

  it("节点文字出现在 SVG 里", () => {
    const h = html(CHART);
    expect(h).toContain("开始");
    expect(h).toContain("判断");
    expect(h).toContain("执行");
    expect(h).toContain("结束");
  });

  it("边标签渲染", () => {
    const h = html(CHART);
    expect(h).toContain(">是<");
    expect(h).toContain(">否<");
  });

  it("不同形状用不同图元", () => {
    const h = html("```mermaid\nflowchart TD\n A[矩形] --> B{菱形}\n C((圆))\n```");
    expect(h).toContain("<rect");
    expect(h).toContain("<polygon"); 
    expect(h).toContain("<ellipse"); 
  });

  it("subgraph 画背景框并带标题", () => {
    const h = html("```mermaid\nflowchart TD\n subgraph G[分组名]\n A --> B\n end\n```");
    expect(h).toContain("分组名");
    expect(h).toContain("md-mermaid-group");
  });

  it("箭头 marker 与虚线样式", () => {
    const h = html("```mermaid\nflowchart TD\n A --> B\n A -.-> C\n```");
    expect(h).toContain("<marker");
    expect(h).toContain("stroke-dasharray");
  });

  it("无 language 的 flowchart 也认（graph 关键字）", () => {
    const h = html("```mermaid\ngraph LR\n A --> B\n```");
    expect(h).toContain("<svg");
  });

  it("不支持的图类型回落成代码块并给提示", () => {
    const h = html("```mermaid\nsequenceDiagram\n A->>B: hi\n```");
    expect(h).toContain("md-copy");
    expect(h).toContain("暂不支持该图表类型");
    expect(h).toContain("sequenceDiagram");
  });

  it("解析器完全认不出时保持原样代码块", () => {
    const h = html("```mermaid\n这不是图\n```");
    expect(h).toContain("md-copy");
    expect(h).toContain("这不是图");
  });

  it("普通代码块行为不变", () => {
    const h = html("```mermaidish\nA --> B\n```");
    expect(h).toContain("md-copy");
    expect(h).not.toContain("<svg");
  });

  it("流式渲染里也能出图", () => {
    const h = renderToStaticMarkup(
      createElement(StreamingMarkdown, { text: CHART, streaming: true }),
    );
    expect(h).toContain("<svg");
  });

  it("图表块不影响同一条消息里的其他 markdown", () => {
    const h = html(`前文**粗体**\n\n${CHART}\n\n| a | b |\n|---|---|\n| 1 | 2 |`);
    expect(h).toContain("<strong>粗体</strong>");
    expect(h).toContain("<svg");
    expect(h).toContain("<table>");
  });

  it("画布尺寸随内容增长（不是 0×0）", () => {
    const h = html(CHART);
    const m = h.match(/viewBox="0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"/);
    expect(m).toBeTruthy();
    expect(Number(m![1])).toBeGreaterThan(50);
    expect(Number(m![2])).toBeGreaterThan(50);
  });
});

describe("缩放 / 全屏控件", () => {
  it("工具条提供 缩小 / 百分比 / 放大 / 适应 / 全屏", () => {
    const h = html(CHART);
    expect(h).toContain('title="缩小"');
    expect(h).toContain('title="放大"');
    expect(h).toContain('title="适应窗口"');
    expect(h).toContain('title="恢复 100%"');
    expect(h).toContain('title="全屏查看"');
    expect(h).toContain("100%");
  });

  it("SVG 不再被 max-width 压扁（那正是小字看不清的根因）", () => {
    const h = html(CHART);
    const svgTag = h.slice(h.indexOf("<svg"), h.indexOf(">", h.indexOf("<svg")) + 1);
    expect(svgTag).not.toContain("max-width");
    expect(svgTag).not.toContain("maxWidth");
  });

  it("缩放容器撑出缩放后的实际尺寸，滚动区域才对得上", () => {
    const h = html(CHART);
    expect(h).toContain("md-mermaid-scaler");
    expect(h).toContain("md-mermaid-content");
    expect(h).toContain("transform:scale(");
  });

  it("全屏初始渲染不出覆盖层（只在点击后才 portal）", () => {
    const h = html(CHART);
    expect(h).not.toContain("md-mermaid-fs-layer");
  });

  it("图模式没有普通代码块的复制按钮（复制在工具条里）", () => {
    const h = html(CHART);
    expect(h).not.toContain("md-copy");
    expect(h).toContain("⧉");
  });
});
