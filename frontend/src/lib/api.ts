import type {
  SSECallbacks, Conversation, ConversationDetail,
  WikiPage, WikiGraph, SearchResult, ReviewItem,
  AppSettings, UserProfile, LLMProvider, GraphInsights,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/** 附加 project_id 查询参数 */
function withProject(url: string, projectId?: string): string {
  if (!projectId) return url;
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}project_id=${encodeURIComponent(projectId)}`;
}

// ─── 项目 ──────────────────────────────────────────────────

export async function fetchProjects(): Promise<any[]> {
  const resp = await fetch(`${API_BASE}/api/projects`);
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function createProject(name: string, path?: string): Promise<any> {
  const resp = await fetch(`${API_BASE}/api/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, path: path || undefined }),
  });
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function deleteProject(id: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/projects/${id}`, { method: 'DELETE' });
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
}

// ─── 对话 ──────────────────────────────────────────────────

export async function sendChatMessage(
  message: string,
  history: Array<{ role: string; content: string }>,
  conversationId: string | null,
  callbacks: SSECallbacks,
  projectId?: string,
) {
  const url = withProject(`${API_BASE}/api/chat`, projectId);
  const response = await fetch(url, {
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
        else if (event.type === 'reasoning') callbacks.onReasoning?.(event.content);
        else if (event.type === 'done') callbacks.onDone(event.conversation_id);
        else if (event.type === 'options') callbacks.onOptions(event.options);
        else if (event.type === 'references') callbacks.onReferences(event.references);
      } catch (e) {
        console.warn('SSE parse error:', e);
      }
    }
  }
}

export async function fetchConversations(projectId?: string): Promise<Conversation[]> {
  const resp = await fetch(withProject(`${API_BASE}/api/conversations`, projectId));
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data || data;
}

export async function fetchConversation(id: string, projectId?: string): Promise<ConversationDetail> {
  const resp = await fetch(withProject(`${API_BASE}/api/conversations/${id}`, projectId));
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data || data;
}

export async function deleteConversation(id: string, projectId?: string): Promise<void> {
  const resp = await fetch(withProject(`${API_BASE}/api/conversations/${id}`, projectId), { method: 'DELETE' });
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
}

// ─── Wiki ──────────────────────────────────────────────────

export async function fetchWikiPages(projectId?: string): Promise<{ tree: WikiPage[]; pages: WikiPage[] }> {
  const resp = await fetch(withProject(`${API_BASE}/api/wiki/pages`, projectId));
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function fetchWikiPage(path: string, projectId?: string): Promise<any> {
  const resp = await fetch(withProject(`${API_BASE}/api/wiki/page?path=${encodeURIComponent(path)}`, projectId));
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function deleteWikiPage(path: string, projectId?: string): Promise<void> {
  const resp = await fetch(withProject(`${API_BASE}/api/wiki/page?path=${encodeURIComponent(path)}`, projectId), { method: 'DELETE' });
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
}

export async function fetchWikiGraph(projectId?: string): Promise<WikiGraph> {
  const resp = await fetch(withProject(`${API_BASE}/api/wiki/graph`, projectId));
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function fetchGraphInsights(projectId?: string): Promise<GraphInsights> {
  const resp = await fetch(withProject(`${API_BASE}/api/wiki/graph/insights`, projectId));
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function searchGraph(query: string, projectId?: string): Promise<{ nodes: any[]; edges: any[] }> {
  const resp = await fetch(withProject(`${API_BASE}/api/wiki/graph/search?q=${encodeURIComponent(query)}`, projectId));
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function searchWiki(query: string, limit = 10, projectId?: string): Promise<SearchResult[]> {
  const resp = await fetch(withProject(`${API_BASE}/api/wiki/search?q=${encodeURIComponent(query)}&limit=${limit}`, projectId));
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

// ─── 摄入 ──────────────────────────────────────────────────

export async function ingestFile(file: File, onProgress: (evt: any) => void, projectId?: string): Promise<any> {
  const form = new FormData();
  form.append('file', file);

  const url = withProject(`${API_BASE}/api/ingest`, projectId);
  const resp = await fetch(url, { method: 'POST', body: form });
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

export async function deepResearch(topic: string, keywords?: string[], onProgress?: (evt: any) => void, projectId?: string): Promise<any> {
  const url = withProject(`${API_BASE}/api/research`, projectId);
  const resp = await fetch(url, {
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

export async function fetchReviews(projectId?: string): Promise<ReviewItem[]> {
  const resp = await fetch(withProject(`${API_BASE}/api/reviews`, projectId));
  if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
  const data = await resp.json();
  return data.data;
}

export async function resolveReview(id: string, action: string, projectId?: string): Promise<void> {
  const resp = await fetch(withProject(`${API_BASE}/api/reviews/${id}/resolve?action=${encodeURIComponent(action)}`, projectId), { method: 'POST' });
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
