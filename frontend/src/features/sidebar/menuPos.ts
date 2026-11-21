

export interface Rect {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export interface Size {
  width: number;
  height: number;
}

export interface Viewport {
  width: number;
  height: number;
}


const MARGIN = 8;

const GAP = 4;

export function menuPosition(btn: Rect, menu: Size, vp: Viewport): { x: number; y: number } {
  
  let x = btn.right - menu.width;
  x = Math.max(MARGIN, Math.min(x, vp.width - menu.width - MARGIN));

  
  let y = btn.bottom + GAP;
  if (y + menu.height > vp.height - MARGIN) y = btn.top - menu.height - GAP;
  y = Math.max(MARGIN, Math.min(y, vp.height - menu.height - MARGIN));

  return { x: Math.round(x), y: Math.round(y) };
}
