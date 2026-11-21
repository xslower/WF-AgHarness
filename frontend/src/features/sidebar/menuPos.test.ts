import { describe, expect, it } from "vitest";
import { menuPosition } from "./menuPos";

const MENU = { width: 120, height: 74 };
const VP = { width: 1440, height: 920 };


const btn = (right: number, top: number, h = 21) => ({
  left: right - 15, top, right, bottom: top + h,
});

describe("menuPosition 弹出菜单坐标", () => {
  it("常规位置：右边缘与按钮对齐，位于按钮下方 4px", () => {
    const p = menuPosition(btn(251, 153), MENU, VP);
    expect(p.x).toBe(251 - 120);   
    expect(p.y).toBe(153 + 21 + 4); 
  });

  it("贴屏幕底部时向上翻，不会掉出视口", () => {
    
    const p = menuPosition(btn(251, 895), MENU, VP);
    expect(p.y).toBe(895 - 74 - 4);          
    expect(p.y + MENU.height).toBeLessThanOrEqual(VP.height - 8);
  });

  it("按钮太靠右时向左夹回视口", () => {
    
    const p = menuPosition(btn(1435, 300), MENU, VP);
    expect(p.x).toBe(VP.width - MENU.width - 8);
    expect(p.x + MENU.width).toBeLessThanOrEqual(VP.width - 8);
  });

  it("极窄侧栏（按钮很靠左）也不会出现负坐标", () => {
    const p = menuPosition(btn(20, 100), MENU, VP);
    expect(p.x).toBe(8);
    expect(p.y).toBe(100 + 21 + 4);
  });

  it("小窗口下上下都放不下时仍留在视口内", () => {
    const vp = { width: 400, height: 90 };
    const p = menuPosition(btn(300, 40), MENU, vp);
    expect(p.y).toBeGreaterThanOrEqual(8);
    expect(p.y + MENU.height).toBeLessThanOrEqual(vp.height - 8);
    expect(p.x).toBeGreaterThanOrEqual(8);
    expect(p.x + MENU.width).toBeLessThanOrEqual(vp.width - 8);
  });

  it("坐标取整，避免 0.5px 造成的模糊", () => {
    const p = menuPosition({ left: 100.4, top: 153.7, right: 251.6, bottom: 175.2 }, MENU, VP);
    expect(Number.isInteger(p.x)).toBe(true);
    expect(Number.isInteger(p.y)).toBe(true);
  });
});
