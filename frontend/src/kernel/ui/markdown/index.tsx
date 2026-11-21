
import { isValidElement, memo, useMemo } from "react";
import Markdown, { type Components } from "react-markdown";
import type { ChatMessage } from "../../api";
import { CopyButton } from "../CopyButton";
import { MermaidBlock } from "./mermaid/MermaidBlock";


function isMermaidLang(className?: string): boolean {
  const m = className?.match(/language-([\w-]+)/);
  return !!m && /^(mermaid|flowchart|graph)$/i.test(m[1]);
}


export function MdPre({ children }: { children?: React.ReactNode }) {
  const child = Array.isArray(children) ? children[0] : children;
  let className: string | undefined;
  let text = "";
  if (isValidElement(child)) {
    const props = child.props as { className?: string; children?: React.ReactNode };
    className = props.className;
    const c = props.children;
    text = String(Array.isArray(c) ? c.join("") : (c ?? "")).replace(/\n$/, "");
  } else {
    text = String(children ?? "").replace(/\n$/, "");
  }
  
  if (isMermaidLang(className)) return <MermaidBlock code={text} />;
  return (
    <div className="md-code">
      <CopyButton text={text} className="md-copy" label="复制代码" />
      <pre><code className={className}>{text}</code></pre>
    </div>
  );
}

export const mdComponents = { pre: MdPre };


export function mdText(t: string): string {
  let fence = false;
  return t.split("\n").map((l) => {
    if (/^\s*```/.test(l)) { fence = !fence; return l; }
    return fence ? l : l.replace(/^[ \t]+/, "");
  }).join("\n");
}



type Align = "left" | "center" | "right" | undefined;
export interface MdTableSeg {
  type: "table";
  head: string[];
  align: Align[];
  rows: string[][];
}
interface MdTextSeg {
  type: "text";
  text: string;
}
export type MdSeg = MdTableSeg | MdTextSeg;

const DELIM_CELL = /^:?-+:?$/;
const FENCE_RE = /^\s*(```+|~~~+)/;


function splitCells(line: string): string[] {
  let s = line.trim();
  if (s.startsWith("|")) s = s.slice(1);
  if (s.endsWith("|") && !s.endsWith("\\|")) s = s.slice(0, -1);
  const cells: string[] = [];
  let cur = "";
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (ch === "\\" && s[i + 1] === "|") { cur += "|"; i++; continue; }
    if (ch === "|") { cells.push(cur.trim()); cur = ""; continue; }
    cur += ch;
  }
  cells.push(cur.trim());
  return cells;
}


function parseAlign(line: string, cols: number): Align[] | null {
  if (!line.includes("-") || !line.includes("|") && cols > 1) return null;
  const cells = splitCells(line);
  if (cells.length !== cols) return null;
  const out: Align[] = [];
  for (const c of cells) {
    if (!DELIM_CELL.test(c)) return null;
    const l = c.startsWith(":");
    const r = c.endsWith(":");
    out.push(l && r ? "center" : l ? "left" : r ? "right" : undefined);
  }
  return out;
}


export function splitMdTables(src: string): MdSeg[] {
  const lines = src.split("\n");
  const out: MdSeg[] = [];
  let buf: string[] = [];
  let fence: string | null = null;
  const flush = () => {
    if (!buf.length) return;
    out.push({ type: "text", text: buf.join("\n") });
    buf = [];
  };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const fm = line.match(FENCE_RE);
    if (fm) {
      if (!fence) fence = fm[1][0];
      else if (fm[1][0] === fence) fence = null;
      buf.push(line);
      continue;
    }
    if (fence) { buf.push(line); continue; }
    
    if (line.includes("|") && i + 1 < lines.length) {
      const head = splitCells(line);
      const align = head.length && head.some((h) => h) ? parseAlign(lines[i + 1], head.length) : null;
      if (align) {
        const rows: string[][] = [];
        let j = i + 2;
        for (; j < lines.length; j++) {
          const l = lines[j];
          if (!l.trim() || !l.includes("|") || FENCE_RE.test(l)) break;
          const cells = splitCells(l);
          while (cells.length < head.length) cells.push("");
          rows.push(cells.slice(0, head.length));
        }
        flush();
        out.push({ type: "table", head, align, rows });
        i = j - 1;
        continue;
      }
    }
    buf.push(line);
  }
  flush();
  return out;
}


const inlineComponents: Components = {
  p: ({ children }) => <>{children}</>,
  ...mdComponents,
};

const alignStyle = (a: Align) => (a ? { textAlign: a } : undefined);

function MdTable({ seg }: { seg: MdTableSeg }) {
  return (
    <div className="md-table-wrap">
      <table>
        <thead>
          <tr>
            {seg.head.map((h, i) => (
              <th key={i} style={alignStyle(seg.align[i])}>
                <Markdown components={inlineComponents}>{h}</Markdown>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {seg.rows.map((r, ri) => (
            <tr key={ri}>
              {seg.head.map((_, ci) => (
                <td key={ci} style={alignStyle(seg.align[ci])}>
                  <Markdown components={inlineComponents}>{r[ci] ?? ""}</Markdown>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


export function RichMarkdown({ text, raw = false }: { text: string; raw?: boolean }) {
  const segs = useMemo(() => splitMdTables(raw ? text : mdText(text)), [text, raw]);
  return (
    <>
      {segs.map((s, i) =>
        s.type === "table"
          ? <MdTable key={i} seg={s} />
          : <Markdown key={i} components={mdComponents}>{s.text}</Markdown>,
      )}
    </>
  );
}


export function splitStableBlocks(text: string): string[] {
  const out: string[] = [];
  let buf: string[] = [];
  let fence: string | null = null;
  let blank = 0;
  for (const line of text.split("\n")) {
    const fm = line.match(/^\s*```/);
    if (fm) {
      fence = fence ? null : "x";
      buf.push(line);
      blank = 0;
      continue;
    }
    if (!fence && !line.trim()) {
      blank += 1;
      
      
      
      if (blank >= 1 && buf.length) {
        out.push(buf.join("\n") + "\n");
        buf = [];
      }
      continue;
    }
    blank = 0;
    buf.push(line);
  }
  if (buf.length) out.push(buf.join("\n"));
  return out;
}


const MdBlock = memo(function MdBlock({ text }: { text: string }) {
  const segs = useMemo(() => splitMdTables(mdText(text)), [text]);
  return (
    <>
      {segs.map((s, i) =>
        s.type === "table"
          ? <MdTable key={i} seg={s} />
          : <Markdown key={i} components={mdComponents}>{s.text}</Markdown>,
      )}
    </>
  );
});


export function StreamingMarkdown({ text, streaming }: {
  text: string;
  streaming?: boolean;
}) {
  if (!streaming) return <RichMarkdown text={text} />;
  const blocks = splitStableBlocks(text);
  return (
    <>
      {blocks.map((b, i) => <MdBlock key={i} text={b} />)}
    </>
  );
}

export function extractText(c: ChatMessage["content"]): string {
  if (typeof c === "string") return c;
  if (Array.isArray(c)) return c.filter((p) => p.type === "text").map((p) => p.text).join("\n");
  return "";
}
