
import { api } from "../../kernel/api";
import { tabFromPreview } from "../../kernel/ui/artifacts/files";
import type { Tab } from "../../kernel/ui/artifacts/types";

export async function previewTab(path: string): Promise<Tab> {
  const d = await api.filePreview(path);
  return tabFromPreview(path, d);
}
