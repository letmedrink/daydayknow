import { useState, useCallback, useEffect } from 'react';
import { fetchConversations, fetchConversation, deleteConversation } from '../lib/api';
import type { Conversation, ConversationDetail } from '../types';

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  const loadConversations = useCallback(async () => {
    try {
      const data = await fetchConversations();
      setConversations(data);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  }, []);

  const selectConversation = useCallback(async (id: string): Promise<ConversationDetail | null> => {
    try {
      const detail = await fetchConversation(id);
      setActiveConversationId(id);
      return detail;
    } catch (err) {
      console.error('Failed to load conversation:', err);
      return null;
    }
  }, []);

  const startNewConversation = useCallback(() => {
    setActiveConversationId(null);
  }, []);

  const removeConversation = useCallback(async (id: string) => {
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  }, []);

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
