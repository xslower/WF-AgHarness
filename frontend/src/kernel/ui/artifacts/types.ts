

export interface Tab {
  key: string;
  title: string;
  kind: "image" | "text" | "web" | "md" | "code" | "subagent" | "workflow-run";
  
  subagentId?: string;
  sessionId?: string;
  
  runId?: string;
  workflow?: string;
  project?: string;
  dataurl?: string;
  content?: string;
  url?: string;
  mdPreview?: boolean;
  ext?: string;
  dirty?: boolean;
  
  conflict?: boolean;
}


export interface UrlBarState {
  urlInput: string;
  setUrlInput: (v: string) => void;
  showUrlBar: boolean;
  setShowUrlBar: (v: boolean) => void;
  openUrl: () => void;
}

export const CODE_EXTS = new Set(["py", "js", "ts", "tsx", "jsx", "sh", "json", "css", "html"]);

export interface FileCtxMenu {
  x: number;
  y: number;
  path: string;
  name: string;
  isDir: boolean;
}
