

const FONT = 12;

export const LINE_H = 16;
const PAD_X = 14;
const PAD_Y = 10;

const MAX_CHARS = 18;


function charWidth(ch: string): number {
  const code = ch.codePointAt(0) ?? 0;
  const wide =
    (code >= 0x1100 && code <= 0x115f) ||
    (code >= 0x2e80 && code <= 0xa4cf) ||
    (code >= 0xac00 && code <= 0xd7a3) ||
    (code >= 0xf900 && code <= 0xfaff) ||
    (code >= 0xfe30 && code <= 0xfe6f) ||
    (code >= 0xff00 && code <= 0xff60) ||
    (code >= 0xffe0 && code <= 0xffe6);
  return wide ? FONT : FONT * 0.55;
}

export function textWidth(s: string): number {
  let w = 0;
  for (const ch of s) w += charWidth(ch);
  return w;
}


export function wrapLabel(label: string): string[] {
  const out: string[] = [];
  for (const rawLine of label.split("\n")) {
    let line = "";
    let w = 0;
    const limit = FONT * MAX_CHARS;
    for (const ch of rawLine) {
      const cw = charWidth(ch);
      if (w + cw > limit && line) {
        
        const sp = ch === " " ? -1 : line.lastIndexOf(" ");
        if (sp > 0 && ch !== " ") {
          out.push(line.slice(0, sp).trimEnd());
          line = line.slice(sp + 1);
          w = textWidth(line);
        } else {
          out.push(line.trimEnd());
          line = "";
          w = 0;
        }
      }
      line += ch;
      w += cw;
    }
    out.push(line.trimEnd());
  }
  return out.length ? out : [""];
}


export function measureNode(
  label: string,
  shape: string,
): { w: number; h: number; lines: string[] } {
  const lines = wrapLabel(label);
  const tw = Math.max(...lines.map(textWidth), 8);
  const th = lines.length * LINE_H;
  let w = tw + PAD_X * 2;
  let h = th + PAD_Y * 2;
  if (shape === "diamond") {
    
    w = tw * 1.55 + PAD_X * 2;
    h = th * 1.8 + PAD_Y * 2;
  } else if (shape === "hexagon") {
    w = tw + PAD_X * 2 + 20;
  } else if (shape === "circle") {
    
    const d = Math.max(tw, th, 14) + 18;
    w = d;
    h = d;
  } else if (shape === "flag" || shape === "parallelogram") {
    w = tw + PAD_X * 2 + 14;
  }
  return {
    w: Math.max(Math.round(w), 44),
    h: Math.max(Math.round(h), shape === "circle" ? 44 : 30),
    lines,
  };
}
