


export type TimerOwner = "backend" | "frontend";


export type TimerAction = "session" | "workflow";


export type TimerKind = "every" | "cron";


export interface TimerSessionPayload {
  project: string;
  prompt: string;
  title?: string;
  model?: string;
}


export interface TimerWorkflowPayload {
  project: string;
  workflow: string;
  inputs?: Record<string, unknown>;
}


export interface TimerJob {
  name: string;
  owner: TimerOwner;
  action: TimerAction;
  kind: TimerKind;
  spec: string;
  payload: TimerSessionPayload | TimerWorkflowPayload;
  enabled: boolean;
  updated_at: number;
  
  nextRunAt: number | null;
  
  invalid?: boolean;
}


export interface TimerInput {
  name: string;
  owner: TimerOwner;
  action: TimerAction;
  kind: TimerKind;
  spec: string;
  payload: Record<string, unknown>;
  enabled?: boolean;
}
