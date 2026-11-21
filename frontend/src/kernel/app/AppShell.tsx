
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { AppView } from "./view";
import { events } from "../api/eventBridge";
import { SpaceAuditPanel, useSpaceAudit } from "../space/SpaceAudit";
import { DialogHost } from "../ui/DialogHost";
import { useAppData } from "./useAppData";
import { useExpansion } from "./useExpansion";
import { useRestoreFromUrl, useSyncUrl } from "./useUrlRoute";
import { useScopedState } from "../ui/useScopedState";
import { scopedStore } from "../ui/scopedStore";
import { useSessionChoice } from "./useSessionChoice";
import { viewScope } from "../chat/chatSessionStore";
import { useSessionLifecycle } from "./useSessionLifecycle";
import { useThemePlugins } from "../theme/useThemePlugins";
import { useChatStream } from "../ui/chat/useChatStream";
import { ChatView } from "../ui/chat/ChatView";
import { useAttention } from "../attention/useAttention";
import { DebugPanel } from "../ui/chat/DebugPanel";
import { UsagePanel } from "../ui/chat/UsagePanel";
import { ChatFloat } from "../ui/chat/ChatFloat";
import { Sidebar } from "../../features/sidebar/Sidebar";
import { ArtifactsPanel } from "../../features/artifacts/ArtifactsPanel";
import { renderWorkflowRunTab } from "../../features/workflow/renderWorkflowRunTab";
import { SettingsPanel } from "../../features/settings/SettingsPanel";
import { WorkflowEditor } from "../../features/workflow/WorkflowEditor";
import { GlobalWorkflowsPanel } from "../../features/workflow/GlobalWorkflows";
import { ProjectHome } from "../../features/project/ProjectHome";
import { PluginDetailPage } from "../../features/project/PluginDetailPage";
import { BotPage } from "../../features/project/BotPage";
import { HomeView } from "../../features/home/HomeView";



