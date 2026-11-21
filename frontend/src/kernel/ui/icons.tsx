
import type { ReactNode } from "react";

export type IconName =
  | "folder" | "folder-open" | "chat" | "workflow"
  | "settings" | "plan" | "artifacts" | "list" | "robot" | "puzzle"
  | "wrench" | "paperclip" | "thought" | "sparkle" | "mic" | "trash"
  | "import" | "export" | "bolt" | "globe" | "file-text" | "book" | "code"
  | "branch" | "loop" | "map" | "search" | "image" | "plug" | "stop" | "plus"
  | "check" | "pencil" | "x" | "copy" | "circle" | "dot" | "expand"
  | "arrow-down" | "alert" | "human";

const PATHS: Record<IconName, ReactNode> = {
  folder: (
    <>
      <path d="M3 7.5A1.5 1.5 0 0 1 4.5 6h4l1.8 2h9.2A1.5 1.5 0 0 1 21 9.5v8A1.5 1.5 0 0 1 19.5 19h-15A1.5 1.5 0 0 1 3 17.5z" />
    </>
  ),
  "folder-open": (
    <>
      <path d="M3.5 8.5V6.5A1 1 0 0 1 4.5 5.5h4l1.7 2h8.3a1 1 0 0 1 1 1v2" />
      <path d="M3.5 10h17l-2 9h-13z" />
    </>
  ),
  chat: (
    <>
      <path d="M20 15.5a1.5 1.5 0 0 1-1.5 1.5H9l-5 4V6.5A1.5 1.5 0 0 1 5.5 5h13A1.5 1.5 0 0 1 20 6.5z" />
      <path d="M8.5 9.5h7M8.5 12.8h4.5" />
    </>
  ),
  workflow: (
    <>
      <circle cx="5" cy="6" r="1.8" />
      <circle cx="19" cy="18" r="1.8" />
      <circle cx="19" cy="6" r="1.8" />
      <path d="M6.8 6h10.4M19 7.8v8.4M6.8 6.9v6.6a3 3 0 0 0 3 3h7" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2.4M12 18.6V21M3 12h2.4M18.6 12H21M5.6 5.6l1.7 1.7M16.7 16.7l1.7 1.7M18.4 5.6l-1.7 1.7M7.3 16.7l-1.7 1.7" />
    </>
  ),
  plan: (
    <>
      <path d="M4 6.6l1.3 1.3L8 5.3" />
      <path d="M11 6.6h9M11 12h9M11 17.4h9" />
      <path d="M4 12.6l1.3 1.3L8 11.3" />
    </>
  ),
  artifacts: (
    <>
      <path d="M3.8 7h16.4v3.2H3.8z" />
      <path d="M5.4 10.2V19h13.2v-8.8" />
      <path d="M10 13.4h4" />
      <path d="M8.6 7L10 4.2h4L15.4 7" />
    </>
  ),
  list: (
    <>
      <path d="M8.5 6h11.5M8.5 12h11.5M8.5 18h11.5" />
      <circle cx="4.3" cy="6" r="1.1" />
      <circle cx="4.3" cy="12" r="1.1" />
      <circle cx="4.3" cy="18" r="1.1" />
    </>
  ),
  robot: (
    <>
      <rect x="3.8" y="7.4" width="16.4" height="11.2" rx="2.6" />
      <circle cx="9.2" cy="13" r="1.2" />
      <circle cx="14.8" cy="13" r="1.2" />
      <path d="M12 4.6v2.8" />
      <circle cx="12" cy="3.6" r="1" />
      <path d="M9.5 16.2h5" />
    </>
  ),
  puzzle: (
    <>
      <path d="M10 4.6a2 2 0 0 1 4 0V6h1.4A1.6 1.6 0 0 1 17 7.6V9h1.4a2 2 0 0 1 0 4H17v1.4a1.6 1.6 0 0 1-1.6 1.6H13v1.4a2 2 0 0 1-4 0V16H7.6A1.6 1.6 0 0 1 6 14.4V13H4.6a2 2 0 0 1 0-4H6V7.6A1.6 1.6 0 0 1 7.6 6H10z" />
    </>
  ),
  wrench: (
    <>
      <path d="M15.2 3.6a5 5 0 0 0-4.4 6.9l-6.3 6.3a1.8 1.8 0 0 0 2.5 2.5l6.3-6.3a5 5 0 0 0 6.9-4.4l-2.8 1.6-2.2-2.2z" />
    </>
  ),
  paperclip: (
    <>
      <path d="M19.5 11.4l-7.6 7.6a4.4 4.4 0 0 1-6.2-6.2l8-8a2.9 2.9 0 0 1 4.1 4.1l-8 8a1.4 1.4 0 0 1-2-2l7.3-7.3" />
    </>
  ),
  thought: (
    <>
      <path d="M8.2 17.4a4.4 4.4 0 0 1-.6-8.7 4 4 0 0 1 7.5-1.4 3.6 3.6 0 0 1 3.3 6 3.9 3.9 0 0 1-2.6 4.1z" />
      <path d="M9 20.6h6" />
    </>
  ),
  sparkle: (
    <>
      <path d="M11 3.6l1.6 4.6 4.6 1.6-4.6 1.6L11 16l-1.6-4.6L4.8 9.8l4.6-1.6z" />
      <path d="M18 14.6l.6 1.7 1.7.6-1.7.6-.6 1.7-.6-1.7-1.7-.6 1.7-.6z" />
    </>
  ),
  mic: (
    <>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5.6 11.4a6.4 6.4 0 0 0 12.8 0" />
      <path d="M12 17.8V21" />
    </>
  ),
  trash: (
    <>
      <path d="M4 7h16" />
      <path d="M9.4 7V4.8h5.2V7" />
      <path d="M6.4 7l1 12.4h9.2L17.6 7" />
      <path d="M10.4 11v6M13.6 11v6" />
    </>
  ),
  
  human: (
    <>
      <circle cx="12" cy="6.6" r="2.4" />
      <path d="M6.6 20v-4.2a5.4 5.4 0 0 1 10.8 0V20" />
      <path d="M12 13.4v3.2" />
    </>
  ),
  import: (
    <>
      <path d="M12 4v10" />
      <path d="M8 10.4l4 4 4-4" />
      <path d="M4.6 19h14.8" />
    </>
  ),
  export: (
    <>
      <path d="M12 15V5" />
      <path d="M8 9l4-4 4 4" />
      <path d="M4.6 19h14.8" />
    </>
  ),
  bolt: (
    <>
      <path d="M13.4 3L5.8 13.2h5l-1 7.8 7.8-10.4h-5z" />
    </>
  ),
  globe: (
    <>
      <circle cx="12" cy="12" r="8.4" />
      <path d="M3.6 12h16.8" />
      <path d="M12 3.6c2.4 2.4 3.7 5.2 3.7 8.4s-1.3 6-3.7 8.4c-2.4-2.4-3.7-5.2-3.7-8.4s1.3-6 3.7-8.4z" />
    </>
  ),
  "file-text": (
    <>
      <path d="M6 3.6h7.4L19 9.2V20.4H6z" />
      <path d="M13.4 3.6v5.6H19" />
      <path d="M9.2 13h6.4M9.2 16.6h4.2" />
    </>
  ),
  book: (
    <>
      <path d="M12 6.4c-2-1.5-4.4-2-7-1.5v12c2.6-.5 5 0 7 1.5 2-1.5 4.4-2 7-1.5v-12c-2.6-.5-5 0-7 1.5z" />
      <path d="M12 6.4v12" />
    </>
  ),
  code: (
    <>
      <path d="M8.6 8L4.4 12l4.2 4" />
      <path d="M15.4 8l4.2 4-4.2 4" />
      <path d="M13.6 5.4l-3.2 13.2" />
    </>
  ),
  branch: (
    <>
      <circle cx="6.2" cy="5.8" r="1.9" />
      <circle cx="17.8" cy="5.8" r="1.9" />
      <circle cx="12" cy="18.2" r="1.9" />
      <path d="M6.2 7.7v2.1a3 3 0 0 0 3 3h1.9M17.8 7.7v2.1a3 3 0 0 1-3 3h-1.9" />
      <path d="M12 12.8v3.5" />
    </>
  ),
  loop: (
    <>
      <path d="M4.6 12a7.4 7.4 0 0 1 12.6-5.3L20 9.4" />
      <path d="M20 4.8v4.6h-4.6" />
      <path d="M19.4 12a7.4 7.4 0 0 1-12.6 5.3L4 14.6" />
      <path d="M4 19.2v-4.6h4.6" />
    </>
  ),
  map: (
    <>
      <path d="M3.6 7.2l5-2 6 2.4 5.8-2.4v11.6l-5.8 2.4-6-2.4-5 2z" />
      <path d="M8.6 5.2v11.6M14.6 7.6v11.6" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="6.4" />
      <path d="M15.7 15.7l4.1 4.1" />
    </>
  ),
  image: (
    <>
      <rect x="3.6" y="4.6" width="16.8" height="14.8" rx="2" />
      <circle cx="9" cy="9.6" r="1.5" />
      <path d="M4.4 17l4.8-4.8 3.8 3.8 2.8-2.4 4 3.6" />
    </>
  ),
  plug: (
    <>
      <path d="M9 3.6v3.8M15 3.6v3.8" />
      <path d="M6.4 7.4h11.2v3.4a5.6 5.6 0 0 1-11.2 0z" />
      <path d="M12 16.4V20.6" />
    </>
  ),
  stop: (
    <>
      <rect x="6.6" y="6.6" width="10.8" height="10.8" rx="1.8" />
    </>
  ),
  plus: (
    <>
      <path d="M12 5v14M5 12h14" />
    </>
  ),
  check: (
    <>
      <path d="M4.5 12.5l5 5L19.5 7" />
    </>
  ),
  alert: (
    <>
      <path d="M12 4.5L21 19.5H3z" />
      <path d="M12 10v4" />
      <circle cx="12" cy="17" r="0.9" fill="currentColor" stroke="none" />
    </>
  ),
  pencil: (
    <>
      <path d="M15.4 4.6l4 4L9 19H5v-4z" />
      <path d="M13.4 6.6l4 4" />
    </>
  ),
  x: (
    <>
      <path d="M6 6l12 12M18 6L6 18" />
    </>
  ),
  copy: (
    <>
      <rect x="8.4" y="8.4" width="11.2" height="11.2" rx="1.8" />
      <path d="M15.6 5.4a1.8 1.8 0 0 0-1.8-1.8H6.2a1.8 1.8 0 0 0-1.8 1.8v7.6a1.8 1.8 0 0 0 1.8 1.8" />
    </>
  ),
  circle: (
    <>
      <circle cx="12" cy="12" r="7.4" />
    </>
  ),
  dot: (
    <>
      <circle cx="12" cy="12" r="7.4" />
      <circle cx="12" cy="12" r="3.4" fill="currentColor" stroke="none" />
    </>
  ),
  expand: (
    <>
      <path d="M8.5 9.5L12 6l3.5 3.5" />
      <path d="M8.5 14.5L12 18l3.5-3.5" />
    </>
  ),
  "arrow-down": (
    <>
      <path d="M12 4.5v15" />
      <path d="M6 13.5L12 19.5l6-6" />
    </>
  ),
};


