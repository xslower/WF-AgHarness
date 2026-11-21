

export interface ArtifactFile {
  name: string;
  path: string;
  mtime: number;
  size: number;
}

export interface FilePreview {
  kind: "image" | "text";
  dataurl?: string;
  content?: string;
}

export interface ArtifactList {
  files: ArtifactFile[];
  reports: ArtifactFile[];
}



export interface RecentFile {
  
  path: string;
  
  rel: string;
  
  name: string;
  
  op: string;
  kind: "file" | "dir";
  size: number;
  mtime: number;
  
  updated: number;
}



export interface RecentFiles {
  items: RecentFile[];
  rev: number;
  unchanged?: boolean;
}



export interface TrashEntry {
  
  stamp: string;
  
  age_days: number;
  
  files: number;
  
  bytes: number;
}

export interface TrashInfo {
  entries: TrashEntry[];
  total_files: number;
  total_bytes: number;
  trash_enabled: boolean;
  retention_days: number;
}

export interface DirEntry {
  name: string;
  path: string;
}

export interface BrowseResult {
  current: string;
  parent: string;
  dirs: DirEntry[];
}


