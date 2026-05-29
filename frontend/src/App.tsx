import { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import { useChat } from './hooks/useChat';
import { useConversations } from './hooks/useConversations';
import { fetchProfile } from './lib/api';
import { NavRail } from './components/NavRail';
import { ConversationPanel } from './components/Sidebar';
import { ChatWindow } from './components/ChatWindow';
import { GraphPage } from './components/GraphPage';
import { ProfilePage } from './components/ProfilePage';
import { ImportPanel } from './components/ImportPanel';
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

  const chat = useChat(loadProfile);
  const convs = useConversations();
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => { loadProfile(); }, [loadProfile]);

  const showConvPanel = location.pathname === '/';

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
      <Routes>
        <Route
          path="/"
          element={
            <ChatWindow
              messages={chat.messages}
              streamingContent={chat.streamingContent}
              isLoading={chat.isLoading}
              extractionNodes={chat.extractionNodes}
              extractionEdges={chat.extractionEdges}
              sendMessage={handleSendMessage}
            />
          }
        />
        <Route path="/graph" element={<GraphPage key={location.key} />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/import" element={<ImportPanel onImported={() => navigate('/graph')} />} />
      </Routes>
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
