

export interface ModelSchedule {
  days: number[]; 
  start: string; 
  end: string;
}

export interface ModelInfo {
  id: string;
  kind: string; 
  
  wireId?: string;
  free: boolean;
  disabled?: boolean; 
  contextLength: number;
  supportsThinking: boolean;
  supportsImages: boolean;
  inputPrice: number;
  outputPrice: number;
  description?: string;
  schedules?: ModelSchedule[]; 
}

export interface Provider {
  id: string;
  name: string;
  baseUrl: string;
  apiKey: string;
  
  kind?: string;
  
  adapter?: string;
  note?: string;
  imported?: boolean;
  
  pluginId?: string;
  dailyFreeQuota?: number;
  
  cooldownSec?: number;
  models: ModelInfo[];
}

export interface Settings {
  
  
  workspaceRoot: string;
  defaultEffort: string;
  contextWarnRatio: number;
  envPython: string;
  envNode: string;
  projectsRoot?: string;
  
  runtimeDir?: string;
  promptPrefix?: string;
  promptSuffix?: string;
  promptTemplateMode?: string;
  quickSuggestions?: boolean;
  
  notifyOnSessionDone?: boolean;
  
  trashEnabled?: boolean;
  
  trashRetentionDays?: number;
  
  escalateFileLimit?: number;
  
  maxToolRounds?: number;
  
  wfChatRetentionDays?: number;
  
  commandDenyPatterns?: string[];
  commandAllowPatterns?: string[];
  
  policyExtraSafePaths?: string[];
  
  wfMaxConcurrency?: number;
  
  compactStrategies?: string[];
  
  compactSummaryMode?: string;
  
  compactUserMsgLimit?: number;
  
  summaryHedgeMs?: number;
}

export interface TimeWindow {
  start: string;
  end: string;
}

export interface ModelQueues {
  parent: string[];
  child: string[];
  
  summary: string[];
  
  schedules?: Record<string, TimeWindow[]>;
}

export interface UtilityModels {
  completion: string[];
  classify: string[];
  review: string[];
  suggest: string[];
}

export interface AppConfig {
  providers: Provider[];
  queues: ModelQueues;
  utility?: UtilityModels;
  settings: Settings;
}

export interface TestResult {
  
  ok: boolean | null;
  ms?: number;
  first_token_ms?: number | null;
  sample?: string;
  error?: string;
  
  skipped?: boolean;
  kind?: string;
}
