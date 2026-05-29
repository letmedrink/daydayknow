import { useState, useCallback, useRef } from 'react';
import { sendChatMessage, pollTaskResult } from '../lib/api';
import type { Message, KgNode, KgEdge } from '../types';

export function useChat(onProfileUpdate?: () => void) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [extractionNodes, setExtractionNodes] = useState<KgNode[]>([]);
  const [extractionEdges, setExtractionEdges] = useState<KgEdge[]>([]);

  // 跟踪当前对话 ID，防止异步回调污染其他对话
  const activeConvRef = useRef<string | null>(null);

  const loadMessages = useCallback((msgs: Message[], convId: string) => {
    setMessages(msgs);
    setConversationId(convId);
    activeConvRef.current = convId;
    setStreamingContent('');
    setExtractionNodes([]);
    setExtractionEdges([]);
  }, []);

  const reset = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    activeConvRef.current = null;
    setStreamingContent('');
    setExtractionNodes([]);
    setExtractionEdges([]);
    setIsLoading(false);
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return;

      setIsLoading(true);
      setStreamingContent('');
      setExtractionNodes([]);
      setExtractionEdges([]);

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
          onExtraction: (nodes, edges) => {
            // 仅在当前对话未变化时更新
            if (activeConvRef.current === (sendConvId || activeConvRef.current)) {
              setExtractionNodes(nodes);
              setExtractionEdges(edges);
            }
          },
          onProfile: () => {
            onProfileUpdate?.();
          },
          onTaskEnqueued: (taskId) => {
            pollTaskResult(taskId, (result) => {
              // 仅在当前对话未变化时更新
              if (activeConvRef.current === (sendConvId || activeConvRef.current)) {
                setExtractionNodes(result.nodes);
                setExtractionEdges(result.edges);
              }
            });
          },
          onError: (err) => {
            console.error(err);
            setMessages((prev) => [
              ...prev,
              { role: 'assistant', content: `[错误] ${err.message}` },
            ]);
            setIsLoading(false);
          },
        },
      );
    },
    [messages, conversationId, isLoading, onProfileUpdate],
  );

  return {
    messages,
    streamingContent,
    isLoading,
    sendMessage,
    extractionNodes,
    extractionEdges,
    conversationId,
    loadMessages,
    reset,
  };
}
