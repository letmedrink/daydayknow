import { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, useLocation } from 'react-router-dom';
import { useChat } from './hooks/useChat';
import { useConversations } from './hooks/useConversations';
import { fetchProfile } from './lib/api';
import { NavRail } from './components/NavRail';
import { ConversationPanel } from './components/Sidebar';
import { ChatWindow } from './components/ChatWindow';
import { GraphPage } from './components/GraphPage';
import { ProfilePage } from './components/ProfilePage';
import { WikiBrowser } from './components/WikiBrowser';
import { IngestPanel } from './components/IngestPanel';
import { ReviewPanel } from './components/ReviewPanel';
import { DeepResearchPanel } from './components/DeepResearchPanel';
import { SettingsPanel } from './components/SettingsPanel';
import type { UserProfile } from './types';

function AppContent() {
  const [profile, setProfile] = useState<UserProfile | null>(null);

  const loadProfile = useCallback(async () => {
    try {
      const data = await fetchProfile();
      setProfile(data);
    } catch (err) {
      console.error('Failed to load profile:', err);
    }
  }, []);

  const chat = useChat();
  const convs = useConversations();
  const location = useLocation();

  useEffect(() => { loadProfile(); }, [loadProfile]);

  const path = location.pathname;
  const showConvPanel = path === '/';

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

  const handleSendMessage = (content: string) => {
    chat.sendMessage(content);
    setTimeout(() => convs.loadConversations(), 500);
  };

  // 所有页面保持挂载，通过 display 切换可见性，避免状态丢失
  const show = (p: string) => ({ display: path === p ? 'flex' : 'none', flex: 1 });

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <NavRail />
      {showConvPanel && (
        <ConversationPanel
          conversations={convs.conversations}
          activeId={convs.activeConversationId}
          onSelect={handleSelectConversation}
          onNew={handleNewConversation}
          onDelete={handleDeleteConversation}
        />
      )}
      <div style={show('/')}>
        <ChatWindow
          messages={chat.messages}
          streamingContent={chat.streamingContent}
          isLoading={chat.isLoading}
          sendMessage={handleSendMessage}
          currentOptions={chat.currentOptions}
          currentReferences={chat.currentReferences}
        />
      </div>
      <div style={show('/wiki')}><WikiBrowser /></div>
      <div style={show('/graph')}><GraphPage /></div>
      <div style={show('/ingest')}><IngestPanel /></div>
      <div style={show('/reviews')}><ReviewPanel /></div>
      <div style={show('/research')}><DeepResearchPanel /></div>
      <div style={show('/settings')}><SettingsPanel /></div>
      <div style={show('/profile')}><ProfilePage /></div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
