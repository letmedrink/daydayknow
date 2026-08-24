import { useEffect, useState } from 'react';
import {
  acceptIngestJob, acceptResearchJob, deleteIngestJob, deleteResearchJob,
  fetchIngestJobs, fetchResearchJobs, rejectIngestJob, rejectResearchJob,
  retryIngestJob, retryResearchJob, fetchChangeJobs, acceptChangeJob, rejectChangeJob,
  retryChangeJob, deleteChangeJob, runWikiLint,
} from '../lib/api';
import { useProject } from '../contexts/ProjectContext';
import { theme } from '../lib/theme';
import { ProposalDiff } from './ProposalDiff';
import { IngestTrace } from './IngestTrace';

type Task = Record<string, any> & { kind: 'ingest' | 'research' | 'query' | 'lint' };
const retryable = new Set(['failed', 'cancelled', 'interrupted']);
const removable = new Set(['failed', 'cancelled', 'interrupted', 'accepted', 'rejected']);
const statusLabel: Record<string, string> = {
  pending: '等待中', running: '运行中', awaiting_review: '待审核', failed: '失败',
  cancelled: '已取消', interrupted: '已中断', accepted: '已接受', rejected: '已拒绝',
};

export function TaskCenter() {
  const { activeProjectId } = useProject();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState('all');
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const [ingest, research, changes] = await Promise.all([fetchIngestJobs(activeProjectId), fetchResearchJobs(activeProjectId), fetchChangeJobs(activeProjectId)]);
      setTasks([
        ...ingest.map((task: any) => ({ ...task, kind: 'ingest' as const })),
        ...research.map((task: any) => ({ ...task, kind: 'research' as const })),
        ...changes.map((task: any) => ({ ...task, kind: task.kind as 'query' | 'lint' })),
      ].sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0)));
      setError('');
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  };

  useEffect(() => { void load(); }, [activeProjectId]);
  const act = async (task: Task, action: 'accept' | 'reject' | 'retry' | 'delete') => {
    setBusy(task.id);
    try {
      if (action === 'accept') {
        if (task.kind === 'ingest') await acceptIngestJob(task.id, activeProjectId);
        else if (task.kind === 'research') await acceptResearchJob(task.id, activeProjectId);
        else await acceptChangeJob(task.id, activeProjectId, task.result?.proposals?.map((page: any) => ({ path: page.path, content: page.content })));
      }
      if (action === 'reject') {
        if (task.kind === 'ingest') await rejectIngestJob(task.id, activeProjectId);
        else if (task.kind === 'research') await rejectResearchJob(task.id, activeProjectId);
        else await rejectChangeJob(task.id, activeProjectId);
      }
      if (action === 'retry') {
        if (task.kind === 'ingest') await retryIngestJob(task.id, () => undefined, activeProjectId);
        else if (task.kind === 'research') await retryResearchJob(task.id, () => undefined, activeProjectId);
        else await retryChangeJob(task.id, activeProjectId);
      }
      if (action === 'delete') {
        if (!window.confirm('删除这条任务记录及暂存文件？已写入的 Wiki 页面不会删除。')) return;
        if (task.kind === 'ingest') await deleteIngestJob(task.id, activeProjectId);
        else if (task.kind === 'research') await deleteResearchJob(task.id, activeProjectId);
        else await deleteChangeJob(task.id, activeProjectId);
      }
      await load();
      window.dispatchEvent(new Event('wikiPagesUpdated'));
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(null); }
  };

  const visible = tasks.filter((task) => filter === 'all' || task.status === filter);
  const updateProposal = (taskId: string, proposalIndex: number, content: string) => setTasks((current) => current.map((task) => task.id === taskId ? {
    ...task, result: { ...task.result, proposals: task.result.proposals.map((page: any, index: number) => index === proposalIndex ? { ...page, content } : page) },
  } : task));
  const startLint = async () => {
    setBusy('lint');
    try { await runWikiLint(activeProjectId); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(null); }
  };
  return <div style={styles.container}>
    <div style={styles.header}><div><h2 style={styles.title}>任务中心</h2><p style={styles.desc}>恢复、审核和清理摄入、研究、问答回写与 Lint 任务</p></div><div style={styles.actions}><button style={styles.btn} disabled={busy === 'lint'} onClick={startLint}>运行 Wiki Lint</button><button style={styles.btn} onClick={load}>刷新</button></div></div>
    <div style={styles.filters}>{['all', 'running', 'awaiting_review', 'failed', 'interrupted', 'accepted', 'rejected'].map((value) => <button key={value} style={{ ...styles.filter, ...(filter === value ? styles.active : {}) }} onClick={() => setFilter(value)}>{value === 'all' ? '全部' : statusLabel[value]}</button>)}</div>
    {error && <p style={styles.error}>{error}</p>}
    {visible.length === 0 ? <p style={styles.empty}>暂无任务</p> : visible.map((task) => <article key={`${task.kind}-${task.id}`} style={styles.card}>
      <div style={styles.cardHeader}><strong>{task.kind === 'ingest' ? task.filename : task.kind === 'research' ? task.topic : task.title}</strong><span style={styles.badge}>{task.kind === 'ingest' ? '摄入' : task.kind === 'research' ? '研究' : task.kind === 'query' ? '问答回写' : 'Lint'} · {statusLabel[task.status] || task.status}</span></div>
      <div style={styles.meta}>{new Date(task.createdAt).toLocaleString()} · {task.message || task.step || ''}</div>
      {task.kind === 'ingest' && task.trace?.length > 0 && <IngestTrace events={task.trace} />}
      {task.status === 'awaiting_review' && <details style={styles.details}><summary>查看待写入页面与检查结果</summary>
        {task.result?.findings?.map((finding: any, index: number) => <div key={`${finding.type}-${index}`} style={styles.finding}>[{finding.type}] {finding.path || ''} {finding.message}</div>)}
        {task.result?.proposals?.map((page: any, index: number) => <details key={page.path} style={styles.page}><summary>{page.title || page.path} · {page.path} · {page.operation || 'update'}</summary>
          {page.previousContent && <ProposalDiff before={page.previousContent} after={page.content} />}
          {(task.kind === 'query' || task.kind === 'lint') ? <textarea style={styles.editor} value={page.content} onChange={(event) => updateProposal(task.id, index, event.target.value)} /> : <pre style={styles.previous}>{page.content}</pre>}
        </details>)}
      </details>}
      <div style={styles.actions}>
        {task.status === 'awaiting_review' && <><button style={styles.accept} disabled={busy === task.id} onClick={() => act(task, 'accept')}>全部接受</button><button style={styles.reject} disabled={busy === task.id} onClick={() => act(task, 'reject')}>拒绝</button></>}
        {retryable.has(task.status) && <button style={styles.btn} disabled={busy === task.id} onClick={() => act(task, 'retry')}>重试</button>}
        {removable.has(task.status) && <button style={styles.btn} disabled={busy === task.id} onClick={() => act(task, 'delete')}>清理记录</button>}
      </div>
    </article>)}
  </div>;
}

