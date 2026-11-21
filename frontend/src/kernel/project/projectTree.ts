
import type { ProjectNode } from "../api";

export function collectPaths(node: ProjectNode, acc: string[] = []): string[] {
  acc.push(node.path);
  node.children.forEach((c) => collectPaths(c, acc));
  return acc;
}
