

import type { PluginConfigField } from "./plugin";


export interface ApprovalItem {
  id: string;
  command: string;
  reason: string;
  kind?: string;
  file_diff?: { path: string; hunks: { id: number; tag: string; old: string; new: string }[] };
  
  risks: { target: string; description: string;
           severity: "low" | "medium" | "high" }[];
}

export interface McpServerCfg {
  name?: string;
  desc?: string;
  command: string;
  args: string[];
  env: Record<string, string>;
  url?: string;
  
  transport?: string;
  headers?: Record<string, string>;
  lazy?: boolean;
  enabled?: boolean;
}

export interface McpStatusItem {
  name: string;
  desc?: string;
  transport?: string;
  connected: boolean;
  tools: string[];
  error?: string;
  
  error_detail?: string;
  lazy?: boolean;
  
  disabled?: boolean;
  disabled_reason?: string;
}


export interface GithubTokenStatus {
  configured: boolean;
  
  hint: string;
  
  source: string;
}

export interface Checkpoint {
  sha: string;
  ts: number;
  message: string;
}

export interface EnvEntry {
  kind: "python" | "node";
  name: string;
  path: string;
  python?: string;
}

export interface UsageBucket {
  calls: number;
  prompt: number;
  completion: number;
  cost: number;
}


export interface UsageSummary {
  by_provider: Record<string, UsageBucket & { models: Record<string, UsageBucket> }>;
  today_cost: number;
  total_cost: number;
}



export interface PluginBotDecl {
  title?: string;
  greeting?: string;
  
  prompt?: string;
  
  workflow?: string;
  
  system_prompt_file?: string;
  
  inputs?: PluginConfigField[];
}



export interface ProjectOverview {
  path: string;
  name: string;
  is_project: boolean;
  is_top: boolean;
  parent: string | null;
  children: { name: string; path: string; depth: number; children: number;
              pluginProject?: boolean; devMode?: boolean; pluginId?: string }[];
  sessions: {
    id: string; title: string; kind?: string;
    created_at?: string; updated_at?: string; message_count?: number;
  }[];
  workflows: { name: string; status?: string; nodes?: number; updated_at?: string }[];
  plugins: {
    id: string; name?: string; version?: string;
    installed_at?: number; source?: string; manifest?: string;
    
    project?: string;

    
    has_page?: boolean;
    
    has_config?: boolean;
    
    mode?: "dev" | "release";
    desc?: string;
    
    readme?: string;
    
    workflows?: string[];
    
    requestedProviderKeys?: string[];
    
    state?: string[];
    bot?: PluginBotDecl | null;
  }[];
  
  tools: {
    id: string; name: string; desc?: string; project?: string;
    path?: string;
    
    has_config?: boolean;
    
    error?: string;
    
    config_error?: string;
  }[];
  skills: string[];
  
  ui?: { hiddenPluginProjects?: boolean; hiddenWorkflows?: boolean };
  
  git?: { enabled: boolean };
  
}
