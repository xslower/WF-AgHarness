

export interface PickRunProjectArgs {
  
  lastProject: string;
  
  current: string;
  
  all: string[];
}


export function pickRunProject({ lastProject, current, all }: PickRunProjectArgs): string {
  if (lastProject && all.includes(lastProject)) return lastProject;
  if (current && all.includes(current)) return current;
  return all[0] ?? "";
}
