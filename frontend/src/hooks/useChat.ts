import { useState, useCallback, useEffect, useRef } from 'react';
import { sendChatMessage } from '../lib/api';
import type { Message, GuidedOption, WikiReference } from '../types';

export function useChat(projectId?: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [currentOptions, setCurrentOptions] = useState<GuidedOption[]>([]);
  const [currentReferences, setCurrentReferences] = useState<WikiReference[]>([]);

  const activeConvRef = useRef<string | null>(null);
  const currentRefsRef = useRef<WikiReference[]>([]);
  const requestRef = useRef<AbortController | null>(null);

  const cancel = useCallback(() => {
    requestRef.current?.abort();
    requestRef.current = null;
    setStreamingContent('');
    setIsLoading(false);
  }, []);

  useEffect(() => () => requestRef.current?.abort(), [projectId]);

  const loadMessages = useCallback((msgs: Message[], convId: string) => {
    setMessages(msgs);
    setConversationId(convId);
    activeConvRef.current = convId;
    setStreamingContent('');
    setCurrentOptions([]);
    setCurrentReferences([]);
  }, []);

  const reset = useCallback(() => {
    requestRef.current?.abort();
    requestRef.current = null;
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
      if (!content.trim() || isLoading || !projectId) return;

      setIsLoading(true);
      setStreamingContent('');
      setCurrentOptions([]);
      setCurrentReferences([]);
      currentRefsRef.current = [];

      const userMsg: Message = { role: 'user', content };
      setMessages((prev) => [...prev, userMsg]);

      let assistantContent = '';
      let thinkingOpen = false;
      const sendConvId = conversationId;
      const controller = new AbortController();
      requestRef.current?.abort();
      requestRef.current = controller;

      const closeThinking = () => {
        if (thinkingOpen) {
          thinkingOpen = false;
          assistantContent += '</think>';
        }
      };

      await sendChatMessage(
        content,
        conversationId,
        {
          onReasoning: (token) => {
            if (!thinkingOpen) {
              thinkingOpen = true;
              assistantContent += '<think>';
            }
            assistantContent += token;
            setStreamingContent(assistantContent);
          },
          onChunk: (chunk) => {
            closeThinking();
            assistantContent += chunk;
            setStreamingContent(assistantContent);
          },
          onDone: (cid, messageId) => {
            closeThinking();
            // 剥离 OPTIONS 行（后端也会剥离，但流式内容已包含）
            const cleanContent = assistantContent.replace(/\n?OPTIONS:\s*.+$/m, '').trim();
            setConversationId(cid);
            activeConvRef.current = cid;
            const refs = currentRefsRef.current;
            setMessages((prev) => [
              ...prev,
              { id: messageId, role: 'assistant', content: cleanContent, references: refs.length > 0 ? refs : undefined },
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
              currentRefsRef.current = refs;
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
        projectId,
        controller.signal,
      );
      if (requestRef.current === controller) {
        requestRef.current = null;
        setIsLoading(false);
      }
    },
    [conversationId, isLoading, projectId],
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
    cancel,
  };
}
