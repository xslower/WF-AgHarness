


const DEFAULT_CURSOR = "col-resize";

export function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

export interface DragSpec {
  
  startX: number;
  startY?: number;
  
  cursor?: string;
  
  onMove: (dx: number, dy: number, ev: MouseEvent) => void;
  onEnd?: () => void;
}

export function startDrag(spec: DragSpec): void {
  const { startX, startY = 0, cursor = DEFAULT_CURSOR, onMove, onEnd } = spec;
  const move = (ev: MouseEvent) => onMove(ev.clientX - startX, ev.clientY - startY, ev);
  const up = () => {
    window.removeEventListener("mousemove", move);
    window.removeEventListener("mouseup", up);
    document.body.style.cursor = "";
    onEnd?.();
  };
  document.body.style.cursor = cursor;
  window.addEventListener("mousemove", move);
  window.addEventListener("mouseup", up);
}

export interface ResizeSpec {
  
  width: number;
  min: number;
  max: number;
  
  edge?: "left" | "right";
  setWidth: (w: number) => void;
}


export function resizeWidth(spec: ResizeSpec) {
  const { width, min, max, edge = "left", setWidth } = spec;
  const sign = edge === "left" ? -1 : 1;
  return (e: React.MouseEvent) => {
    e.preventDefault();
    startDrag({
      startX: e.clientX,
      onMove: (dx) => setWidth(clamp(width + sign * dx, min, max)),
    });
  };
}

export interface ResizeHeightSpec {
  
  height: number;
  min: number;
  max: number;
  
  edge?: "top" | "bottom";
  setHeight: (h: number) => void;
}


export function resizeHeight(spec: ResizeHeightSpec) {
  const { height, min, max, edge = "top", setHeight } = spec;
  const sign = edge === "top" ? -1 : 1;
  return (e: React.MouseEvent) => {
    e.preventDefault();
    startDrag({
      startX: e.clientX,
      startY: e.clientY,
      cursor: "row-resize",
      onMove: (_dx, dy) => setHeight(clamp(height + sign * dy, min, max)),
    });
  };
}
