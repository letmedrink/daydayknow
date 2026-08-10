import { useState, useCallback, useEffect } from 'react';
import { fetchConversations, fetchConversation, deleteConversation } from '../lib/api';
import type { Conversation, ConversationDetail } from '../types';

export function useConversations(projectId?: string) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  const loadConversations = useCallback(async () => {
    if (!projectId) return;
    try {
      const data = await fetchConversations(projectId);
      setConversations(data);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  }, [projectId]);

  const selectConversation = useCallback(async (id: string): Promise<ConversationDetail | null> => {
    if (!projectId) return null;
    try {
      const detail = await fetchConversation(id, projectId);
      setActiveConversationId(id);
      return detail;
    } catch (err) {
      console.error('Failed to load conversation:', err);
      return null;
    }
  }, [projectId]);

  const startNewConversation = useCallback(() => {
    setActiveConversationId(null);
  }, []);

  const removeConversation = useCallback(async (id: string) => {
    try {
      await deleteConversation(id, projectId);
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  }, [projectId]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  return {
    conversations,
    activeConversationId,
    loadConversations,
    selectConversation,
    startNewConversation,
    deleteConversation: removeConversation,
  };
}
