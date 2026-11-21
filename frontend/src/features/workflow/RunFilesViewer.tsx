
import type { WfRunFile } from "../../kernel/api";
import { ArtifactMain } from "../../kernel/ui/artifacts/ArtifactMain";
import { fmtSize } from "../../kernel/ui/format";
import { useRunFileTabs } from "./useRunFileTabs";


export function RunFilesViewer({ file, onClose }: {
  
  file: WfRunFile | null;
  onClose: () => void;
}) {
  const v = useRunFileTabs(file);

  if (!file) return null;

  return (
    <div className="wf-files-viewer">
      <div className="wf-files-viewer-head">
        <span className="wf-files-path" title={file.path}>{file.rel || file.name}</span>
        <span className="dim">{fmtSize(file.size)}</span>
        <span className="flex1" />
        <button className="link" onClick={onClose} title="关闭查看器">✕</button>
      </div>
      {v.error && <div className="error pad8">{v.error}</div>}
      <div className="wf-files-viewer-body">
        <ArtifactMain
          tabs={v.tabs} cur={v.cur} active={v.active} setActive={v.setActive}
          closeTab={v.closeTab} patchTab={v.patchTab} saveTab={v.saveTab}
          urlInput={v.urlInput} setUrlInput={v.setUrlInput}
          showUrlBar={v.showUrlBar} setShowUrlBar={v.setShowUrlBar} openUrl={v.openUrl} />
      </div>
    </div>
  );
}
