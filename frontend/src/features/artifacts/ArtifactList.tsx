
import type { ArtifactFile, Checkpoint } from "../../kernel/api";
import type { SubAgentList } from "./useSubAgents";
import { SnapshotPanel } from "./SnapshotPanel";
import { SubAgentPanel } from "./SubAgentPanel";
import { baseName } from "../../kernel/ui/artifacts/files";
import { fmtSize } from "../../kernel/ui/format";
import type { TreeNode } from "./useFileTree";
import type { FileCtxMenu } from "../../kernel/ui/artifacts/types";
import { Icon } from "../../kernel/ui/icons";
import { normSlashes } from "./eventRefresh";


const SUPPORTED_EXTS = /^(py|js|ts|tsx|jsx|node|md|txt|html|css|json|csv|xml|yaml|yml|toml|ini|sh|sql|png|jpe?g|gif|webp|bmp|svg|mp4|webm|ogg|mov|avi|mkv)$/i;
function isSupportedFile(name: string): boolean {
  const ext = name.split(".").pop();
  return !!ext && SUPPORTED_EXTS.test(ext);
}


function relOf(project: string, p: string): string {
  
  
  const root = normSlashes(project);
  const full = normSlashes(p);
  if (!root) return full;
  if (full === root) return baseName(full);
  return full.startsWith(`${root}/`) ? full.slice(root.length + 1) : full;
}

interface Props {
  project: string;
  width: number;
  files: ArtifactFile[];
  reports: ArtifactFile[];
  listTab: "recent" | "files";
  setListTab: (v: "recent" | "files") => void;
  
  sessionId?: string;
  
  subAgents: SubAgentList;
  onRefresh: () => void;
  
  purgeTrash: () => void;
  fileTree: TreeNode[];
  
  treeError?: string;
  
  treeLoading?: boolean;
  expandedDirs: Set<string>;
  toggleDir: (path: string) => void;
  openFile: (f: { path: string; name: string; size: number }) => void;
  setCtxMenu: (m: FileCtxMenu | null) => void;
  showSnaps: boolean;
  setShowSnaps: (v: boolean) => void;
  cks: Checkpoint[];
  setCks: (v: Checkpoint[]) => void;
}

export function ArtifactList({
  project, width, files, reports, listTab, setListTab, sessionId, subAgents, onRefresh, purgeTrash, fileTree,
  treeError = "", treeLoading = false,
  expandedDirs, toggleDir, openFile, setCtxMenu, showSnaps, setShowSnaps, cks, setCks,
}: Props) {
  
  const renderItem = (f: ArtifactFile) => (
    <div key={f.path} className="art-item" title={f.name} onClick={() => openFile(f)}>
      <span className="art-name">
        {/\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(f.name) ? "🖼 " : /\.(mp4|webm|ogg|mov|avi|mkv)$/i.test(f.name) ? "🎬 " : /\.md$/i.test(f.name) ? "📘 " : "📄 "}{baseName(f.name)}
      </span>
      <span className="dim">{fmtSize(f.size)}</span>
    </div>
  );

  const renderFileNode = (node: TreeNode, depth: number) => {
    
    const name = node.name ?? "";
    if (name.startsWith(".")) return null;
    
    if (!node.isDir && !isSupportedFile(name)) return null;
    const isImg = /\.(png|jpe?g|gif|webp|bmp)$/i.test(name);
    const isMd = /\.md$/i.test(name);
    const icon = node.isDir ? (expandedDirs.has(node.path) ? "▾" : "▸") : isImg ? "🖼" : isMd ? "📘" : "📄";
    
    const tip = relOf(project, node.path);
    return (
      <div key={node.path}>
        <div className="art-item" style={{ paddingLeft: depth * 14 }} title={tip}
          onClick={() => node.isDir ? toggleDir(node.path) : openFile({ path: node.path, name, size: 0 })}
          onContextMenu={(e) => { e.preventDefault(); e.stopPropagation(); setCtxMenu({ x: e.clientX, y: e.clientY, path: node.path, name, isDir: !!node.isDir }); }}>
          <span className="art-name">{icon} {name}</span>
        </div>
        {node.isDir && expandedDirs.has(node.path) && node.children?.map((c) => renderFileNode(c, depth + 1))}
      </div>
    );
  };

  return (
    <div className="art-list" style={{ width, minWidth: 180 }}>
      {!project && <div className="dim pad8">选择项目后显示该项目产出物</div>}
      {project && (
        <>
          <div className="list-tabs">
            <button className={listTab === "recent" ? "active" : ""} onClick={() => setListTab("recent")}>最近</button>
            <button className={listTab === "files" ? "active" : ""} onClick={() => setListTab("files")}>文件</button>
            <button className="link" title="刷新：重新加载产出物与文件树" onClick={onRefresh}>🔄</button>
            <button className="link" title="清理回收站（项目内 .trash）" onClick={purgeTrash}><Icon name="trash" /></button>
          </div>
          {listTab === "recent" ? (
          <>
          <div className="q-title">最近文件</div>
          {files.filter((f) => !f.name.startsWith(".") && isSupportedFile(f.name)).map(renderItem)}
          {!files.filter((f) => !f.name.startsWith(".") && isSupportedFile(f.name)).length && <div className="dim">暂无</div>}
          {reports.filter((f) => !f.name.startsWith(".") && isSupportedFile(f.name)).length > 0 && <div className="q-title">工作流报告</div>}
          {reports.filter((f) => !f.name.startsWith(".") && isSupportedFile(f.name)).map(renderItem)}
          </>
          ) : (
          <div className="file-tree">
            {fileTree.map((n) => renderFileNode(n, 0))}
            {}
            {!fileTree.length && (
              treeError
                ? <div className="dim" title={treeError}>加载失败：{treeError}</div>
                : treeLoading ? <div className="dim">加载中…</div>
                  : <div className="dim">暂无文件</div>
            )}
          </div>
          )}
          <SnapshotPanel
            project={project} showSnaps={showSnaps} setShowSnaps={setShowSnaps}
            cks={cks} setCks={setCks} />
          {}
          {sessionId && <SubAgentPanel ctl={subAgents} />}
        </>
      )}
    </div>
  );
}
