
import type { ThemeManifest } from "../contracts";
import { classicDark } from "./classicDark";
import { lightModern } from "./lightModern";
import { compactIDE } from "./compactIDE";
import { minimal } from "./minimal";
import { glassmorphism } from "./glassmorphism";
import { retroTerminal } from "./retroTerminal";
import { modernAdmin } from "./modernAdmin";

export const BUILTIN_THEMES: ThemeManifest[] = [
  classicDark,
  lightModern,
  compactIDE,
  minimal,
  glassmorphism,
  retroTerminal,
  modernAdmin,
];
