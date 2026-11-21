
import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { parseFlowchart, type NodeShape } from "./parser";
import { layoutFlow, textWidth, wrapLabel, type FlowLayout, type LaidNode } from "./layout";
import { LINE_H } from "./layoutMeasure";
import { zoomLabel, MAX_ZOOM, MIN_ZOOM } from "./zoom";
import { CopyButton } from "../../CopyButton";
import { useZoomViewport } from "./useZoomViewport";



function nodeShape(n: LaidNode, fill: string, stroke: string) {
  const { x, y, w, h } = n;
  switch (n.shape) {
    case "round":
      return <rect x={x} y={y} width={w} height={h} rx={h / 2 > 14 ? 14 : h / 2} fill={fill} stroke={stroke} />;
    case "stadium":
      return <rect x={x} y={y} width={w} height={h} rx={h / 2} fill={fill} stroke={stroke} />;
    case "subroutine":
      return (
        <g>
          <rect x={x} y={y} width={w} height={h} fill={fill} stroke={stroke} />
          <line x1={x + 6} y1={y} x2={x + 6} y2={y + h} stroke={stroke} />
          <line x1={x + w - 6} y1={y} x2={x + w - 6} y2={y + h} stroke={stroke} />
        </g>
      );
    case "cylinder": {
      const ry = Math.min(8, h / 6);
      return (
        <g>
          <path
            d={`M${x},${y + ry} A${w / 2},${ry} 0 0 1 ${x + w},${y + ry} V${y + h - ry} A${w / 2},${ry} 0 0 1 ${x},${y + h - ry} Z`}
            fill={fill} stroke={stroke}
          />
          <path d={`M${x},${y + ry} A${w / 2},${ry} 0 0 0 ${x + w},${y + ry}`} fill="none" stroke={stroke} />
        </g>
      );
    }
    case "circle":
      return <ellipse cx={x + w / 2} cy={y + h / 2} rx={w / 2} ry={h / 2} fill={fill} stroke={stroke} />;
    case "diamond":
      return (
        <polygon
          points={`${x + w / 2},${y} ${x + w},${y + h / 2} ${x + w / 2},${y + h} ${x},${y + h / 2}`}
          fill={fill} stroke={stroke}
        />
      );
    case "hexagon": {
      const k = Math.min(14, w / 4);
      return (
        <polygon
          points={`${x + k},${y} ${x + w - k},${y} ${x + w},${y + h / 2} ${x + w - k},${y + h} ${x + k},${y + h} ${x},${y + h / 2}`}
          fill={fill} stroke={stroke}
        />
      );
    }
    case "flag":
      return (
        <polygon
          points={`${x},${y} ${x + w - 10},${y} ${x + w},${y + h / 2} ${x + w - 10},${y + h} ${x},${y + h}`}
          fill={fill} stroke={stroke}
        />
      );
    case "parallelogram": {
      const k = 10;
      return (
        <polygon
          points={`${x + k},${y} ${x + w},${y} ${x + w - k},${y + h} ${x},${y + h}`}
          fill={fill} stroke={stroke}
        />
      );
    }
    default:
      return <rect x={x} y={y} width={w} height={h} rx={6} fill={fill} stroke={stroke} />;
  }
}


function nodeText(n: LaidNode, color: string) {
  const lines = wrapLabel(n.label);
  const startY = n.y + n.h / 2 - ((lines.length - 1) * LINE_H) / 2;
  return (
    <text
      x={n.x + n.w / 2}
      y={startY}
      fill={color}
      fontSize={12}
      textAnchor="middle"
      dominantBaseline="middle"
    >
      {lines.map((l, i) => (
        <tspan key={i} x={n.x + n.w / 2} dy={i === 0 ? 0 : LINE_H}>{l}</tspan>
      ))}
    </text>
  );
}


