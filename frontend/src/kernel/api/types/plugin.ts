

import type { PluginBotDecl } from "./misc";



export type PluginConfigType =
  | "string" | "text" | "number" | "boolean" | "select" | "secret" | "key" | "path";

export interface PluginConfigField {
  key: string;
  label: string;
  type: PluginConfigType;
  
  default?: string | number | boolean;
  placeholder?: string;
  min?: number;
  max?: number;
  options?: string[];
  required?: boolean;
}


export interface PluginConfigResponse {
  id: string;
  
  project: string | null;
  values: Record<string, unknown>;
  fields: PluginConfigField[];
}


export interface InstalledPlugin {
  id: string;
  version: string;
  
  project: string;
  installed_at: number;
  source: string;
  
  manifest: string;
}

export interface InstalledPluginList {
  installed: InstalledPlugin[];
  project: string | null;
}


export interface PluginCatalogEntry {
  id: string;
  name: string;
  version: string;
  kinds: string[];
  mode: string;
  desc: string;
  
  path: string;
  installed: boolean;
  
  error: string;
  
  requestedProviderKeys: string[];
}


export interface PluginModeResult {
  id: string;
  mode: string;
  project: string | null;
}


export interface PluginDetail {
  id: string;
  name: string;
  version: string;
  
  project: string;
  has_page: boolean;
  mode: "dev" | "release";
  desc: string;
  
  readme: string;
  
  workflows: string[];
  
  state: string[];
  has_config: boolean;
  requestedProviderKeys: string[];
  config_error?: string;
  
  bot?: PluginBotDecl | null;
}



export interface PluginUninstallResult {

  id: string;
  project: string;
  removed: string[];
}


export interface PluginScanResult {
  plugins: { id: string; name?: string; path: string; kinds?: string[];
             version?: string; desc?: string; error?: string }[];
  skills: { name: string; display?: string; path: string }[];
  tools: { name: string; display?: string; path: string;
           
           unit?: "dir" | "file"; desc?: string; scope?: string;
           error?: string;
           
           requestedProviderKeys?: string[];
           
           config_error?: string }[];
  dev: { id: string; name?: string; path: string; kinds?: string[];
         version?: string; desc?: string;
         
         mode?: string;
         registered?: boolean; errors?: string[]; error?: string;
         
         requestedProviderKeys?: string[];
         
         config_error?: string }[];
}



export interface ProjectUiPrefs {
  hiddenPluginProjects?: boolean;
  hiddenWorkflows?: boolean;
}


export const MASKED_PLUGIN_SECRET = "••••";
