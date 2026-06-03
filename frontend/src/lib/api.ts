import type {
  SSECallbacks, Conversation, ConversationDetail,
  WikiPage, WikiGraph, SearchResult, ReviewItem,
  AppSettings, UserProfile, LLMProvider, GraphInsights,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ─── 对话 ──────────────────────────────────────────────────

export async function sendChatMessage(
  message: string,
  history: Array<{ role: string; content: string }>,
  conversationId: string | null,
  callbacks: SSECallbacks,
) {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
      if (!line.startsWith('data: ')) continue;
      try {
        const event = JSON.parse(line.slice(6));
        if (event.type === 'chunk') callbacks.onChunk(event.content);
        else if (event.type === 'done') callbacks.onDone(event.conversation_id);
        else if (event.type === 'options') callbacks.onOptions(event.options);
        else if (event.type === 'references') callbacks.onReferences(event.references);
      } catch (e) {
        console.warn('SSE parse error:', e);
      }
    }
  }
}

export async function fetchConversations(): Promise<Conversation[]> {
  const resp = await fetch(`${API_BASE}/api/conversations`);
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data || data;
}

export async function fetchConversation(id: string): Promise<ConversationDetail> {
  const resp = await fetch(`${API_BASE}/api/conversations/${id}`);
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data || data;
}

export async function deleteConversation(id: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/conversations/${id}`, { method: 'DELETE' });
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
}

// ─── Wiki ──────────────────────────────────────────────────

export async function fetchWikiPages(): Promise<{ tree: WikiPage[]; pages: WikiPage[] }> {
  const resp = await fetch(`${API_BASE}/api/wiki/pages`);
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function fetchWikiPage(path: string): Promise<any> {
  const resp = await fetch(`${API_BASE}/api/wiki/page?path=${encodeURIComponent(path)}`);
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function deleteWikiPage(path: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/wiki/page?path=${encodeURIComponent(path)}`, { method: 'DELETE' });
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
}

export async function fetchWikiGraph(): Promise<WikiGraph> {
  const resp = await fetch(`${API_BASE}/api/wiki/graph`);
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function fetchGraphInsights(): Promise<GraphInsights> {
  const resp = await fetch(`${API_BASE}/api/wiki/graph/insights`);
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function searchGraph(query: string): Promise<{ nodes: any[]; edges: any[] }> {
  const resp = await fetch(`${API_BASE}/api/wiki/graph/search?q=${encodeURIComponent(query)}`);
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function searchWiki(query: string, limit = 10): Promise<SearchResult[]> {
  const resp = await fetch(`${API_BASE}/api/wiki/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

// ─── 摄入 ──────────────────────────────────────────────────

export async function ingestFile(file: File, onProgress: (evt: any) => void): Promise<any> {
  const form = new FormData();
  form.append('file', file);

  const resp = await fetch(`${API_BASE}/api/ingest`, { method: 'POST', body: form });
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);

  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let result = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      try {
        const event = JSON.parse(line.slice(6));
        if (event.type === 'progress') onProgress(event);
        else if (event.type === 'done') result = event.result;
        else if (event.type === 'error') throw new Error(event.error);
      } catch (e) {
        if ((e as Error).message !== 'Failed: ' + (e as any).status) throw e;
      }
    }
  }

  return result;
}

// ─── 研究 ──────────────────────────────────────────────────

export async function deepResearch(topic: string, keywords?: string[], onProgress?: (evt: any) => void): Promise<any> {
  const resp = await fetch(`${API_BASE}/api/research`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, keywords }),
  });
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);

  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let result = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      try {
        const event = JSON.parse(line.slice(6));
        if (event.type === 'progress' && onProgress) onProgress(event);
        else if (event.type === 'done') result = event.result;
        else if (event.type === 'error') throw new Error(event.error);
      } catch (e) {
        if ((e as Error).message?.startsWith('Failed')) throw e;
      }
    }
  }

  return result;
}

// ─── 审阅项 ────────────────────────────────────────────────

export async function fetchReviews(): Promise<ReviewItem[]> {
  const resp = await fetch(`${API_BASE}/api/reviews`);
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function resolveReview(id: string, action: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/reviews/${id}/resolve?action=${encodeURIComponent(action)}`, { method: 'POST' });
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
}

// ─── 设置 ──────────────────────────────────────────────────

export async function fetchSettings(): Promise<AppSettings> {
  const resp = await fetch(`${API_BASE}/api/settings`);
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function updateSettings(updates: Partial<AppSettings>): Promise<AppSettings> {
  const resp = await fetch(`${API_BASE}/api/settings`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function testLLMConnection(provider: LLMProvider): Promise<{ success: boolean; data?: any; error?: string }> {
  const resp = await fetch(`${API_BASE}/api/settings/test-connection`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(provider),
  });
  return resp.json();
}

// ─── 用户画像 ──────────────────────────────────────────────

export async function fetchProfile(): Promise<UserProfile | null> {
  const resp = await fetch(`${API_BASE}/api/settings/profile`);
  if (!resp.ok) return null;
  const data = await resp.json();
  return data.data;
}

export async function updateProfile(profile: Partial<UserProfile>): Promise<UserProfile> {
  const resp = await fetch(`${API_BASE}/api/settings/profile`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  });
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}
