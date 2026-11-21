
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { ArtifactList } from "./ArtifactList";
import { ArtifactMain } from "../../kernel/ui/artifacts/ArtifactMain";
import { useScopedState } from "../../kernel/ui/useScopedState";
import { FileCtxMenu } from "./FileCtxMenu";
import type { FileCtxMenu as CtxMenuState } from "../../kernel/ui/artifacts/types";
import { useArtifactLayout } from "./useArtifactLayout";
import { useFileTree } from "./useFileTree";
import { useArtifactData } from "./useArtifactData";
import { useArtifactTabs } from "./useArtifactTabs";
import { useSubAgents } from "./useSubAgents";
import { SubAgentCard } from "../../kernel/ui/chat/SubAgentCard";

interface Props {
  project: string;
  title?: string;
  onClose: () => void;
  showList: boolean;
  setShowList: (v: boolean) => void;
  showMain: boolean;
  setShowMain: (v: boolean) => void;
  
  scope: string;
  
  renderWorkflowRun?: (t: { runId: string; workflow: string; project: string }) => ReactNode;
}

export function ArtifactsPanel({ project, onClose, showList, setShowList,
                                showMain, setShowMain, scope,
                                renderWorkflowRun }: Props) {
  const [urlInput, setUrlInput] = useState("");
  const [showUrlBar, setShowUrlBar] = useState(false);
  const [ctxMenu, setCtxMenu] = useState<CtxMenuState | null>(null);
  
  const [listTab, setListTab] = useScopedState<"recent" | "files">(scope, "art.listTab", "recent");
  
  const sessionId = scope.startsWith("sess:") ? scope.slice(5) : "";
  const realSid = sessionId === "__new__" ? "" : sessionId;

  const layout = useArtifactLayout(scope, showList, showMain);
  const tree = useFileTree(scope);
  const data = useArtifactData(project, listTab, tree);
  const tabState = useArtifactTabs(project, () => setShowMain(true), scope);
  const subAgents = useSubAgents(realSid, project);

  
  
  const curSubId = tabState.cur?.kind === "subagent" ? tabState.cur.subagentId : undefined;
  useEffect(() => {
    if (curSubId && !subAgents.detailOf(curSubId)) void subAgents.toggle(curSubId);
    
  }, [curSubId]);
  const subDetail = curSubId ? subAgents.detailOf(curSubId) : undefined;
  const subAgentView = subDetail ? (
    <SubAgentCard sa={subDetail} active onToggle={() => {}}
      onQuery={(id) => subAgents.toggle(id)}
      onStop={subDetail.status === "running"
        ? (id) => subAgents.stop(id) : undefined} />
  ) : <div className="dim pad8">加载子 Agent 会话…</div>;

  
  const curWfRun = tabState.cur?.kind === "workflow-run" ? tabState.cur : undefined;
  const workflowRunView = curWfRun && renderWorkflowRun
    ? renderWorkflowRun({ runId: curWfRun.runId ?? "",
        workflow: curWfRun.workflow ?? "",
        project: curWfRun.project || project })
    : null;

  
  useEffect(() => {
    if (!ctxMenu) return;
    const close = () => setCtxMenu(null);
    window.addEventListener("click", close);
    window.addEventListener("contextmenu", close);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("contextmenu", close);
    };
  }, [ctxMenu]);

  
  
  
  
  
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey) || e.key.toLowerCase() !== "s") return;
      const t = tabState.cur;
      const editable = !!t && (t.kind === "code" || t.kind === "md");
      if (!editable) return;
      e.preventDefault();
      e.stopPropagation();
      if (t!.dirty) tabState.saveTab(t!.key);
    };
    window.addEventListener("keydown", onKey, true);   
    return () => window.removeEventListener("keydown", onKey, true);
  }, [tabState]);

  if (!showList && !showMain) return null;

  return (
    <aside className="art-panel">
      <div className="art-body">
        {}
        {(showList || showMain) && (
          <div className="art-edge" onMouseDown={layout.onLeftEdgeDrag} title="拖动调节面板宽度">
            <span className="art-drag-bar" />
          </div>
        )}
        {showList && (
          <ArtifactList
            project={project} width={layout.listW} onRefresh={data.refresh}
            sessionId={realSid} subAgents={subAgents}
            treeError={tree.error} treeLoading={tree.loading}
            purgeTrash={data.purgeTrash}
            files={data.files} reports={data.reports}
            listTab={listTab} setListTab={setListTab}
            fileTree={tree.tree} expandedDirs={tree.expandedDirs}
            toggleDir={(p: string) => tree.toggleDir(project, p)}
            openFile={tabState.openFile} setCtxMenu={setCtxMenu}
            showSnaps={data.showSnaps} setShowSnaps={data.setShowSnaps}
            cks={data.cks} setCks={data.setCks} />
        )}
        {}
        {showList && showMain && (
          <div className="art-edge" onMouseDown={layout.onListDrag} title="拖动调节产出物栏宽度">
            <span className="art-drag-bar" />
          </div>
        )}
        {showMain && (
          <div className="art-main" style={{ width: layout.mainW, flex: "0 0 auto" }}>
            <ArtifactMain
              tabs={tabState.tabs} cur={tabState.cur} active={tabState.active}
              setActive={tabState.setActive}
              closeTab={tabState.closeTab} patchTab={tabState.patchTab}
              saveTab={tabState.saveTab}
              urlInput={urlInput} setUrlInput={setUrlInput}
              showUrlBar={showUrlBar} setShowUrlBar={setShowUrlBar}
              openUrl={() => {
                if (tabState.openUrl(urlInput)) setUrlInput("");
              }}
              subAgentView={subAgentView} workflowRunView={workflowRunView} />
          </div>
        )}
        {}
        {showMain && (
          <div className="art-edge" onMouseDown={layout.onRightEdgeDrag}
               title="拖动调节多功能栏宽度">
            <span className="art-drag-bar" />
          </div>
        )}
      </div>
      {ctxMenu && (
        <FileCtxMenu menu={ctxMenu} project={project}
                     onDone={data.refresh} onClose={() => setCtxMenu(null)} />
      )}
    </aside>
  );
}
