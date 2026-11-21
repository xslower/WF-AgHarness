


export interface ProjectPolicyMode {
  value: string;
  label: string;
  hint: string;
}

export interface ProjectPolicy {
  
  mode: string;
  
  default: string;
  
  modes: ProjectPolicyMode[];
  
  always: string;
}
