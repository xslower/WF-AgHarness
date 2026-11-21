
export interface SubAgentOpenRequest {
  id: string;
  task: string;
  
  sessionId?: string;
}

let opener: ((req: SubAgentOpenRequest) => void) | null = null;

export function bindSubAgentOpener(fn: ((req: SubAgentOpenRequest) => void) | null): void {
  opener = fn;
}

export function openSubAgentTab(req: SubAgentOpenRequest): void {
  opener?.(req);
}
