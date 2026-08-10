import { describe, expect, it } from 'vitest';

import { consumeSSE, projectBase } from './api';

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
});
