import { lazy, Suspense, useState, useCallback, useRef } from 'react';
import { BrowserRouter, useLocation } from 'react-router-dom';
import { useChat } from './hooks/useChat';
import { useConversations } from './hooks/useConversations';
import { PreviewProvider, usePreview } from './contexts/PreviewContext';
import { ProjectProvider, useProject } from './contexts/ProjectContext';
import { theme } from './lib/theme';
import { WikiTree } from './components/WikiTree';
import { ContentNav } from './components/ContentNav';
import { PreviewPanel } from './components/PreviewPanel';
import { ChatWindow } from './components/ChatWindow';
import { ProjectHome } from './components/ProjectHome';

const GraphPage = lazy(() => import('./components/GraphPage').then((module) => ({ default: module.GraphPage })));
const WikiBrowser = lazy(() => import('./components/WikiBrowser').then((module) => ({ default: module.WikiBrowser })));
const IngestPanel = lazy(() => import('./components/IngestPanel').then((module) => ({ default: module.IngestPanel })));
const ReviewPanel = lazy(() => import('./components/ReviewPanel').then((module) => ({ default: module.ReviewPanel })));
const DeepResearchPanel = lazy(() => import('./components/DeepResearchPanel').then((module) => ({ default: module.DeepResearchPanel })));
const SettingsPanel = lazy(() => import('./components/SettingsPanel').then((module) => ({ default: module.SettingsPanel })));
const TaskCenter = lazy(() => import('./components/TaskCenter').then((module) => ({ default: module.TaskCenter })));

/** 可拖拽的分隔条 */
function Divider({ onDrag }: { onDrag: (delta: number) => void }) {
  const startRef = useRef<number>(0);
  const [hovered, setHovered] = useState(false);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    startRef.current = e.clientX;

    const handleMouseMove = (ev: MouseEvent) => {
      const delta = ev.clientX - startRef.current;
      startRef.current = ev.clientX;
      onDrag(delta);
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [onDrag]);

  return (
    <div
      style={{
        ...styles.divider,
        backgroundColor: hovered ? theme.accent : theme.border.light,
      }}
      onMouseDown={handleMouseDown}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    />
  );
}

function ProjectWorkspace({ onBack }: { onBack: () => void }) {
  const [leftWidth, setLeftWidth] = useState(240);
  const [rightWidth, setRightWidth] = useState(340);

  const { activeProjectId } = useProject();
  const chat = useChat(activeProjectId);
  const convs = useConversations(activeProjectId);
  const location = useLocation();
  const { previewOpen } = usePreview();

  const path = location.pathname;

  const handleSelectConversation = async (id: string) => {
    const detail = await convs.selectConversation(id);
    if (detail) chat.loadMessages(detail.messages, id);
  };

  const handleNewConversation = () => {
    convs.startNewConversation();
    chat.reset();
  };

  const handleDeleteConversation = async (id: string) => {
    await convs.deleteConversation(id);
    if (convs.activeConversationId === id) chat.reset();
  };

  const handleSendMessage = async (content: string) => {
    await chat.sendMessage(content);
    await convs.loadConversations();
  };

  const handleLeftDrag = useCallback((delta: number) => {
    setLeftWidth((w) => Math.max(180, Math.min(400, w + delta)));
  }, []);

  const handleRightDrag = useCallback((delta: number) => {
    setRightWidth((w) => Math.max(240, Math.min(600, w - delta)));
  }, []);

  const renderContent = () => {
    if (path === '/wiki') return <WikiBrowser />;
    if (path === '/graph') return <GraphPage />;
    if (path === '/ingest') return <IngestPanel />;
    if (path === '/reviews') return <ReviewPanel />;
    if (path === '/research') return <DeepResearchPanel />;
    if (path === '/tasks') return <TaskCenter />;
    if (path === '/settings') return <SettingsPanel />;
    return (
      <ChatWindow
        messages={chat.messages}
        streamingContent={chat.streamingContent}
        isLoading={chat.isLoading}
        sendMessage={handleSendMessage}
        cancelMessage={chat.cancel}
        currentOptions={chat.currentOptions}
        conversations={convs.conversations}
        activeConversationId={convs.activeConversationId}
        conversationId={chat.conversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
      />
    );
  };

  return (
    <div style={styles.root}>
      {/* 左栏：知识树 */}
      <div style={{ ...styles.leftPanel, width: leftWidth, minWidth: leftWidth }}>
        <WikiTree onBack={onBack} />
      </div>

      <Divider onDrag={handleLeftDrag} />

      {/* 中栏：导航 + 内容 */}
      <div style={styles.centerPanel}>
        <ContentNav />
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          <Suspense fallback={<div style={styles.loading}>加载中...</div>}>{renderContent()}</Suspense>
        </div>
      </div>

      {/* 右栏：预览面板 */}
      {previewOpen && (
        <>
          <Divider onDrag={handleRightDrag} />
          <div style={{ ...styles.rightPanel, width: rightWidth, minWidth: rightWidth }}>
            <PreviewPanel />
          </div>
        </>
      )}
    </div>
  );
}

function AppContent() {
  const [inProject, setInProject] = useState(false);

  if (!inProject) {
    return <ProjectHome onEnter={() => setInProject(true)} />;
  }

  return <ProjectWorkspace onBack={() => setInProject(false)} />;
}

export default function App() {
  return (
    <BrowserRouter>
      <ProjectProvider>
        <PreviewProvider>
          <AppContent />
        </PreviewProvider>
      </ProjectProvider>
    </BrowserRouter>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    display: 'flex',
    height: '100vh',
    backgroundColor: theme.bg.window,
    fontFamily: theme.font,
    overflow: 'hidden',
  },
  leftPanel: {
    height: '100vh',
    overflow: 'hidden',
    flexShrink: 0,
  },
  centerPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    minWidth: 0,
    overflow: 'hidden',
  },
  rightPanel: {
    height: '100vh',
    overflow: 'hidden',
    flexShrink: 0,
  },
  divider: {
    width: 3,
    cursor: 'col-resize',
    flexShrink: 0,
    transition: 'background-color 0.15s',
    position: 'relative' as const,
  },
  loading: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: theme.text.tertiary },
};
