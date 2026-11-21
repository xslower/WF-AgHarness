

export interface WorkflowSummary {
  name: string;
  desc: string;
  nodes: number;
  
  internal?: boolean;
  
  parent?: string;
  
  status?: string;
}




export interface WfAvailable {
  name: string;
  desc?: string;
  nodes?: number;
  inputs?: string[];
  
  scope: "project" | "global";
}



export interface NodeCatalogField {
  key: string;
  label: string;
  kind: "text" | "textarea" | "code" | "select" | "number" | "boolean" | "model";
  options?: string[];
  required?: boolean;
  placeholder?: string;
}



export interface NodeCatalogItem {
  type: string;
  label: string;
  group: string;
  desc: string;
  fields: NodeCatalogField[];
}

export interface WfRunNode {
  status: string;
  output: string;
  ms: number;
  error?: string;
  attempts?: number;
  output_path?: string;
  output_bytes?: number;
  
  truncated?: boolean;
  
  original_chars?: number;
}



export interface WfRunWarning {
  code: string;
  node: string;
  message: string;
}



export interface WfRunFile {
  path: string;
  
  rel: string;
  name: string;
  size: number;
  mtime: number;
  
  node?: string;
}

export interface WfRun {
  id: string;
  workflow: string;
  status: "running" | "done" | "failed" | "cancelled";
  started: number;
  finished: number | null;
  nodes: Record<string, WfRunNode>;
  final: string;
  error: string;
  workspace?: string;
  inputs?: Record<string, unknown>;
  
  files?: WfRunFile[];
  
  pending_human?: HumanGateView | null;
  
  warnings?: WfRunWarning[];
  
  session?: string;
  
  parent_run?: string | null;
  parent_node?: string | null;
}



export interface HumanGateView {
  run_id?: string;
  node_id: string;
  title: string;
  ask: string;
  show: string;
  options: string[];
  created?: number;
}



export interface WfRunSummary {
  id: string;
  workflow: string;
  status: "running" | "done" | "failed" | "cancelled";
  started: number;
  finished: number | null;
  error: string;
  final_preview?: string;
  
  final_chars?: number;
  nodes: Record<string, {
    status: string; ms?: number; error?: string;
    output_preview?: string; output_chars?: number;
  }>;
  parent_run?: string | null;
  parent_node?: string | null;
}

export interface WfInputDecl {
  name: string;
  desc?: string;
  type?: string;
  default?: string;
}

export interface WorkflowEdge {
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
}

export interface WorkflowDef {
  name: string;
  desc?: string;
  
  status?: string;

  inputs?: WfInputDecl[];
  
  last_project?: string;
  _revision?: string;
  parallel_mode?: "agent" | "sequential";
  edges?: WorkflowEdge[];
  nodes: {
    id: string;
    type: string;
    prompt?: string;
    command?: string;
    path?: string;
    content?: string;
    task?: string;
    expr?: string;
    tool?: string;
    model?: string;
    next?: string | null;
    true?: string;
    false?: string;
    body?: string;
    [key: string]: unknown;
  }[];
}










export interface WfWhyDigest {
  node: string;
  status: string;
  
  chars: number;
  
  empty: boolean;
  
  reads: string[];
  
  writes: string[];
  ms?: number;
  error?: string;
}


export interface WfWhyHit {
  node: string;
  chars: number;
  
  at: number;
  
  snippet: string;
}

interface WfWhyBase { query: string }


export interface WfWhyNode extends WfWhyBase {
  query: "node";
  node: string;
  reads: string[];
  writes: string[];
  status: string;
  chars: number;
  ms?: number;
  
  path: string;
  preview: string;
}


export interface WfWhyKey extends WfWhyBase {
  query: "key";
  key: string;
  writers: string[];
  readers: string[];
}


export interface WfWhyGrep extends WfWhyBase {
  query: "grep";
  grep: string;
  hits: WfWhyHit[];
}


export interface WfWhyOverview extends WfWhyBase {
  query: "overview";
  workflow: string;
  status: string;
  nodes: WfWhyDigest[];
}

export type WfWhy = WfWhyNode | WfWhyKey | WfWhyGrep | WfWhyOverview;
