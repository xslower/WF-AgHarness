

export interface Box {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Routed {
  path: string;
  sx: number;
  sy: number;
  ex: number;
  ey: number;
}


export function edgePath(a: Box, b: Box, vertical: boolean): Routed {
  if (vertical) {
    const ax = a.x + a.w / 2;
    const ay = a.y + a.h;
    const bx = b.x + b.w / 2;
    const by = b.y;
    if (Math.abs(ax - bx) < 1) {
      return { path: `M${ax},${ay} L${bx},${by}`, sx: ax, sy: ay, ex: bx, ey: by };
    }
    const midY = (ay + by) / 2;
    return {
      path: `M${ax},${ay} C${ax},${midY} ${bx},${midY} ${bx},${by}`,
      sx: ax, sy: ay, ex: bx, ey: by,
    };
  }
  const ax = a.x + a.w;
  const ay = a.y + a.h / 2;
  const bx = b.x;
  const by = b.y + b.h / 2;
  if (Math.abs(ay - by) < 1) {
    return { path: `M${ax},${ay} L${bx},${by}`, sx: ax, sy: ay, ex: bx, ey: by };
  }
  const midX = (ax + bx) / 2;
  return {
    path: `M${ax},${ay} C${midX},${ay} ${midX},${by} ${bx},${by}`,
    sx: ax, sy: ay, ex: bx, ey: by,
  };
}


function segHitsNode(
  x1: number, y1: number, x2: number, y2: number,
  n: { x: number; y: number; w: number; h: number },
): boolean {
  const minX = Math.min(x1, x2), maxX = Math.max(x1, x2);
  const minY = Math.min(y1, y2), maxY = Math.max(y1, y2);
  return minX < n.x + n.w - 1 && maxX > n.x + 1 && minY < n.y + n.h - 1 && maxY > n.y + 1;
}


export function routeAround(
  a: Box,
  b: Box,
  obstacles: Box[],
  vertical: boolean,
): Routed | null {
  
  const forward = vertical ? b.y > a.y + a.h : b.x > a.x + a.w;
  if (!forward) return null;
  
  const between = obstacles.filter((n) => {
    if (n.id === a.id || n.id === b.id) return false;
    return vertical
      ? n.y >= a.y + a.h && n.y + n.h <= b.y
      : n.x >= a.x + a.w && n.x + n.w <= b.x;
  });
  if (!between.length) return null;

  const ax = vertical ? a.x + a.w / 2 : a.x + a.w;
  const ay = vertical ? a.y + a.h : a.y + a.h / 2;
  const bx = vertical ? b.x + b.w / 2 : b.x;
  const by = vertical ? b.y : b.y + b.h / 2;

  
  const blocked = between.some((n) => segHitsNode(ax, ay, bx, by, n));
  if (!blocked) return null;

  
  const leftEdge = Math.min(...between.map((n) => (vertical ? n.x : n.y)));
  const rightEdge = Math.max(...between.map((n) => (vertical ? n.x + n.w : n.y + n.h)));
  const laneGap = 18;
  const leftLane = leftEdge - laneGap;
  const rightLane = rightEdge + laneGap;
  const curMid = vertical ? (ax + bx) / 2 : (ay + by) / 2;
  const useLeft = Math.abs(curMid - leftLane) <= Math.abs(curMid - rightLane);
  const lane = Math.max(useLeft ? leftLane : rightLane, 2);

  if (vertical) {
    
    return {
      path: `M${ax},${ay} L${ax},${ay + 8} L${lane},${ay + 8} L${lane},${by - 8} L${bx},${by - 8} L${bx},${by}`,
      sx: ax, sy: ay, ex: bx, ey: by,
    };
  }
  return {
    path: `M${ax},${ay} L${ax + 8},${ay} L${ax + 8},${lane} L${bx - 8},${lane} L${bx - 8},${by} L${bx},${by}`,
    sx: ax, sy: ay, ex: bx, ey: by,
  };
}


export function routeBack(
  a: Box,
  b: Box,
  obstacles: Box[],
  vertical: boolean,
): Routed | null {
  const backward = vertical ? b.y + b.h <= a.y : b.x + b.w <= a.x;
  if (!backward) return null;

  const gap = 16;
  const others = obstacles.filter((n) => n.id !== a.id && n.id !== b.id);
  const leftEdge = Math.min(
    ...others.map((n) => (vertical ? n.x : n.y)),
    vertical ? a.x : a.y,
    vertical ? b.x : b.y,
  );
  const rightEdge = Math.max(
    ...others.map((n) => (vertical ? n.x + n.w : n.y + n.h)),
    vertical ? a.x + a.w : a.y + a.h,
    vertical ? b.x + b.w : b.y + b.h,
  );
  const leftLane = leftEdge - gap;
  const rightLane = rightEdge + gap;
  const midA = vertical ? a.x + a.w / 2 : a.y + a.h / 2;
  const midB = vertical ? b.x + b.w / 2 : b.y + b.h / 2;
  const mid = (midA + midB) / 2;
  const useLeft = Math.abs(mid - leftLane) <= Math.abs(mid - rightLane);
  const lane = useLeft ? leftLane : rightLane;

  if (vertical) {
    
    const sx = useLeft ? a.x : a.x + a.w;
    const sy = a.y + a.h / 2;
    const ex = useLeft ? b.x : b.x + b.w;
    const ey = b.y + b.h / 2;
    return {
      path: `M${sx},${sy} L${lane},${sy} L${lane},${ey} L${ex},${ey}`,
      sx, sy, ex, ey,
    };
  }
  const sx = a.x + a.w / 2;
  const sy = useLeft ? a.y : a.y + a.h;
  const ex = b.x + b.w / 2;
  const ey = useLeft ? b.y : b.y + b.h;
  return {
    path: `M${sx},${sy} L${sx},${lane} L${ex},${lane} L${ex},${ey}`,
    sx, sy, ex, ey,
  };
}


export function selfLoopPath(a: Box): Routed {
  const x = a.x + a.w;
  const y = a.y + a.h / 2;
  const r = 18;
  return {
    path: `M${x},${y - r * 0.5} C${x + r * 1.6},${y - r} ${x + r * 1.6},${y + r} ${x},${y + r * 0.5}`,
    sx: x, sy: y - r * 0.5, ex: x, ey: y + r * 0.5,
  };
}


export function shiftPath(path: string, dx: number, dy: number): string {
  return path.replace(/(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/g, (_, x, y) =>
    `${(parseFloat(x) + dx).toFixed(1)},${(parseFloat(y) + dy).toFixed(1)}`,
  );
}


export function pathBounds(p: string): { x0: number; y0: number; x1: number; y1: number } {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const m of p.matchAll(/(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/g)) {
    const x = parseFloat(m[1]), y = parseFloat(m[2]);
    x0 = Math.min(x0, x); y0 = Math.min(y0, y);
    x1 = Math.max(x1, x); y1 = Math.max(y1, y);
  }
  return { x0, y0, x1, y1 };
}
