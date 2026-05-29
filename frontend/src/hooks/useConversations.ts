import { useState, useCallback, useEffect } from 'react';
import { fetchConversations, fetchConversation, deleteConversation as apiDeleteConversation } from '../lib/api';
import type { Conversation } from '../types';

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

  const selectConversation = useCallback(async (id: string) => {
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
    return null;
  }, []);

  const deleteConv = useCallback(async (id: string) => {
    try {
      await apiDeleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  }, []);

  // 初始加载
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  return {
    conversations,
    activeConversationId,
    loadConversations,
    selectConversation,
    startNewConversation,
    deleteConversation: deleteConv,
  };
}
