// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { TaskCenter } from './TaskCenter';

const api = vi.hoisted(() => ({
  fetchIngestJobs: vi.fn(), fetchResearchJobs: vi.fn(), acceptIngestJob: vi.fn(),
  acceptResearchJob: vi.fn(), deleteIngestJob: vi.fn(), deleteResearchJob: vi.fn(),
  rejectIngestJob: vi.fn(), rejectResearchJob: vi.fn(), retryIngestJob: vi.fn(), retryResearchJob: vi.fn(),
}));

vi.mock('../lib/api', () => api);
vi.mock('../contexts/ProjectContext', () => ({ useProject: () => ({ activeProjectId: 'project-one' }) }));

afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe('TaskCenter', () => {
  it('restores persisted ingest and research tasks and filters status', async () => {
    api.fetchIngestJobs.mockResolvedValue([{ id: 'ingest_1', filename: 'book.pdf', status: 'awaiting_review', createdAt: 2, result: { proposals: [] } }]);
    api.fetchResearchJobs.mockResolvedValue([{ id: 'research_1', topic: 'RAG', status: 'failed', createdAt: 1, message: 'network' }]);
    render(<TaskCenter />);

    expect(await screen.findByText('book.pdf')).toBeInTheDocument();
    expect(screen.getByText('RAG')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '失败' }));
    await waitFor(() => expect(screen.queryByText('book.pdf')).not.toBeInTheDocument());
    expect(screen.getByText('RAG')).toBeInTheDocument();
  });

  it('accepts a recovered ingest task and refreshes the list', async () => {
    api.fetchIngestJobs.mockResolvedValueOnce([{ id: 'ingest_1', filename: 'book.pdf', status: 'awaiting_review', createdAt: 2, result: { proposals: [] } }]).mockResolvedValueOnce([]);
    api.fetchResearchJobs.mockResolvedValue([]);
    api.acceptIngestJob.mockResolvedValue({});
    render(<TaskCenter />);
    fireEvent.click(await screen.findByRole('button', { name: '全部接受' }));
    await waitFor(() => expect(api.acceptIngestJob).toHaveBeenCalledWith('ingest_1', 'project-one'));
    await waitFor(() => expect(screen.getByText('暂无任务')).toBeInTheDocument());
  });
});
