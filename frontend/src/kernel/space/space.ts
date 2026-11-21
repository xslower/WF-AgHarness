


export function textWidth(text: string, fontSize: number): number {
  let w = 0;
  for (const ch of text) {
    const code = ch.codePointAt(0) ?? 0;
    
    const full = (code >= 0x2e80 && code <= 0x9fff) ||
                 (code >= 0xf900 && code <= 0xfaff) ||
                 (code >= 0xff00 && code <= 0xff60);
    w += full ? fontSize : fontSize * 0.6;
  }
  return w;
}


export function buttonMinWidth(text: string, fontSize = 13, padX = 24, border = 2): number {
  return Math.ceil(textWidth(text, fontSize) + padX + border);
}


export function iconBtnMinWidth(iconSize = 14, padX = 14, border = 2): number {
  return iconSize + padX + border;
}


export const PAD_PER_LEVEL = 1;

export function levelMin(childrenMin: number, level: number): number {
  return childrenMin + PAD_PER_LEVEL * 2 * level;
}


export function listRowMinWidth(nameChars = 20, sizeCol = 48, fontSize = 13): number {
  return Math.ceil(textWidth("字".repeat(nameChars), fontSize) + 16  + 8  + sizeCol + 12 );
}


export function artListMinWidth(): number {
  return listRowMinWidth() + 24 + 2;
}


export function artMainMinWidth(): number {
  return 320;
}


export function clampPanelWidth(w: number, viewportW: number, sidebarW: number,
                                artListW: number, chatMinW = 360): number {
  const available = viewportW - sidebarW - artListW - chatMinW - 20;
  const max = Math.max(artMainMinWidth(), Math.min(1200, available));
  return Math.min(max, Math.max(artMainMinWidth(), w));
}


export interface SpaceIssue {
  selector: string;
  issue: "overflow-x" | "wrapped" | "clipped";
  detail: string;
}

export function auditSpace(root: ParentNode = document): SpaceIssue[] {
  const issues: SpaceIssue[] = [];
  const els = root.querySelectorAll<HTMLElement>("*");
  for (const el of els) {
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") continue;
    const tag = el.tagName.toLowerCase();
    const cls = el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\s+/).join(".") : "";
    const sel = tag + cls;
    
    if (el.scrollWidth > el.clientWidth + 1 && cs.overflowX !== "auto" && cs.overflowX !== "scroll" && cs.overflowX !== "hidden") {
      issues.push({ selector: sel, issue: "overflow-x", detail: `内容 ${el.scrollWidth}px > 容器 ${el.clientWidth}px` });
    }
    
    if (cs.whiteSpace === "normal" && el.children.length === 0 && el.textContent && el.textContent.trim()) {
      const lh = parseFloat(cs.lineHeight) || 20;
      if (el.getBoundingClientRect().height > lh * 1.8 && el.textContent.length <= 30) {
        issues.push({ selector: sel, issue: "wrapped", detail: `短文本换行: "${el.textContent.slice(0, 20)}"` });
      }
    }
    
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.right > window.innerWidth + 1) {
      issues.push({ selector: sel, issue: "clipped", detail: `右边界 ${Math.round(r.right)}px 超出视口 ${window.innerWidth}px` });
    }
  }
  return issues.slice(0, 100);
}
