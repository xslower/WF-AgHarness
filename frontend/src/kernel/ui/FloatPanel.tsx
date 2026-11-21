
import { useRef, useState, type ReactNode } from "react";

interface Props {
  
  storeKey: string;
  title: ReactNode;
  
  accent?: "warn" | "ok" | "info";
  
  onClose?: () => void;
  children: ReactNode;
}

interface Pos {
  x: number;
  y: number;
}

const POS_KEY = (k: string) => `ui.floatPos.${k}`;

function readPos(key: string): Pos | null {
  try {
    const raw = localStorage.getItem(POS_KEY(key));
    if (!raw) return null;
    const p = JSON.parse(raw) as Pos;
    if (typeof p?.x !== "number" || typeof p?.y !== "number") return null;
    return p;
  } catch {
    return null;
  }
}

export function FloatPanel({ storeKey, title, accent = "info", onClose, children }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<Pos | null>(() => readPos(storeKey));
  const drag = useRef<{ dx: number; dy: number } | null>(null);

  const startDrag = (e: React.PointerEvent) => {
    
    if ((e.target as HTMLElement).closest("button, input, textarea, select, a")) return;
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    drag.current = { dx: e.clientX - r.left, dy: e.clientY - r.top };
    
    setPos({ x: r.left, y: r.top });
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  };

  const onDrag = (e: React.PointerEvent) => {
    const d = drag.current;
    const el = ref.current;
    if (!d || !el) return;
    const x = Math.max(4, Math.min(window.innerWidth - el.offsetWidth - 4, e.clientX - d.dx));
    const y = Math.max(4, Math.min(window.innerHeight - el.offsetHeight - 4, e.clientY - d.dy));
    setPos({ x, y });
  };

  const endDrag = () => {
    if (!drag.current) return;
    drag.current = null;
    if (pos) {
      try {
        localStorage.setItem(POS_KEY(storeKey), JSON.stringify(pos));
      } catch {
        
      }
    }
  };

  return (
    <div
      ref={ref}
      className={`float-panel accent-${accent}`}
      style={pos ? { left: pos.x, top: pos.y, right: "auto", bottom: "auto" } : undefined}
    >
      <div
        className="float-head"
        onPointerDown={startDrag}
        onPointerMove={onDrag}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        title="按住拖动"
      >
        <span className="float-grip">⠿</span>
        <span className="float-title">{title}</span>
        {onClose && (
          <button className="float-x" onClick={onClose} title="关闭">✕</button>
        )}
      </div>
      <div className="float-content">{children}</div>
    </div>
  );
}
