

export type FlowDirection = "TD" | "LR" | "BT" | "RL";

export type NodeShape =
  | "rect" 
  | "round" 
  | "stadium" 
  | "subroutine" 
  | "cylinder" 
  | "circle" 
  | "diamond" 
  | "hexagon" 
  | "flag" 
  | "parallelogram"; 

export type EdgeStyle = "solid" | "dotted" | "thick";
export type ArrowHead = "arrow" | "circle" | "cross" | "none";

export interface FlowNode {
  id: string;
  label: string;
  shape: NodeShape;
  
  groups: string[];
}

export interface FlowEdge {
  from: string;
  to: string;
  label: string;
  style: EdgeStyle;
  head: ArrowHead;
  
  tailHead: boolean;
}

export interface FlowGroup {
  id: string;
  label: string;
  parent: string | null;
}

export interface FlowGraph {
  direction: FlowDirection;
  nodes: FlowNode[];
  edges: FlowEdge[];
  groups: FlowGroup[];
}

interface NodeRef {
  id: string;
  label?: string;
  shape?: NodeShape;
}

const DIRS = new Set(["TD", "TB", "BT", "RL", "LR"]);
const NODE_ID_RE = /^[A-Za-z0-9_][A-Za-z0-9_.:]*/;


const IGNORE_LINE_RE = /^(classDef|class|style|linkStyle|click|link)\b/;


class GraphBuilder {
  nodes = new Map<string, { label: string; shape: NodeShape; groups: string[] }>();
  edges: FlowEdge[] = [];
  groups = new Map<string, FlowGroup>();
  stack: string[] = [];

  touch(ref: NodeRef) {
    const cur = this.nodes.get(ref.id);
    if (!cur) {
      this.nodes.set(ref.id, {
        label: ref.label ?? ref.id,
        shape: ref.shape ?? "rect",
        
        groups: [...this.stack],
      });
      return;
    }
    
    for (const g of this.stack) if (!cur.groups.includes(g)) cur.groups.push(g);
    
    if (ref.label !== undefined && cur.label === ref.id) cur.label = ref.label;
    if (ref.shape !== undefined && cur.shape === "rect") cur.shape = ref.shape;
  }

  addEdge(from: NodeRef, to: NodeRef, e: Omit<FlowEdge, "from" | "to">) {
    this.touch(from);
    this.touch(to);
    this.edges.push({ from: from.id, to: to.id, ...e });
  }
}


function readEnclosed(s: string, i: number, open: string, close: string) {
  
  let j = i + open.length;
  let depth = 1;
  let out = "";
  while (j < s.length) {
    if (s[j] === '"' && depth === 1) {
      
      const end = s.indexOf('"', j + 1);
      const inner = end < 0 ? s.slice(j + 1) : s.slice(j + 1, end);
      if (end < 0) return { text: cleanLabel(inner), next: s.length };
      out += inner.replace(/"/g, "");
      j = end + 1;
      continue;
    }
    if (s.startsWith(close, j)) {
      if (depth === 1) return { text: cleanLabel(out), next: j + close.length };
      depth -= 1;
      j += close.length;
      continue;
    }
    if (s.startsWith(open, j)) {
      depth += 1;
      j += open.length;
      continue;
    }
    out += s[j];
    j += 1;
  }
  return { text: cleanLabel(out), next: s.length };
}


function cleanLabel(t: string): string {
  return t
    .replace(/^"+|"+$/g, "")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/&nbsp;/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, "&")
    .trim();
}

const SHAPES: { open: string; close: string; shape: NodeShape }[] = [
  { open: "([", close: "])", shape: "stadium" },
  { open: "[[", close: "]]", shape: "subroutine" },
  { open: "[(", close: ")]", shape: "cylinder" },
  { open: "((", close: "))", shape: "circle" },
  { open: "{{", close: "}}", shape: "hexagon" },
  { open: "[/", close: "/]", shape: "parallelogram" },
  { open: "[", close: "]", shape: "rect" },
  { open: "(", close: ")", shape: "round" },
  { open: "{", close: "}", shape: "diamond" },
];


function readNodeRef(s: string, i: number): { ref: NodeRef; next: number } | null {
  while (i < s.length && s[i] === " ") i++;
  const m = s.slice(i).match(NODE_ID_RE);
  if (!m) return null;
  const ref: NodeRef = { id: m[0] };
  let j = i + m[0].length;
  
  while (s[j] === " ") j++;
  
  if (s[j] === ">") {
    const r = readEnclosed(s, j, ">", "]");
    ref.label = r.text;
    ref.shape = "flag";
    return { ref, next: r.next };
  }
  
  if (s.startsWith("[\\", j)) {
    const r = readEnclosed(s, j, "[\\", "\\]");
    ref.label = r.text;
    ref.shape = "parallelogram";
    return { ref, next: r.next };
  }
  for (const sh of SHAPES) {
    if (s.startsWith(sh.open, j)) {
      const r = readEnclosed(s, j, sh.open, sh.close);
      ref.label = r.text;
      ref.shape = sh.shape;
      return { ref, next: r.next };
    }
  }
  return { ref, next: j };
}


