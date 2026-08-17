import { describe, expect, it } from 'vitest';

import { consumeSSE, deleteProjectData, ingestFile, projectBase, resolveReview } from './api';

describe('projectBase', () => {
  it('builds a path-scoped project URL', () => {
    expect(projectBase('project with spaces')).toMatch(/\/api\/projects\/project%20with%20spaces$/);
  });

  it('requires an active project', () => {
    expect(() => projectBase()).toThrow('请先选择项目');
  });
});

describe('consumeSSE', () => {
  it('parses events split across stream chunks', async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"chunk","content":"你'));
        controller.enqueue(encoder.encode('好"}\n\ndata: {"type":"done"}\n\n'));
        controller.close();
      },
    });
    const events: any[] = [];
    await consumeSSE(new Response(stream, { status: 200 }), (event) => events.push(event));
    expect(events).toEqual([{ type: 'chunk', content: '你好' }, { type: 'done' }]);
  });

  it('turns an SSE error event into an exception', async () => {
    const body = 'data: {"type":"error","error":"upstream failed"}\n\n';
    await expect(consumeSSE(new Response(body), () => undefined)).rejects.toThrow('upstream failed');
  });

  it('supports CRLF, multiline data and a final unterminated frame', async () => {
    const body = 'event: message\r\ndata: {"type":\r\ndata: "chunk","content":"ok"}\r\n\r\ndata: {"type":"done"}';
    const events: any[] = [];
    await consumeSSE(new Response(body), (event) => events.push(event));
    expect(events).toEqual([{ type: 'chunk', content: 'ok' }, { type: 'done' }]);
  });
});

describe('mutation protocols', () => {
  it('sends the explicit force flag for re-ingest', async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async (_url: string | URL | Request, init?: RequestInit) => {
      const form = init?.body as FormData;
      expect(form.get('force')).toBe('true');
      return new Response('data: {"type":"done","result":{"cached":false}}\n\n');
    }) as typeof fetch;
    try {
      const result = await ingestFile(new File(['source'], 'source.txt'), () => undefined, 'project', true);
      expect(result.cached).toBe(false);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('requires a project-name confirmation for permanent deletion', async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async (_url: string | URL | Request, init?: RequestInit) => {
      expect(init?.method).toBe('DELETE');
      expect(JSON.parse(String(init?.body))).toEqual({ confirmation: 'alpha' });
      return new Response('{"success":true,"data":null}', { headers: { 'Content-Type': 'application/json' } });
    }) as typeof fetch;
    try {
      await deleteProjectData('project', 'alpha');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('sends review resolution as a validated JSON action', async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async (_url: string | URL | Request, init?: RequestInit) => {
      expect(init?.method).toBe('POST');
      expect(JSON.parse(String(init?.body))).toEqual({ action: 'skip' });
      return new Response('{"success":true,"data":null}', { headers: { 'Content-Type': 'application/json' } });
    }) as typeof fetch;
    try {
      await resolveReview('review', 'skip', 'project');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
