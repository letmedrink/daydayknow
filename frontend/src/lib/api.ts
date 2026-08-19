import type {
  AppSettings, Conversation, ConversationDetail, GraphInsights, LLMProvider,
  ReviewItem, SearchResult, SSECallbacks, UserProfile, WikiGraph, WikiPage, WikiPageContent, WikiPageVersion,
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
    buffer = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    const frames = buffer.split('\n\n');
    buffer = frames.pop() || '';
    for (const frame of frames) {
      const data = frame.split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).replace(/^ /, ''))
        .join('\n');
      if (!data) continue;
      const event = JSON.parse(data);
      if (event.type === 'error') throw new Error(event.error || '流式请求失败');
      onEvent(event);
    }
    if (done) {
      const tail = buffer.trim();
      if (tail) {
        const data = tail.split('\n').filter((line) => line.startsWith('data:')).map((line) => line.slice(5).replace(/^ /, '')).join('\n');
        if (data) {
          const event = JSON.parse(data);
          if (event.type === 'error') throw new Error(event.error || '流式请求失败');
          onEvent(event);
        }
      }
      break;
    }
  }
}

export const fetchProjects = () => jsonRequest<any[]>(`${API_BASE}/api/projects`);

export const createProject = (name: string, path?: string) => jsonRequest<any>(`${API_BASE}/api/projects`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, path: path || undefined }),
});

export async function deleteProject(id: string): Promise<void> {
  await jsonRequest(`${API_BASE}/api/projects/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export async function deleteProjectData(id: string, confirmation: string): Promise<void> {
  await jsonRequest(`${API_BASE}/api/projects/${encodeURIComponent(id)}/data`, {
    method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirmation }),
  });
}

export async function exportProject(id: string, name: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/projects/${encodeURIComponent(id)}/export`);
  if (!response.ok) throw new Error(`导出失败: ${response.status}`);
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a'); link.href = url; link.download = `${name}.zip`; link.click();
  URL.revokeObjectURL(url);
}

export async function importProject(file: File, name?: string): Promise<any> {
  const form = new FormData(); form.append('archive', file); if (name) form.append('name', name);
  return jsonRequest<any>(`${API_BASE}/api/projects/import`, { method: 'POST', body: form });
}

export async function sendChatMessage(
  message: string,
  conversationId: string | null,
  callbacks: SSECallbacks,
  projectId?: string,
  signal?: AbortSignal,
) {
  try {
    const response = await fetch(`${projectBase(projectId)}/chat`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, conversation_id: conversationId }),
      signal,
    });
    await consumeSSE(response, (event) => {
      if (event.type === 'chunk') callbacks.onChunk(event.content);
      else if (event.type === 'reasoning') callbacks.onReasoning?.(event.content);
      else if (event.type === 'done') callbacks.onDone(event.conversation_id);
      else if (event.type === 'options') callbacks.onOptions(event.options);
      else if (event.type === 'references') callbacks.onReferences(event.references);
    });
  } catch (error) {
    if (!(error instanceof DOMException && error.name === 'AbortError')) {
      callbacks.onError(error instanceof Error ? error : new Error(String(error)));
    }
  }
}