function readEdge(s: string, i: number) {
  while (i < s.length && s[i] === " ") i++;
  const rest = s.slice(i);
  
  let tailHead = false;
  let j = 0;
  if (/^(<|x|o)/.test(rest)) {
    const c = rest[0];
    
    if (c === "<") tailHead = true;
    else tailHead = false;
    if (c === "<") j = 1;
    else if ((c === "o" || c === "x") && /^[-=]/.test(rest.slice(1))) {
      tailHead = true;
      j = 1;
    }
  }
  const lineM = rest.slice(j).match(/^(-{2,}\.?|-\.+-|={2,}|-\.-?)/);
  if (!lineM) return null;
  const line = lineM[0];
  let k = j + line.length;
  const style: EdgeStyle = line.startsWith("=") ? "thick" : line.includes(".") ? "dotted" : "solid";
  
  let head: ArrowHead = "none";
  const h = rest[k];
  if (h === ">") head = "arrow";
  else if (h === "o") head = "circle";
  else if (h === "x") head = "cross";
  
  if (head !== "none") k += 1;
  
  let label = "";
  if (rest[k] === "|") {
    const end = rest.indexOf("|", k + 1);
    if (end > 0) {
      label = cleanLabel(rest.slice(k + 1, end));
      k = end + 1;
    }
  }
  
  return { style, head, tailHead, label, next: i + k };
}


function normalizeInlineLabels(line: string): string {
  return line
    .replace(/--\s+([^|>][^-]*?)\s+-->/g, "-->|$1|")
    .replace(/==\s+([^|>][^=]*?)\s+==>/g, "==>|$1|")
    .replace(/-\.\s+([^|.][^.]*?)\s+\.->/g, "-.->|$1|");
}


function parseStatement(stmt: string, b: GraphBuilder) {
  let i = 0;
  
  const firstGroup: NodeRef[] = [];
  for (;;) {
    const r = readNodeRef(stmt, i);
    if (!r) return;
    firstGroup.push(r.ref);
    i = r.next;
    while (i < stmt.length && stmt[i] === " ") i++;
    if (stmt[i] === "&") {
      i += 1;
      continue;
    }
    break;
  }
  firstGroup.forEach((ref) => b.touch(ref));
  let prev = firstGroup;
  
  for (;;) {
    const e = readEdge(stmt, i);
    if (!e) return;
    i = e.next;
    const group: NodeRef[] = [];
    for (;;) {
      const r = readNodeRef(stmt, i);
      if (!r) return;
      group.push(r.ref);
      i = r.next;
      while (i < stmt.length && stmt[i] === " ") i++;
      if (stmt[i] === "&") {
        i += 1;
        continue;
      }
      break;
    }
    for (const from of prev) {
      for (const to of group) {
        b.addEdge(from, to, {
          label: e.label,
          style: e.style,
          head: e.head,
          tailHead: e.tailHead,
        });
      }
    }
    prev = group;
  }
}


function splitStatements(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let inQuote = false;
  for (const ch of line) {
    if (ch === '"') inQuote = !inQuote;
    if (ch === ";" && !inQuote) {
      out.push(cur);
      cur = "";
      continue;
    }
    cur += ch;
  }
  out.push(cur);
  return out;
}


const UNSUPPORTED_RE =
  /^(sequenceDiagram|classDiagram|classDiagram-v2|stateDiagram|stateDiagram-v2|erDiagram|gantt|pie|journey|mindmap|timeline|gitGraph|block-beta|quadrantChart|xychart-beta|sankey-beta|zenuml|requirementDiagram|C4Context|C4Container|C4Component|C4Dynamic|C4Deployment)\b/;


export function parseFlowchart(src: string): FlowGraph | null {
  const lines = src.replace(/\r\n?/g, "\n").split("\n");
  let direction: FlowDirection | null = null;
  const b = new GraphBuilder();
  let sawStatement = false;

  for (const raw of lines) {
    let line = raw.trim();
    if (!line) continue;
    if (line.startsWith("%%")) continue;
    if (UNSUPPORTED_RE.test(line)) return null;
    
    const head = line.match(/^(?:flowchart|graph)\s+(TD|TB|BT|RL|LR)\b/i);
    if (head) {
      direction = head[1].toUpperCase() as FlowDirection;
      continue;
    }
    if (/^(flowchart|graph)\s*$/i.test(line) && !direction) {
      direction = "TD";
      continue;
    }
    if (/^%%\{/.test(line)) continue;
    if (IGNORE_LINE_RE.test(line)) continue;

    
    const sg = line.match(/^subgraph\s+([^\n]*)$/i);
    if (sg) {
      const rawName = sg[1].trim();
      let id = rawName;
      let label = rawName;
      const m = rawName.match(/^([A-Za-z0-9_][A-Za-z0-9_.:-]*)\s*\[(.*)\]$/);
      if (m) {
        id = m[1];
        label = cleanLabel(m[2]);
      }
      id = id.replace(/["']/g, "") || `sg${b.groups.size}`;
      b.groups.set(id, { id, label, parent: b.stack[b.stack.length - 1] ?? null });
      b.stack.push(id);
      continue;
    }
    if (/^end$/i.test(line)) {
      b.stack.pop();
      continue;
    }

    
    for (const stmtRaw of splitStatements(line)) {
      const stmt = normalizeInlineLabels(stmtRaw.trim());
      if (!stmt) continue;
      const before = b.edges.length + b.nodes.size;
      parseStatement(stmt, b);
      if (b.edges.length + b.nodes.size > before) sawStatement = true;
    }
  }

  if (!direction && !sawStatement) return null;
  if (b.nodes.size === 0) return null;

  return {
    direction: direction ?? "TD",
    nodes: [...b.nodes.entries()].map(([id, v]) => ({ id, label: v.label, shape: v.shape, groups: v.groups })),
    edges: b.edges,
    groups: [...b.groups.values()],
  };
}
