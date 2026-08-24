// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { IngestTrace } from './IngestTrace';

afterEach(cleanup);

describe('IngestTrace', () => {
  it('renders a chronological, structured ingest chain', () => {
    render(<IngestTrace events={[
      { stage: 'parse', title: '文档解析完成', timestamp: 1000, meta: [{ label: '物理分页', value: '12' }] },
      { stage: 'analyze', title: '分析分块 1/2', message: '正在调用文本模型', timestamp: 2500, meta: [{ label: '模型', value: 'test-model' }] },
    ]} />);
    expect(screen.getByText('详细处理链路 · 2 条事件')).toBeInTheDocument();
    expect(screen.getByText('文档解析完成')).toBeInTheDocument();
    expect(screen.getByText(/test-model/)).toBeInTheDocument();
    expect(screen.getByText('+1.5s')).toBeInTheDocument();
  });
});
