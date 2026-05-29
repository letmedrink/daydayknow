import type { SSECallbacks, KgNode, KgEdge, Conversation, ConversationDetail, UserProfile } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const USER_ID = 'poc_user_001';

export async function sendChatMessage(
  message: string,
  history: Array<{ role: string; content: string }>,
  conversationId: string | null,
  callbacks: SSECallbacks,
) {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-user-id': USER_ID,
    },
    body: JSON.stringify({ message, history, conversation_id: conversationId }),
  });

  if (!response.ok) {
    callbacks.onError(new Error(`Chat failed: ${response.status}`));
    return;
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event = JSON.parse(line.slice(6));
          if (event.type === 'chunk') callbacks.onChunk(event.content);
          else if (event.type === 'done') callbacks.onDone(event.conversation_id);
          else if (event.type === 'extraction')
            callbacks.onExtraction(event.nodes, event.edges);
          else if (event.type === 'profile' && callbacks.onProfile)
            callbacks.onProfile();
          else if (event.type === 'conflict' && callbacks.onConflict)
            callbacks.onConflict(event.conflicts);
          else if (event.type === 'task_enqueued' && callbacks.onTaskEnqueued)
            callbacks.onTaskEnqueued(event.task_id, event.conversation_id);
        } catch (e) {
          console.warn('SSE parse error:', e, line.slice(6, 120));
        }
      }
    }
  }
}

export async function pollTaskResult(
  taskId: string,
  onResult: (result: { nodes: KgNode[]; edges: KgEdge[] }) => void,
  maxAttempts = 30,
) {
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    try {
      const resp = await fetch(`${API_BASE}/api/tasks/${taskId}`);
      if (!resp.ok) continue;
      const data = await resp.json();
      if (data.status === 'completed' && data.result) {
        onResult({
          nodes: data.result.nodes || [],
          edges: data.result.edges || [],
        });
        return;
      }
      if (data.status === 'failed') {
        console.warn('Task failed:', data);
        return;
      }
    } catch (e) {
      console.warn('Task poll error:', e);
    }
  }
  console.warn('Task poll timed out:', taskId);
}

export async function fetchKnowledge(): Promise<{ nodes: KgNode[]; edges: KgEdge[] }> {
  const response = await fetch(`${API_BASE}/api/knowledge/${USER_ID}`);
  if (!response.ok) throw new Error(`Failed to fetch knowledge: ${response.status}`);
  return response.json();
}

export async function fetchConversations(limit = 50): Promise<Conversation[]> {
  const response = await fetch(`${API_BASE}/api/conversations?limit=${limit}`, {
    headers: { 'x-user-id': USER_ID },
  });
  if (!response.ok) throw new Error(`Failed to fetch conversations: ${response.status}`);
  return response.json();
}

export async function fetchConversation(id: string): Promise<ConversationDetail> {
  const response = await fetch(`${API_BASE}/api/conversations/${id}`, {
    headers: { 'x-user-id': USER_ID },
  });
  if (!response.ok) throw new Error(`Failed to fetch conversation: ${response.status}`);
  return response.json();
}

export async function deleteConversation(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/conversations/${id}`, {
    method: 'DELETE',
    headers: { 'x-user-id': USER_ID },
  });
  if (!response.ok) throw new Error(`Failed to delete conversation: ${response.status}`);
}

export async function importContent(content: string, sourceName?: string): Promise<{ nodes: KgNode[]; edges: KgEdge[]; error?: string }> {
  const response = await fetch(`${API_BASE}/api/import`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-user-id': USER_ID,
    },
    body: JSON.stringify({ content, source_name: sourceName }),
  });
  if (!response.ok) throw new Error(`Import failed: ${response.status}`);
  return response.json();
}

export async function fetchProfile(): Promise<UserProfile | null> {
  const response = await fetch(`${API_BASE}/api/profile/${USER_ID}`, {
    headers: { 'x-user-id': USER_ID },
  });
  if (!response.ok) throw new Error(`Failed to fetch profile: ${response.status}`);
  const data = await response.json();
  return data.data;
}