export default function AppShell() {
  const data = useAppData();
  const expansion = useExpansion(data.projTree, data.refreshWfs);

  
  
  const [view, setView] = useState<AppView>({ kind: "home" });

  const { themeId, setThemeId, registry, theme } = useThemePlugins();
  const [showSettings, setShowSettings] = useState(false);
  const [showUsage, setShowUsage] = useState(false);
  const spaceAudit = useSpaceAudit();

  
  useEffect(() => { scopedStore.prune(); }, []);

  
  
  useEffect(() => {
    const refresh = () => { void data.refreshTree(); };
    window.addEventListener("harness:refresh-tree", refresh);
    return () => window.removeEventListener("harness:refresh-tree", refresh);
  }, [data.refreshTree]);



  
  useEffect(() => { events.connect(); }, []);

  
  
  const chatRef = useRef<{
    loadSession: (s: Awaited<ReturnType<typeof api.getSession>>) => void;
    reset: () => void;
  } | null>(null);

  const choice = useSessionChoice({ config: data.config, chatRef });

  
  const scope = viewScope(choice.curId);
  const [showArtifacts, setShowArtifacts] = useScopedState(scope, "ui.showArtifacts", true);
  const [showArtList, setShowArtList] = useScopedState(scope, "ui.showArtList", true);
  const [showArtMain, setShowArtMain] = useScopedState(scope, "ui.showArtMain", true);
  const [showDebug, setShowDebug] = useScopedState(scope, "ui.showDebug", false);
  
  
  const [showSidebar, setShowSidebar] = useScopedState(scope, "ui.showSidebar", true);
  const [swapLayout, setSwapLayout] = useScopedState(scope, "ui.swapLayout", false);

  const chat = useChatStream({
    project: choice.curProject,
    sessionId: choice.curId,
    setSessionId: choice.setCurId,
    refreshSessions: data.refreshSessions,
    modelSel: choice.modelSel,
    notifyOnDone: data.config?.settings.notifyOnSessionDone,
  });
  chatRef.current = { loadSession: chat.loadSession, reset: chat.reset };

  
  
  const attn = useAttention(choice.curId);

  useRestoreFromUrl({
    setView,
    setCurProject: choice.setCurProject,
    setCurId: choice.setCurId,
    loadSession: chat.loadSession,
  });
  useSyncUrl({ view, curProject: choice.curProject, curId: choice.curId });

  
  const latest = useRef({ chat, attn, curId: choice.curId });
  latest.current = { chat, attn, curId: choice.curId };

  
  const lifecycle = useSessionLifecycle({
    curId: choice.curId,
    dropSession: chat.dropSession,
    resetChat: chat.reset,
    setCurId: choice.setCurId,
    resetForNewSession: choice.resetForNewSession,
    refreshSessions: data.refreshSessions,
  });
  const { newSessionFor } = lifecycle;

  
  const openSession = useCallback((id: string) => {
    setView({ kind: "chat" });
    void choice.openSession(id);
  }, [choice.openSession]);

  const openProject = useCallback((path: string) => {
    choice.setCurProject(path);
    choice.setCurId(null);
    latest.current.chat.reset();
    expansion.toggleExpand(path);
    void data.refreshWfs(path);
    
    
    setView({ kind: "project", path });
  }, [choice.setCurProject, choice.setCurId, expansion.toggleExpand,
      data.refreshWfs, setView]);

  const newSession = useCallback((id: string, project: string) => {
    setView({ kind: "chat" });
    choice.resetForNewSession(id, project);
  }, [choice.resetForNewSession]);

  
  const openWorkflow = useCallback((project: string, name: string) => {
    const a = latest.current.attn;
    setView({ kind: "workflow", project, name });
    for (const r of a.snapshot.sessions) {
      if (r.kind === "workflow" && r.origin === name
          && (r.project || "") === (project || "")) {
        a.markSidSeen(r.id);
      }
    }
  }, []);

  const deleteSession = lifecycle.deleteSession;

  const openSettings = useCallback(() => {
    setShowSettings(true);
    void data.refreshConfig();
  }, [data.refreshConfig]);

  const showChat = view.kind === "chat";
  const showHome = view.kind === "home";
  const showGlobalWf = view.kind === "workflows";
  const showProject = view.kind === "project";

  const sessionTitle = data.sessions.find((s) => s.id === choice.curId)?.title || undefined;
  
  
  const artifactSlot = (
    <ArtifactsPanel project={choice.curProject} title={sessionTitle}
      scope={scope}
      onClose={() => setShowArtifacts(false)}
      showList={showArtList} setShowList={setShowArtList}
      showMain={showArtMain} setShowMain={setShowArtMain}
      renderWorkflowRun={renderWorkflowRunTab} />
  );

  return (
    <div className="layout">
      {showSidebar && (
        <Sidebar
          sessions={data.sessions} projTree={data.projTree} wfs={data.wfs}
          expanded={expansion.expanded}
          curProject={choice.curProject} curId={choice.curId} view={view}
          scope={scope} config={data.config}
          onShowUsage={() => setShowUsage(true)}
          onExpand={expansion.expand} onToggleExpand={expansion.toggleExpand}
          onToggleAll={expansion.toggleAll}
          onOpenProject={openProject} onOpenSession={openSession}
          onOpenPlugin={(proj, id) =>
            setView({ kind: "plugin", project: proj, id })}
          onOpenWorkflow={openWorkflow}
          onNewSession={newSession} onDeleteSession={deleteSession}
          onOpenSettings={openSettings}
          onOpenGlobalWorkflows={() => setView({ kind: "workflows" })}
          onOpenHome={() => setView({ kind: "home" })}

          refreshSessions={data.refreshSessions} refreshTree={data.refreshTree}
          refreshWfs={data.refreshWfs}
          attnOf={attn.of} attnOfFlow={attn.ofFlow}
        />
      )}

      {swapLayout && showArtifacts && showChat && artifactSlot}

      <main className="chat">
        {showHome ? (
          <HomeView
            projTree={data.projTree}
            onOpenProjectHome={(p) => setView({ kind: "project", path: p })}
            onOpenWorkflow={openWorkflow}
            onNewSession={(p) => void newSessionFor(p)}
          />
        ) : showProject ? (
          <ProjectHome
            path={(view as { kind: "project"; path: string }).path}
            onBack={() => setView({ kind: "chat" })}
            onOpenProject={(p) => setView({ kind: "project", path: p })}
            onOpenSession={openSession}
            onNewSession={(p) => void newSessionFor(p)}
            onOpenWorkflow={openWorkflow}
            onOpenPlugin={(proj, id) => setView({ kind: "plugin", project: proj, id })}
            onOpenBot={(proj, id) => setView({ kind: "bot", project: proj, id })}
          />
        ) : view.kind === "bot" ? (
          <BotPage hostProject={view.project} pluginId={view.id}
            onBack={() => setView({ kind: "project", path: view.project })} />
        ) : view.kind === "plugin" ? (
          <PluginDetailPage
            hostProject={view.project} pluginId={view.id}
            onBack={() => setView({ kind: "project", path: view.project })}
            onOpenWorkflow={openWorkflow}
          />
        ) : showGlobalWf ? (
          <GlobalWorkflowsPanel
            onBack={() => setView({ kind: "chat" })}
            onOpenWorkflow={openWorkflow}
          />
        ) : showChat ? (
          <ChatView
            chat={chat} config={data.config} modelSel={choice.modelSel}
            setModelSel={choice.changeModel}
            prefs={choice.curPrefs}
            onPlanChange={choice.changePlan}
            projTree={data.projTree} curProject={choice.curProject} curId={choice.curId}
            sessions={data.sessions} onOpenProject={openProject}
            showSidebar={showSidebar} setShowSidebar={setShowSidebar}
            showArtifacts={showArtifacts} setShowArtifacts={setShowArtifacts}
            showArtList={showArtList} setShowArtList={setShowArtList}
            showArtMain={showArtMain} setShowArtMain={setShowArtMain}
            showDebug={showDebug} setShowDebug={setShowDebug}
            swapLayout={swapLayout} setSwapLayout={setSwapLayout}
            chatMaxWidth={theme.layout.chatMaxWidth}
          />
        ) : (
          <WorkflowEditor project={view.project} name={view.name}
            onBack={() => setView({ kind: "chat" })}
            onChanged={() => void data.refreshWfs(view.project)}
            onOpenWorkflow={openWorkflow} />
        )}
      </main>

      {showDebug && (
        <DebugPanel logs={chat.debugLogs} onClear={chat.clearDebugLogs}
          onClose={() => setShowDebug(false)} />
      )}
      {showUsage && <UsagePanel onClose={() => setShowUsage(false)} />}
      {spaceAudit.issues && (
        <SpaceAuditPanel issues={spaceAudit.issues} onClose={spaceAudit.close} />
      )}

      {!swapLayout && showArtifacts && showChat && artifactSlot}

      {}
      {!showChat && <ChatFloat chat={chat} />}
      {}
      <DialogHost />

      {showSettings && data.config && (
        <SettingsPanel config={data.config} onClose={() => setShowSettings(false)}
          onSaved={async (c) => { data.setConfig(c); }}
          uiPluginId={themeId} setUiPluginId={setThemeId}
          themes={registry.all()} />
      )}
    </div>
  );
}
