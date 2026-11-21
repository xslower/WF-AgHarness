

export type SlotId =
  | "sidebar.footer"
  | "chat.aside"
  | "artifacts.tab"
  | "settings.section";

export interface ThemeTokens {
  bg: string;
  bg2: string;
  panel: string;
  panel2: string;
  border: string;
  border2: string;
  text: string;
  dim: string;
  accent: string;
  accent2: string;
  ok: string;
  warn: string;
  err: string;
  fontFamily: string;
  fontMono: string;
  fontSize: number;
  radius: number;
  borderWidth: number;
  spaceUnit: number;
  shadow: string;
}

export interface ThemeLayout {
  sidebarWidth: number;
  artListWidth: number;
  chatMaxWidth: number;
  density: "compact" | "cozy" | "comfortable";
  preset: "classic" | "split" | "focus";
}

export interface ThemeManifest {
  id: string;
  name: string;
  description: string;
  tokens: ThemeTokens;
  layout: ThemeLayout;
  
  version?: string;
  
  source?: string;
}


export interface ExternalThemeManifest
  extends Omit<ThemeManifest, "tokens" | "layout"> {
  tokens?: Partial<ThemeTokens>;
  layout?: Partial<ThemeLayout>;
}

export interface ThemeListResponse {
  themes: ExternalThemeManifest[];
}

export type PluginLevel = "declarative" | "behavioral";

export interface PluginMeta {
  id: string;
  name: string;
  version: string;
  apiVersion: number;
  kinds: string[];
  level: PluginLevel;
  permissions: string[];
  builtin: boolean;
}

export interface SlotContribution {
  id: string;
  slot: SlotId;
  order?: number;
  render: () => React.ReactNode;
}
