import { useEffect, useState } from 'react';
import {
  acceptIngestJob, acceptResearchJob, deleteIngestJob, deleteResearchJob,
  fetchIngestJobs, fetchResearchJobs, rejectIngestJob, rejectResearchJob,
  retryIngestJob, retryResearchJob,
} from '../lib/api';
import { useProject } from '../contexts/ProjectContext';
import { theme } from '../lib/theme';

type Task = Record<string, any> & { kind: 'ingest' | 'research' };
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
      const [ingest, research] = await Promise.all([fetchIngestJobs(activeProjectId), fetchResearchJobs(activeProjectId)]);
      setTasks([
        ...ingest.map((task: any) => ({ ...task, kind: 'ingest' as const })),
        ...research.map((task: any) => ({ ...task, kind: 'research' as const })),
      ].sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0)));
      setError('');
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  };

  useEffect(() => { void load(); }, [activeProjectId]);
  const act = async (task: Task, action: 'accept' | 'reject' | 'retry' | 'delete') => {
    setBusy(task.id);
    try {
      if (action === 'accept') await (task.kind === 'ingest' ? acceptIngestJob(task.id, activeProjectId) : acceptResearchJob(task.id, activeProjectId));
      if (action === 'reject') await (task.kind === 'ingest' ? rejectIngestJob(task.id, activeProjectId) : rejectResearchJob(task.id, activeProjectId));
      if (action === 'retry') await (task.kind === 'ingest' ? retryIngestJob(task.id, () => undefined, activeProjectId) : retryResearchJob(task.id, () => undefined, activeProjectId));
      if (action === 'delete') {
        if (!window.confirm('删除这条任务记录及暂存文件？已写入的 Wiki 页面不会删除。')) return;
        await (task.kind === 'ingest' ? deleteIngestJob(task.id, activeProjectId) : deleteResearchJob(task.id, activeProjectId));
      }
      await load();
      window.dispatchEvent(new Event('wikiPagesUpdated'));
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(null); }
  };

  const visible = tasks.filter((task) => filter === 'all' || task.status === filter);
  return <div style={styles.container}>
    <div style={styles.header}><div><h2 style={styles.title}>任务中心</h2><p style={styles.desc}>恢复、审核和清理摄入及研究任务</p></div><button style={styles.btn} onClick={load}>刷新</button></div>
    <div style={styles.filters}>{['all', 'running', 'awaiting_review', 'failed', 'interrupted', 'accepted', 'rejected'].map((value) => <button key={value} style={{ ...styles.filter, ...(filter === value ? styles.active : {}) }} onClick={() => setFilter(value)}>{value === 'all' ? '全部' : statusLabel[value]}</button>)}</div>
    {error && <p style={styles.error}>{error}</p>}
    {visible.length === 0 ? <p style={styles.empty}>暂无任务</p> : visible.map((task) => <article key={`${task.kind}-${task.id}`} style={styles.card}>
      <div style={styles.cardHeader}><strong>{task.kind === 'ingest' ? task.filename : task.topic}</strong><span style={styles.badge}>{task.kind === 'ingest' ? '摄入' : '研究'} · {statusLabel[task.status] || task.status}</span></div>
      <div style={styles.meta}>{new Date(task.createdAt).toLocaleString()} · {task.message || task.step || ''}</div>
      {task.status === 'awaiting_review' && <details style={styles.details}><summary>查看待写入页面</summary>{task.result?.proposals?.map((page: any) => <div key={page.path} style={styles.page}>{page.title || page.path} · {page.path}</div>)}</details>}
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
};
