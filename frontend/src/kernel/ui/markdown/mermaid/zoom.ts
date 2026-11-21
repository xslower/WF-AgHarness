

export const MIN_ZOOM = 0.2;
export const MAX_ZOOM = 4;


export function clampZoom(z: number): number {
  if (!Number.isFinite(z)) return 1;
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z));
}


const STEPS = [0.2, 0.3, 0.4, 0.5, 0.67, 0.75, 0.9, 1, 1.25, 1.5, 1.75, 2, 2.5, 3, 3.5, 4];

export function nextZoom(cur: number, dir: 1 | -1): number {
  if (dir > 0) return STEPS.find((s) => s > cur + 1e-6) ?? MAX_ZOOM;
  const below = [...STEPS].reverse().find((s) => s < cur - 1e-6);
  return below ?? MIN_ZOOM;
}


export const MIN_READABLE_ZOOM = 0.75;

export function fitWidth(contentW: number, boxW: number): number {
  if (!(contentW > 0) || !(boxW > 0)) return 1;
  return clampZoom(Math.min(1, Math.max(MIN_READABLE_ZOOM, boxW / contentW)));
}


export function fitZoom(
  content: { w: number; h: number },
  box: { w: number; h: number },
  opts: { allowUpscale?: boolean } = {},
): number {
  if (!(content.w > 0) || !(content.h > 0) || !(box.w > 0) || !(box.h > 0)) return 1;
  const z = Math.min(box.w / content.w, box.h / content.h);
  return clampZoom(opts.allowUpscale ? z : Math.min(1, z));
}


export function zoomAtPoint(
  cur: number,
  next: number,
  point: { x: number; y: number },
  scroll: { left: number; top: number },
): { left: number; top: number } {
  if (!Number.isFinite(next) || cur <= 0) return scroll;
  const ratio = next / cur;
  
  const cx = scroll.left + point.x;
  const cy = scroll.top + point.y;
  return {
    left: Math.max(0, cx * ratio - point.x),
    top: Math.max(0, cy * ratio - point.y),
  };
}


export function zoomLabel(z: number): string {
  return `${Math.round(z * 100)}%`;
}
