
export type AppView =
  | { kind: "home" }             
  | { kind: "chat" }
  | { kind: "workflow"; project: string; name: string }
  | { kind: "workflows" }          
  | { kind: "project"; path: string }  
  | { kind: "plugin"; project: string; id: string }  
  | { kind: "bot"; project: string; id: string };  