const styles: Record<string, React.CSSProperties> = {
  container: { flex: 1, padding: 24, maxWidth: 820, margin: '0 auto', overflowY: 'auto', fontFamily: theme.font },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' }, title: { margin: 0, color: theme.text.primary, fontSize: 20 }, desc: { color: theme.text.secondary, fontSize: 13 },
  filters: { display: 'flex', gap: 6, margin: '12px 0 18px', flexWrap: 'wrap' }, filter: { padding: '5px 10px', border: `1px solid ${theme.border.light}`, borderRadius: 12, background: theme.bg.content, color: theme.text.secondary, cursor: 'pointer' }, active: { background: theme.accentBg, color: theme.accent },
  card: { padding: 15, marginBottom: 10, border: `1px solid ${theme.border.light}`, borderRadius: theme.radius.md, background: theme.bg.raised }, cardHeader: { display: 'flex', justifyContent: 'space-between', gap: 12 }, badge: { color: theme.accent, fontSize: 12 }, meta: { marginTop: 7, color: theme.text.tertiary, fontSize: 12 },
  actions: { display: 'flex', gap: 8, marginTop: 12 }, btn: { padding: '6px 11px', border: `1px solid ${theme.border.medium}`, borderRadius: 5, background: theme.bg.content, color: theme.text.primary, cursor: 'pointer' }, accept: { padding: '6px 11px', border: 'none', borderRadius: 5, background: '#27845b', color: '#fff', cursor: 'pointer' }, reject: { padding: '6px 11px', border: 'none', borderRadius: 5, background: '#b84a45', color: '#fff', cursor: 'pointer' },
  details: { marginTop: 10, color: theme.text.secondary, fontSize: 12 }, page: { padding: '4px 8px' }, error: { padding: 10, background: '#f4deda', color: '#9d3e38' }, empty: { textAlign: 'center', color: theme.text.tertiary, padding: 40 },
  finding: { padding: 7, marginTop: 5, backgroundColor: '#fff4dc', color: '#735c24', borderRadius: 4 },
  diffLabel: { marginTop: 8, fontWeight: 600 },
  previous: { maxHeight: 180, overflow: 'auto', whiteSpace: 'pre-wrap', padding: 8, backgroundColor: theme.bg.content, border: `1px solid ${theme.border.light}` },
  editor: { width: '100%', minHeight: 220, boxSizing: 'border-box', padding: 8, marginTop: 7, border: `1px solid ${theme.border.light}`, backgroundColor: theme.bg.content, color: theme.text.primary, fontFamily: theme.fontMono },
};
