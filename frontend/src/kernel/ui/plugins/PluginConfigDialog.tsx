
import { Modal } from "../Modal";
import { PluginConfigForm } from "./PluginConfigForm";

export interface ConfigTarget {
  
  id: string;
  
  name?: string;
  
  project?: string;
  
  where?: string;
}

interface Props {
  target: ConfigTarget | null;
  onClose: () => void;
  onSaved?: () => void;
}

export function PluginConfigDialog({ target, onClose, onSaved }: Props) {
  if (!target) return null;
  return (
    <Modal
      title={`配置 · ${target.name || target.id}`}
      subtitle={target.where ?? "加密保存在系统 agent.db（插件通过 plugin.config() 读）"}
      onClose={onClose}
      width={560}
    >
      <PluginConfigForm pluginId={target.id} project={target.project ?? ""}
        onSaved={onSaved} />
    </Modal>
  );
}
