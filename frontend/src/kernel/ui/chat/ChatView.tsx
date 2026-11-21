
import type { AppConfig, ProjectNode, SessionSummary } from "../../api";
import { collectPaths } from "../../project/projectTree";
import { TodoPanel } from "./TodoPanel";
import { ChatPanel } from "./ChatPanel";
import { Icon } from "../icons";
import type { ChatStream } from "./useChatStream";
import type { SessionPrefs } from "../../chat/sessionPrefs";
import { baseName } from "../format";

interface Props {
  chat: ChatStream;
  config: AppConfig | null;
  modelSel: string;
  setModelSel: (v: string) => void;
  
  prefs?: SessionPrefs;
  onPlanChange?: (v: boolean) => void;
  projTree: ProjectNode | null;
  curProject: string;
  curId: string | null;
  sessions: SessionSummary[];
  onOpenProject: (path: string) => void;
  showSidebar: boolean;
  setShowSidebar: (v: boolean) => void;
  showArtifacts: boolean;
  setShowArtifacts: (v: boolean) => void;
  showArtList: boolean;
  setShowArtList: (v: boolean) => void;
  showArtMain: boolean;
  setShowArtMain: (v: boolean) => void;
  showDebug: boolean;
  setShowDebug: (v: boolean) => void;
  swapLayout: boolean;
  setSwapLayout: (v: boolean) => void;
  chatMaxWidth: number;
}

export function ChatView({
  chat, modelSel, setModelSel, prefs, onPlanChange, config: appConfig, projTree, curProject, curId, sessions,
  onOpenProject, showSidebar, setShowSidebar, showArtifacts, setShowArtifacts,
  showArtList, setShowArtList, showArtMain, setShowArtMain, showDebug, setShowDebug,
  swapLayout, setSwapLayout, chatMaxWidth,
}: Props) {
  
  
  const wfSel = prefs?.workflow ?? "";

  return (
    <>
      <div className="art-topbar-inline">
        <button className={`icon-btn ${showSidebar ? "on" : ""}`} title="侧栏"
          onClick={() => setShowSidebar(!showSidebar)}><Icon name="folder" /></button>
        {projTree && projTree.children.length > 0 && (
          !curProject ? (
            <select className="topbar-proj" value={curProject} onChange={(e) => onOpenProject(e.target.value)}
              title="选择当前项目（选定后任务归属此项目，不可更改）">
              <option value="">— 项目 —</option>
              {collectPaths(projTree).map((p) => {
                const parts = p.split("/");
                return <option key={p} value={p}>{"  ".repeat(parts.length - 1)}{parts[parts.length - 1]}</option>;
              })}
            </select>
          ) : curId ? (
            <span className="topbar-proj-fixed" title="项目已固定"><Icon name="folder" /> {baseName(curProject)}</span>
          ) : (
            <select className="topbar-proj" value={curProject} onChange={(e) => onOpenProject(e.target.value)}
              title="选择当前项目或子项目">
              {collectPaths(projTree).filter((p) => p === curProject || p.startsWith(curProject + "/")).map((p) => {
                const parts = p.split("/");
                return <option key={p} value={p}>{"  ".repeat(parts.length - 1)}{parts[parts.length - 1]}</option>;
              })}
            </select>
          )
        )}
        <span className="art-topbar-title">{sessions.find((s) => s.id === curId)?.title || "产出物"}</span>
        <span className="flex1" />
        <button className={`icon-btn ${showArtList ? "on" : ""}`} title="产出物列表栏"
          onClick={() => setShowArtList(!showArtList)}><Icon name="list" /></button>
        <button className={`icon-btn ${showArtMain ? "on" : ""}`} title="多功能展示栏"
          onClick={() => setShowArtMain(!showArtMain)}>🖥</button>
        <button className={`icon-btn ${showDebug ? "on" : ""}`} title="Debug 信息"
          onClick={() => setShowDebug(!showDebug)}>🐛</button>
        <button className={`icon-btn ${swapLayout ? "on" : ""}`} title="交换布局"
          onClick={() => setSwapLayout(!swapLayout)}>🔄</button>
      </div>
      <TodoPanel todos={chat.todos} />
      <ChatPanel
        project={curProject}
        chat={chat}
        sessionId={curId}
        modelSel={modelSel}
        setModelSel={setModelSel}
        outerConfig={appConfig}
        onPlanChange={onPlanChange}
        prefs={prefs}
        workflow={wfSel}
        showArtifacts={showArtifacts}
        setShowArtifacts={setShowArtifacts}
        maxWidth={chatMaxWidth}
      />
    </>
  );
}
