
import { useCallback, useEffect, useRef, useState } from "react";

import { clampZoom, fitWidth, fitZoom, MIN_READABLE_ZOOM,
  nextZoom, zoomAtPoint } from "./zoom";


const FIT_PADDING = 24;

const INLINE_PADDING_X = 20;

export interface ZoomViewport {
  boxRef: React.RefObject<HTMLDivElement>;
  zoom: number;
  dragging: boolean;
  
  contentW: number;
  contentH: number;
  zoomBy: (dir: 1 | -1) => void;
  reset: () => void;
  fit: () => void;
  onPointerDown: (e: React.PointerEvent) => void;
  onPointerMove: (e: React.PointerEvent) => void;
  endDrag: (e: React.PointerEvent) => void;
}

export function useZoomViewport(opts: {
  width: number;
  height: number;
  
  initialZoom?: number;
  fullscreen: boolean;
}): ZoomViewport {
  const { width, height, initialZoom, fullscreen } = opts;
  const boxRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(() => initialZoom ?? 1);
  const [dragging, setDragging] = useState(false);
  const dragRef = useRef<{ x: number; y: number; left: number; top: number } | null>(null);
  
  const autoFit = useRef(initialZoom === undefined);

  const boxSize = useCallback(() => {
    const el = boxRef.current;
    return el ? { w: el.clientWidth, h: el.clientHeight } : { w: 0, h: 0 };
  }, []);

  
  const resetScroll = useCallback(() => {
    const el = boxRef.current;
    if (el) { el.scrollLeft = 0; el.scrollTop = 0; }
  }, []);

  const applyFit = useCallback(() => {
    const box = boxSize();
    
    
    const z = fullscreen
      ? Math.max(
          MIN_READABLE_ZOOM,
          fitZoom({ w: width, h: height }, { w: box.w - FIT_PADDING, h: box.h - FIT_PADDING }),
        )
      : fitWidth(width, box.w - INLINE_PADDING_X);
    setZoom(clampZoom(z));
    requestAnimationFrame(resetScroll);
  }, [boxSize, fullscreen, width, height, resetScroll]);

  
  useEffect(() => {
    if (!boxRef.current) return;
    if (autoFit.current) applyFit();
    const el = boxRef.current;
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      if (autoFit.current) applyFit();
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [applyFit]);

  const setManual = useCallback((z: number) => {
    autoFit.current = false;
    setZoom(clampZoom(z));
  }, []);

  const zoomBy = (dir: 1 | -1) => setManual(nextZoom(zoom, dir));

  
  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const next = clampZoom(zoom * (e.deltaY < 0 ? 1.15 : 1 / 1.15));
      if (next === zoom) return;
      const target = zoomAtPoint(
        zoom, next,
        { x: e.clientX - rect.left, y: e.clientY - rect.top },
        { left: el.scrollLeft, top: el.scrollTop },
      );
      setManual(next);
      
      requestAnimationFrame(() => {
        el.scrollLeft = target.left;
        el.scrollTop = target.top;
      });
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [zoom, setManual]);

  const onPointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    const el = boxRef.current;
    if (!el) return;
    dragRef.current = { x: e.clientX, y: e.clientY, left: el.scrollLeft, top: el.scrollTop };
    setDragging(true);
    el.setPointerCapture?.(e.pointerId);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const d = dragRef.current;
    const el = boxRef.current;
    if (!d || !el) return;
    
    el.scrollLeft = d.left - (e.clientX - d.x);
    el.scrollTop = d.top - (e.clientY - d.y);
  };

  const endDrag = (e: React.PointerEvent) => {
    dragRef.current = null;
    setDragging(false);
    boxRef.current?.releasePointerCapture?.(e.pointerId);
  };

  const reset = () => {
    autoFit.current = false;
    setZoom(1);
    requestAnimationFrame(resetScroll);
  };

  
  const fit = () => { autoFit.current = true; applyFit(); };

  return {
    boxRef, zoom, dragging,
    contentW: Math.round(width * zoom),
    contentH: Math.round(height * zoom),
    zoomBy, reset, fit,
    onPointerDown, onPointerMove, endDrag,
  };
}
