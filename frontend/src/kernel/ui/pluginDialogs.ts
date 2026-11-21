
import { confirmDialog } from "./dialog";


export function confirmDeletePlugin(name: string): Promise<boolean> {
  return confirmDialog({
    title: "删除插件",
    danger: true,
    okText: "删除",
    message: `确认删除插件「${name}」？\n会把插件目录移到回收站（可手工找回），需要重启后端生效。`,
  });
}