export function FlowchartSvg({
  source,
  markerPrefix = "",
  layout: givenLayout,
}: {
  source?: string;
  markerPrefix?: string;
  layout?: FlowLayout;
}) {
  const uid = useId().replace(/[^A-Za-z0-9_-]/g, "");
  const graph = useMemo(() => (source !== undefined ? parseFlowchart(source) : null), [source]);
  const layout = useMemo(
    () => givenLayout ?? (graph ? layoutFlow(graph) : null),
    [givenLayout, graph],
  );

  if (!layout) return null;

  const suffix = `${markerPrefix}${uid}`;
  const arrowId = `arrow-${suffix}`;
  const arrowDottedId = `arrow-dot-${suffix}`;
  const arrowThickId = `arrow-thick-${suffix}`;

  return (
    <svg
      className="md-mermaid-svg"
      viewBox={`0 0 ${layout.width} ${layout.height}`}
      width={layout.width}
      height={layout.height}
      role="img"
      aria-label="流程图"
    >
      <defs>
        {[
          { id: arrowId, w: 8, h: 8 },
          { id: arrowDottedId, w: 8, h: 8 },
          { id: arrowThickId, w: 9, h: 9 },
        ].map((m) => (
          <marker
            key={m.id}
            id={m.id}
            viewBox={`0 0 ${m.w} ${m.h}`}
            refX={m.w - 1}
            refY={m.h / 2}
            markerWidth={m.w}
            markerHeight={m.h}
            orient="auto-start-reverse"
          >
            <path d={`M0,0 L${m.w},${m.h / 2} L0,${m.h} Z`} fill="currentColor" />
          </marker>
        ))}
      </defs>

      {}
      {layout.groups.map((g) => (
        <g key={`g-${g.id}`} className="md-mermaid-group">
          <rect
            x={g.x} y={g.y} width={g.w} height={g.h} rx={8}
            fill="rgba(127,127,127,.06)"
            stroke="rgba(127,127,127,.35)"
            strokeDasharray="4 3"
          />
          <text x={g.x + 10} y={g.y + 15} fontSize={11} fill="currentColor" opacity={0.7}>{g.label}</text>
        </g>
      ))}

      {}
      {layout.edges.map((e, i) => {
        const markerId =
          e.style === "dotted" ? arrowDottedId : e.style === "thick" ? arrowThickId : arrowId;
        const dash = e.style === "dotted" ? "4 3" : undefined;
        const sw = e.style === "thick" ? 2.4 : 1.4;
        const labelW = e.label ? textWidth(e.label) * 0.92 + 8 : 0;
        return (
          <g key={`e-${i}`} className="md-mermaid-edge">
            <path
              d={e.path}
              fill="none"
              stroke="currentColor"
              strokeWidth={sw}
              strokeDasharray={dash}
              markerEnd={e.head === "none" ? undefined : `url(#${markerId})`}
              markerStart={e.tailHead ? `url(#${markerId})` : undefined}
            />
            {e.label && (
              <g>
                <rect
                  x={e.lx - labelW / 2}
                  y={e.ly - 9}
                  width={labelW}
                  height={16}
                  rx={3}
                  fill="var(--bg2, #15181e)"
                  opacity={0.92}
                />
                <text x={e.lx} y={e.ly} fontSize={11} textAnchor="middle" dominantBaseline="middle" fill="currentColor">
                  {e.label}
                </text>
              </g>
            )}
          </g>
        );
      })}

      {}
      {layout.nodes.map((n) => (
        <g key={`n-${n.id}`} className="md-mermaid-node">
          {nodeShape(n, "var(--bg2, #15181e)", "currentColor")}
          {nodeText(n, "currentColor")}
        </g>
      ))}
    </svg>
  );
}



interface ViewportProps {
  layout: FlowLayout;
  
  markerPrefix?: string;
  
  initialZoom?: number;
  fullscreen?: boolean;
  onToggleFullscreen?: () => void;
  
  children?: React.ReactNode;
}

