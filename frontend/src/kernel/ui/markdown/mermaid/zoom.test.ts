import { describe, expect, it } from "vitest";
import {
  clampZoom, fitWidth, fitZoom, MAX_ZOOM, MIN_READABLE_ZOOM, MIN_ZOOM, nextZoom, zoomAtPoint, zoomLabel,
} from "./zoom";

describe("clampZoom", () => {
  it("钳制到 0.2x ~ 4x", () => {
    expect(clampZoom(0.01)).toBe(MIN_ZOOM);
    expect(clampZoom(99)).toBe(MAX_ZOOM);
    expect(clampZoom(1.5)).toBe(1.5);
  });

  it("非有限值退回 1（NaN/Infinity 不该把图炸没）", () => {
    expect(clampZoom(NaN)).toBe(1);
    expect(clampZoom(Infinity)).toBe(1);
    expect(clampZoom(-Infinity)).toBe(1);
  });
});

describe("nextZoom", () => {
  it("逐档放大/缩小，且在边界停住", () => {
    expect(nextZoom(1, 1)).toBe(1.25);
    expect(nextZoom(1, -1)).toBe(0.9);
    expect(nextZoom(4, 1)).toBe(MAX_ZOOM);
    expect(nextZoom(MIN_ZOOM, -1)).toBe(MIN_ZOOM);
  });

  it("从任意中间值也能走到下一档（不会原地卡死）", () => {
    const z = nextZoom(1.05, 1);
    expect(z).toBeGreaterThan(1.05);
    expect(nextZoom(1.05, -1)).toBeLessThan(1.05);
  });

  it("一直点放大能到上限，一直点缩小能到下限", () => {
    let z = 1;
    for (let i = 0; i < 50; i++) z = nextZoom(z, 1);
    expect(z).toBe(MAX_ZOOM);
    for (let i = 0; i < 50; i++) z = nextZoom(z, -1);
    expect(z).toBe(MIN_ZOOM);
  });
});

describe("fitWidth（内联只按宽度适应 + 可读下限）", () => {
  it("宽图按比例缩小到容器宽（未触及可读下限时）", () => {
    expect(fitWidth(650, 500)).toBeCloseTo(0.769, 3);
  });

  it("缩到 0.75 以下就停住，改让容器横向滚动（保字号可读）", () => {
    
    expect(fitWidth(1087, 498)).toBe(0.75);
    
    expect(fitWidth(1000, 800)).toBe(0.8);
  });

  it("高图不会被高度压小（避免自找的小字）", () => {
    
    expect(fitWidth(500, 500)).toBe(1);
  });

  it("小图不放大", () => {
    expect(fitWidth(100, 500)).toBe(1);
  });

  it("容器尺寸未知时退回 1", () => {
    expect(fitWidth(300, 0)).toBe(1);
  });

  it("可读下限保证 12px 字号不小于 9px", () => {
    expect(12 * MIN_READABLE_ZOOM).toBeGreaterThanOrEqual(9);
  });
});

describe("fitZoom", () => {
  it("按宽高比取更小的一边，且默认不放大", () => {
    expect(fitZoom({ w: 1000, h: 500 }, { w: 500, h: 500 })).toBe(0.5);
    expect(fitZoom({ w: 100, h: 100 }, { w: 500, h: 500 })).toBe(1); 
  });

  it("allowUpscale 时允许超过 1", () => {
    expect(fitZoom({ w: 100, h: 100 }, { w: 400, h: 400 }, { allowUpscale: true })).toBe(4);
  });

  it("容器尺寸未知时退回 1（首帧 clientWidth 可能是 0）", () => {
    expect(fitZoom({ w: 100, h: 100 }, { w: 0, h: 0 })).toBe(1);
  });
});

describe("zoomAtPoint", () => {
  it("锚点下的内容缩放前后不移动", () => {
    
    const next = zoomAtPoint(1, 2, { x: 100, y: 100 }, { left: 50, top: 50 });
    
    expect(next.left).toBe(200);
    expect(next.top).toBe(200);
  });

  it("缩小回 1x 时回到原位置", () => {
    const back = zoomAtPoint(2, 1, { x: 100, y: 100 }, { left: 200, top: 200 });
    expect(back.left).toBe(50);
    expect(back.top).toBe(50);
  });

  it("不会算出负的滚动位置", () => {
    const r = zoomAtPoint(1, 2, { x: 0, y: 0 }, { left: 0, top: 0 });
    expect(r.left).toBe(0);
    expect(r.top).toBe(0);
  });

  it("非法输入原样返回（不产生 NaN 滚动）", () => {
    expect(zoomAtPoint(0, 2, { x: 10, y: 10 }, { left: 5, top: 5 })).toEqual({ left: 5, top: 5 });
    expect(zoomAtPoint(1, NaN, { x: 10, y: 10 }, { left: 5, top: 5 })).toEqual({ left: 5, top: 5 });
  });
});

describe("zoomLabel", () => {
  it("显示成百分比", () => {
    expect(zoomLabel(1)).toBe("100%");
    expect(zoomLabel(0.9)).toBe("90%");
    expect(zoomLabel(1.25)).toBe("125%");
  });
});
