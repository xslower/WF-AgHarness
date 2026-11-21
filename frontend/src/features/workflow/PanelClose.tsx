
export function PanelClose({ onClose, title = "关闭面板" }: {
  onClose: () => void;
  title?: string;
}) {
  return (
    <button type="button" className="wf-panel-close" title={title}
      onClick={(e) => { e.stopPropagation(); onClose(); }}>✕</button>
  );
}