function ChartViewport({
  layout,
  markerPrefix = "",
  initialZoom,
  fullscreen = false,
  onToggleFullscreen,
  children,
}: ViewportProps) {
  const v = useZoomViewport({ width: layout.width, height: layout.height, initialZoom, fullscreen });
  const { boxRef, zoom, dragging } = v;

  return (
    <div className={fullscreen ? "md-mermaid md-mermaid-fs" : "md-mermaid"}>
      <div className="md-mermaid-bar">
        <span className="md-mermaid-tag">mermaid · flowchart</span>
        <button className="md-mermaid-btn" title="缩小" onClick={() => v.zoomBy(-1)}>−</button>
        <button className="md-mermaid-btn md-mermaid-zoom" title="恢复 100%" onClick={v.reset}>
          {zoomLabel(zoom)}
        </button>
        <button className="md-mermaid-btn" title="放大" onClick={() => v.zoomBy(1)}>＋</button>
        <button
          className="md-mermaid-btn"
          title="适应窗口"
          onClick={v.fit}
        >适应</button>
        {children}
        {onToggleFullscreen && (
          <button
            className="md-mermaid-btn"
            title={fullscreen ? "退出全屏（Esc）" : "全屏查看"}
            onClick={onToggleFullscreen}
          >{fullscreen ? "✕ 退出" : "⛶ 全屏"}</button>
        )}
      </div>
      <div
        className={`md-mermaid-canvas${dragging ? " dragging" : ""}`}
        ref={boxRef}
        onPointerDown={v.onPointerDown}
        onPointerMove={v.onPointerMove}
        onPointerUp={v.endDrag}
        onPointerCancel={v.endDrag}
        onDoubleClick={v.reset}
        style={fullscreen ? { maxHeight: "none", flex: 1 } : undefined}
      >
        {}
        <div className="md-mermaid-scaler" style={{ width: v.contentW, height: v.contentH }}>
          <div
            className="md-mermaid-content"
            style={{
              width: layout.width,
              height: layout.height,
              transform: `scale(${zoom})`,
              transformOrigin: "0 0",
            }}
          >
            <FlowchartSvg layout={layout} markerPrefix={markerPrefix} />
          </div>
        </div>
      </div>
    </div>
  );
}



export type NodeShapeName = NodeShape;


export function MermaidBlock({ code }: { code: string }) {
  const [showSource, setShowSource] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const graph = useMemo(() => parseFlowchart(code), [code]);
  const layout = useMemo(() => (graph ? layoutFlow(graph) : null), [graph]);
  const ok = !!graph && !!layout;

  
  useEffect(() => {
    if (!fullscreen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        setFullscreen(false);
      }
    };
    window.addEventListener("keydown", onKey, true);
    
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey, true);
      document.body.style.overflow = prev;
    };
  }, [fullscreen]);

  
  if (!ok) {
    return (
      <div className="md-code md-mermaid-fallback">
        <CopyButton text={code} className="md-copy" label="复制代码" />
        <div className="md-mermaid-hint">暂不支持该图表类型，已显示源码</div>
        <pre><code className="language-mermaid">{code}</code></pre>
      </div>
    );
  }

  const toolbar = (
    <>
      <button className="md-mermaid-btn" onClick={() => setShowSource((v) => !v)}>
        {showSource ? "看图" : "源码"}
      </button>
      <CopyButton text={code} className="md-mermaid-btn" label="复制源码" />
    </>
  );

  if (showSource) {
    return (
      <div className="md-mermaid">
        <div className="md-mermaid-bar">
          <span className="md-mermaid-tag">mermaid · flowchart</span>
          {toolbar}
        </div>
        <pre className="md-mermaid-src"><code>{code}</code></pre>
      </div>
    );
  }

  return (
    <>
      <ChartViewport layout={layout!} onToggleFullscreen={() => setFullscreen(true)}>
        {toolbar}
      </ChartViewport>
      {fullscreen && typeof document !== "undefined" && createPortal(
        <div className="md-mermaid-fs-layer" role="dialog" aria-modal="true">
          <ChartViewport
            layout={layout!}
            markerPrefix="fs-"
            fullscreen
            onToggleFullscreen={() => setFullscreen(false)}
          />
        </div>,
        document.body,
      )}
    </>
  );
}

export { MAX_ZOOM, MIN_ZOOM };
