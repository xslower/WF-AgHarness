
import { Icon } from "../../kernel/ui/icons";
import type { FileCtxMenu as CtxMenuState } from "../../kernel/ui/artifacts/types";
import { useFileCtxActions } from "./useFileCtxActions";

interface Props {
  menu: CtxMenuState;
  project: string;
  
  onDone: () => void;
  onClose: () => void;
}

export function FileCtxMenu({ menu, project, onDone, onClose }: Props) {
  const a = useFileCtxActions(project, onDone);

  return (
    <div className="ctx-menu" style={{ left: menu.x, top: menu.y }} onClick={onClose}>
      <div className="ctx-item" onClick={() => void a.remove(menu.path, menu.name)}>
        <Icon name="trash" /> 移到回收站
      </div>
      <div className="ctx-item" onClick={() => void a.rename(menu.path, menu.name)}>
        <Icon name="pencil" /> 重命名
      </div>
      <div className="ctx-item" onClick={() => a.cut(menu.path)}>✂ 剪切</div>
      <div className="ctx-item" onClick={() => a.copy(menu.path)}><Icon name="copy" /> 复制</div>
      {a.clipboard && (
        <div className="ctx-item" onClick={() => void a.paste(menu)}>📌 粘贴</div>
      )}
    </div>
  );
}
