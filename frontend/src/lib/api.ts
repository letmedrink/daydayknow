import type {
  AppSettings, Conversation, ConversationDetail, GraphInsights, LLMProvider,
  ReviewItem, SearchResult, SSECallbacks, UserProfile, WikiGraph, WikiPage,
} from '../types';

const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

export function projectBase(projectId?: string): string {
  if (!projectId) throw new Error('请先选择项目');
  return `${API_BASE}/api/projects/${encodeURIComponent(projectId)}`;
}

async function jsonRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.success === false) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload.data as T;
}

export async function consumeSSE(response: Response, onEvent: (event: any) => void): Promise<void> {
  if (!response.ok || !response.body) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const frames = buffer.split('\n\n');
    buffer = frames.pop() || '';
    for (const frame of frames) {
      const data = frame.split('\n').find((line) => line.startsWith('data: '));
      if (!data) continue;
      const event = JSON.parse(data.slice(6));
      if (event.type === 'error') throw new Error(event.error || '流式请求失败');
      onEvent(event);
    }
    if (done) break;
  }
}

export const fetchProjects = () => jsonRequest<any[]>(`${API_BASE}/api/projects`);

export const createProject = (name: string, path?: string) => jsonRequest<any>(`${API_BASE}/api/projects`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, path: path || undefined }),
});

export async function deleteProject(id: string): Promise<void> {
  await jsonRequest(`${API_BASE}/api/projects/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export async function sendChatMessage(
  message: string,
  conversationId: string | null,
  callbacks: SSECallbacks,
  projectId?: string,
) {
  try {
    const response = await fetch(`${projectBase(projectId)}/chat`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, conversation_id: conversationId }),
    });
    await consumeSSE(response, (event) => {
      if (event.type === 'chunk') callbacks.onChunk(event.content);
      else if (event.type === 'reasoning') callbacks.onReasoning?.(event.content);
      else if (event.type === 'done') callbacks.onDone(event.conversation_id);
      else if (event.type === 'options') callbacks.onOptions(event.options);
      else if (event.type === 'references') callbacks.onReferences(event.references);
    });
  } catch (error) {
    callbacks.onError(error instanceof Error ? error : new Error(String(error)));
  }
}

export const fetchConversations = (projectId?: string) => jsonRequest<Conversation[]>(`${projectBase(projectId)}/conversations`);
export const fetchConversation = (id: string, projectId?: string) => jsonRequest<ConversationDetail>(`${projectBase(projectId)}/conversations/${encodeURIComponent(id)}`);
export async function deleteConversation(id: string, projectId?: string): Promise<void> {
  await jsonRequest(`${projectBase(projectId)}/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export const fetchWikiPages = (projectId?: string) => jsonRequest<{ tree: WikiPage[]; pages: WikiPage[] }>(`${projectBase(projectId)}/wiki/pages`);
export const fetchWikiPage = (path: string, projectId?: string) => jsonRequest<any>(`${projectBase(projectId)}/wiki/page?path=${encodeURIComponent(path)}`);
export async function deleteWikiPage(path: string, projectId?: string): Promise<void> {
  await jsonRequest(`${projectBase(projectId)}/wiki/page?path=${encodeURIComponent(path)}`, { method: 'DELETE' });
}
export const fetchWikiGraph = (projectId?: string) => jsonRequest<WikiGraph>(`${projectBase(projectId)}/wiki/graph`);
export const fetchGraphInsights = (projectId?: string) => jsonRequest<GraphInsights>(`${projectBase(projectId)}/wiki/graph/insights`);
export const searchGraph = (query: string, projectId?: string) => jsonRequest<{ nodes: any[]; edges: any[] }>(`${projectBase(projectId)}/wiki/graph/search?q=${encodeURIComponent(query)}`);
export const searchWiki = (query: string, limit = 10, projectId?: string) => jsonRequest<SearchResult[]>(`${projectBase(projectId)}/wiki/search?q=${encodeURIComponent(query)}&limit=${limit}`);

export async function ingestFile(file: File, onProgress: (event: any) => void, projectId?: string): Promise<any> {
  const form = new FormData();
  form.append('file', file);
  let result: any = null;
  await consumeSSE(await fetch(`${projectBase(projectId)}/ingest`, { method: 'POST', body: form }), (event) => {
    if (event.type === 'progress') onProgress(event);
    else if (event.type === 'done') result = event.result;
  });
  return result;
}

export async function deepResearch(topic: string, keywords?: string[], onProgress?: (event: any) => void, projectId?: string): Promise<any> {
  let result: any = null;
  const response = await fetch(`${projectBase(projectId)}/research`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ topic, keywords }),
  });
  await consumeSSE(response, (event) => {
    if (event.type === 'progress') onProgress?.(event);
    else if (event.type === 'done') result = event.result;
  });
  return result;
}

export const fetchReviews = (projectId?: string) => jsonRequest<ReviewItem[]>(`${projectBase(projectId)}/reviews`);
export async function resolveReview(id: string, action: string, projectId?: string): Promise<void> {
  await jsonRequest(`${projectBase(projectId)}/reviews/${encodeURIComponent(id)}/resolve?action=${encodeURIComponent(action)}`, { method: 'POST' });
}

export const fetchSettings = () => jsonRequest<AppSettings>(`${API_BASE}/api/settings`);
export const updateSettings = (updates: Partial<AppSettings>) => jsonRequest<AppSettings>(`${API_BASE}/api/settings`, {
  method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(updates),
});
export async function testLLMConnection(provider: LLMProvider): Promise<{ success: boolean; data?: any; error?: string }> {
  const response = await fetch(`${API_BASE}/api/settings/test-connection`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(provider),
  });
  return response.json();
}
export const fetchProfile = () => jsonRequest<UserProfile | null>(`${API_BASE}/api/profile`);
export const updateProfile = (profile: Partial<UserProfile>) => jsonRequest<UserProfile>(`${API_BASE}/api/profile`, {
  method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile),
});