export const fetchConversations = (projectId?: string) => jsonRequest<Conversation[]>(`${projectBase(projectId)}/conversations`);
export const fetchConversation = (id: string, projectId?: string) => jsonRequest<ConversationDetail>(`${projectBase(projectId)}/conversations/${encodeURIComponent(id)}`);
export async function deleteConversation(id: string, projectId?: string): Promise<void> {
  await jsonRequest(`${projectBase(projectId)}/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export const fetchWikiPages = (projectId?: string) => jsonRequest<{ tree: WikiPage[]; pages: WikiPage[] }>(`${projectBase(projectId)}/wiki/pages`);
export const fetchWikiPage = (path: string, projectId?: string) => jsonRequest<WikiPageContent>(`${projectBase(projectId)}/wiki/page?path=${encodeURIComponent(path)}`);
export const saveWikiPage = (path: string, content: string, projectId?: string) => jsonRequest<WikiPageContent>(`${projectBase(projectId)}/wiki/page`, {
  method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path, content }),
});
export const renameWikiPage = (oldPath: string, newPath: string, projectId?: string, updateLinks = true) => jsonRequest<{ path: string; updated_links: string[] }>(`${projectBase(projectId)}/wiki/page/rename`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ old_path: oldPath, new_path: newPath, update_links: updateLinks }),
});
export const fetchWikiPageHistory = (path: string, projectId?: string) => jsonRequest<WikiPageVersion[]>(`${projectBase(projectId)}/wiki/page/history?path=${encodeURIComponent(path)}`);
export const fetchWikiPageVersion = (path: string, versionId: string, projectId?: string) => jsonRequest<WikiPageContent & { id: string; createdAt: number }>(`${projectBase(projectId)}/wiki/page/history/version?path=${encodeURIComponent(path)}&version_id=${encodeURIComponent(versionId)}`);
export const restoreWikiPageVersion = (path: string, versionId: string, projectId?: string) => jsonRequest<WikiPageContent>(`${projectBase(projectId)}/wiki/page/history/restore`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path, version_id: versionId }),
});
export async function deleteWikiPage(path: string, projectId?: string): Promise<void> {
  await jsonRequest(`${projectBase(projectId)}/wiki/page?path=${encodeURIComponent(path)}`, { method: 'DELETE' });
}
export const fetchWikiGraph = (projectId?: string) => jsonRequest<WikiGraph>(`${projectBase(projectId)}/wiki/graph`);
export const fetchGraphInsights = (projectId?: string) => jsonRequest<GraphInsights>(`${projectBase(projectId)}/wiki/graph/insights`);
export const searchGraph = (query: string, projectId?: string) => jsonRequest<{ nodes: any[]; edges: any[] }>(`${projectBase(projectId)}/wiki/graph/search?q=${encodeURIComponent(query)}`);
export const searchWiki = (query: string, limit = 10, projectId?: string) => jsonRequest<SearchResult[]>(`${projectBase(projectId)}/wiki/search?q=${encodeURIComponent(query)}&limit=${limit}`);

export async function ingestFile(file: File, onProgress: (event: any) => void, projectId?: string, force = false, signal?: AbortSignal): Promise<any> {
  const form = new FormData();
  form.append('file', file);
  form.append('force', String(force));
  let result: any = null;
  await consumeSSE(await fetch(`${projectBase(projectId)}/ingest`, { method: 'POST', body: form, signal }), (event) => {
    if (event.type === 'progress') onProgress(event);
    else if (event.type === 'done') result = { ...event.result, job: event.job };
  });
  return result;
}

export async function deepResearch(topic: string, keywords?: string[], onProgress?: (event: any) => void, projectId?: string, signal?: AbortSignal, reviewId?: string): Promise<any> {
  let result: any = null;
  const response = await fetch(`${projectBase(projectId)}/research`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ topic, keywords, review_id: reviewId }), signal,
  });
  await consumeSSE(response, (event) => {
    if (event.type === 'progress') onProgress?.(event);
    else if (event.type === 'done') result = { ...event.result, job: event.job };
  });
  return result;
}

export const fetchResearchJobs = (projectId?: string) => jsonRequest<any[]>(`${projectBase(projectId)}/research/jobs`);
export const acceptResearchJob = (jobId: string, projectId?: string) => jsonRequest<any>(`${projectBase(projectId)}/research/jobs/${encodeURIComponent(jobId)}/accept`, { method: 'POST' });
export const rejectResearchJob = (jobId: string, projectId?: string) => jsonRequest<any>(`${projectBase(projectId)}/research/jobs/${encodeURIComponent(jobId)}/reject`, { method: 'POST' });
export const deleteResearchJob = (jobId: string, projectId?: string) => jsonRequest<void>(`${projectBase(projectId)}/research/jobs/${encodeURIComponent(jobId)}`, { method: 'DELETE' });
export async function retryResearchJob(jobId: string, onProgress: (event: any) => void, projectId?: string): Promise<any> {
  let result: any = null;
  await consumeSSE(await fetch(`${projectBase(projectId)}/research/jobs/${encodeURIComponent(jobId)}/retry`, { method: 'POST' }), (event) => {
    if (event.type === 'progress') onProgress(event); else if (event.type === 'done') result = { ...event.result, job: event.job };
  });
  return result;
}

export const fetchIngestJobs = (projectId?: string) => jsonRequest<any[]>(`${projectBase(projectId)}/ingest/jobs`);
export const acceptIngestJob = (jobId: string, projectId?: string, proposals?: Array<{ path: string; content: string; merge?: boolean }>) => jsonRequest<any>(`${projectBase(projectId)}/ingest/jobs/${encodeURIComponent(jobId)}/accept`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ proposals }),
});
export const rejectIngestJob = (jobId: string, projectId?: string) => jsonRequest<any>(`${projectBase(projectId)}/ingest/jobs/${encodeURIComponent(jobId)}/reject`, { method: 'POST' });
export const cancelIngestJob = (jobId: string, projectId?: string) => jsonRequest<any>(`${projectBase(projectId)}/ingest/jobs/${encodeURIComponent(jobId)}/cancel`, { method: 'POST' });
export const deleteIngestJob = (jobId: string, projectId?: string) => jsonRequest<void>(`${projectBase(projectId)}/ingest/jobs/${encodeURIComponent(jobId)}`, { method: 'DELETE' });
export async function retryIngestJob(jobId: string, onProgress: (event: any) => void, projectId?: string): Promise<any> {
  let result: any = null;
  await consumeSSE(await fetch(`${projectBase(projectId)}/ingest/jobs/${encodeURIComponent(jobId)}/retry`, { method: 'POST' }), (event) => {
    if (event.type === 'progress') onProgress(event); else if (event.type === 'done') result = { ...event.result, job: event.job };
  });
  return result;
}
export async function regenerateIngestJob(jobId: string, feedback: string, onProgress: (event: any) => void, projectId?: string, signal?: AbortSignal): Promise<any> {
  let result: any = null;
  const response = await fetch(`${projectBase(projectId)}/ingest/jobs/${encodeURIComponent(jobId)}/regenerate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ feedback }), signal,
  });
  await consumeSSE(response, (event) => {
    if (event.type === 'progress') onProgress(event);
    else if (event.type === 'done') result = { ...event.result, job: event.job };
  });
  return result;
}

export const fetchReviews = (projectId?: string) => jsonRequest<ReviewItem[]>(`${projectBase(projectId)}/reviews`);
export async function resolveReview(id: string, action: string, projectId?: string, details: Record<string, any> = {}): Promise<void> {
  await jsonRequest(`${projectBase(projectId)}/reviews/${encodeURIComponent(id)}/resolve`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action, ...details }),
  });
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