export type IconTone = "blue" | "violet" | "amber" | "cyan" | "green" | "red" | "muted";

const DEFAULT_TONE: Partial<Record<IconName, IconTone>> = {
  
  
  folder: "amber", "folder-open": "amber",
  
  artifacts: "blue", "file-text": "blue",
  book: "blue", copy: "blue", import: "blue", export: "blue",
  
  robot: "violet", puzzle: "violet", sparkle: "violet",
  thought: "violet",
  
  chat: "blue", workflow: "green",
  
  settings: "cyan", plug: "cyan",
  
  plan: "amber", list: "amber", bolt: "amber", code: "amber", pencil: "amber",
  
  globe: "cyan", search: "cyan", image: "cyan", mic: "cyan",
  
  branch: "green", loop: "green", map: "green", check: "green", circle: "green",
  dot: "green",
  
  trash: "red", x: "red", stop: "red", alert: "red", human: "amber",
};

export function Icon({
  name, size = 16, className, title, tone,
}: {
  name: IconName;
  size?: number;
  className?: string;
  title?: string;
  
  tone?: IconTone;
}) {
  const t = tone ?? DEFAULT_TONE[name] ?? "muted";
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`ico tone-${t}${className ? ` ${className}` : ""}`}
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      focusable="false"
    >
      {title ? <title>{title}</title> : null}
      {PATHS[name]}
    </svg>
  );
}


export function nodeIcon(name: string): IconName {
  const map: Record<string, IconName> = {
    llm: "robot", subagent: "puzzle", handoff: "export", write: "file-text",
    f_read: "book", exec: "bolt", code: "code", web_search: "globe",
    web_fetch: "globe", condition: "branch", loop: "loop", map: "map",
    ocr: "search", image: "image", asr: "mic", mcp: "plug", tool: "wrench",
    op: "sparkle",
    human: "human",
    "文件 IO": "folder-open", "代码": "code", "网络": "globe",
    "逻辑": "branch", "扩展": "plug",
  };
  return map[name] || "wrench";
}
