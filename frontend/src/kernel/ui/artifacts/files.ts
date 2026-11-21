
import type { FilePreview } from "../../api";
import { baseName } from "../format";
import { CODE_EXTS, type Tab } from "./types";

export { baseName };


export function tabKind(name: string, kind?: string): Tab["kind"] {
  const ext = name.split(".").pop()?.toLowerCase() || "";
  if (kind === "image") return "image";
  if (ext === "md") return "md";
  if (CODE_EXTS.has(ext)) return "code";
  return "text";
}


export function tabFromPreview(path: string, d: FilePreview): Tab {
  const ext = baseName(path).split(".").pop()?.toLowerCase() || "";
  const kind = tabKind(path, d.kind);
  return {
    key: path,
    title: baseName(path) || path,
    kind,
    dataurl: d.dataurl,
    content: d.content,
    ext,
    
    mdPreview: kind === "md",
  };
}
