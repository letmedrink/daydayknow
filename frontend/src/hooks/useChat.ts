import { useState, useCallback, useRef } from 'react';
import { sendChatMessage } from '../lib/api';
import type { Message, GuidedOption, WikiReference } from '../types';

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [currentOptions, setCurrentOptions] = useState<GuidedOption[]>([]);
  const [currentReferences, setCurrentReferences] = useState<WikiReference[]>([]);

  const activeConvRef = useRef<string | null>(null);

  const loadMessages = useCallback((msgs: Message[], convId: string) => {
    setMessages(msgs);
    setConversationId(convId);
    activeConvRef.current = convId;
    setStreamingContent('');
    setCurrentOptions([]);
    setCurrentReferences([]);
  }, []);

  const reset = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    activeConvRef.current = null;
    setStreamingContent('');
    setCurrentOptions([]);
    setCurrentReferences([]);
    setIsLoading(false);
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return;

      setIsLoading(true);
      setStreamingContent('');
      setCurrentOptions([]);
      setCurrentReferences([]);

      const userMsg: Message = { role: 'user', content };
      setMessages((prev) => [...prev, userMsg]);

      let assistantContent = '';
      const sendConvId = conversationId;

      await sendChatMessage(
        content,
        [...messages, userMsg].map((m) => ({ role: m.role, content: m.content })),
        conversationId,
        {
          onChunk: (chunk) => {
            assistantContent += chunk;
            setStreamingContent(assistantContent);
          },
          onDone: (cid) => {
            setConversationId(cid);
            activeConvRef.current = cid;
            setMessages((prev) => [
              ...prev,
              { role: 'assistant', content: assistantContent },
            ]);
            setStreamingContent('');
            setIsLoading(false);
          },
          onOptions: (options) => {
            if (activeConvRef.current === (sendConvId || activeConvRef.current)) {
              setCurrentOptions(options);
            }
          },
          onReferences: (refs) => {
            if (activeConvRef.current === (sendConvId || activeConvRef.current)) {
              setCurrentReferences(refs);
            }
          },
          onError: (err) => {
            setMessages((prev) => [
              ...prev,
              { role: 'assistant', content: `[错误] ${err.message}` },
            ]);
            setIsLoading(false);
          },
        },
      );
    },
    [messages, conversationId, isLoading],
  );

  return {
    messages,
    streamingContent,
    isLoading,
    sendMessage,
    conversationId,
    loadMessages,
    reset,
    currentOptions,
    currentReferences,
  };
}
