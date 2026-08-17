import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { acceptResearchJob, deepResearch, fetchSettings, rejectResearchJob } from '../lib/api';
import { useProject } from '../contexts/ProjectContext';
import { refreshWikiPagesCache } from './ChatWindow';

export function DeepResearchPanel() {
  const { activeProjectId } = useProject();
  const [topic, setTopic] = useState('');
  const [keywords, setKeywords] = useState('');
  const [progress, setProgress] = useState<any[]>([]);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [searchConfigured, setSearchConfigured] = useState<boolean | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [searchParams] = useSearchParams();
  const reviewId = searchParams.get('review_id') || undefined;

  useEffect(() => {
    setTopic(searchParams.get('topic') || '');
    setKeywords(searchParams.get('keywords') || '');
  }, [searchParams]);

  useEffect(() => {
    fetchSettings()
      .then((settings) => setSearchConfigured(Boolean(settings.searchApiConfig?.provider && settings.searchApiConfig?.has_api_key)))
      .catch(() => setSearchConfigured(false));
  }, []);

  const handleResearch = async () => {
    if (!topic.trim()) return;

    setLoading(true);
    setProgress([]);
    setResult(null);
    const controller = new AbortController();
    abortRef.current?.abort();
    abortRef.current = controller;

    const kwList = keywords.split(/[,，\n]/).map((k) => k.trim()).filter(Boolean);

    try {
      const res = await deepResearch(
        topic,
        kwList.length > 0 ? kwList : undefined,
        (evt) => setProgress((prev) => [...prev, evt]),
        activeProjectId,
        controller.signal,
        reviewId,
      );
      setResult(res);
    } catch (e: any) {
      if (e.name !== 'AbortError') setProgress((prev) => [...prev, { step: 'error', message: e.message }]);
    } finally {
      abortRef.current = null;
      setLoading(false);
    }
  };

  const acceptResult = async () => {
    if (!result?.job?.id) return;
    setLoading(true);
    try {
      const job = await acceptResearchJob(result.job.id, activeProjectId);
      setResult(job.result);
      refreshWikiPagesCache(activeProjectId);
      window.dispatchEvent(new Event('wikiPagesUpdated'));
      setProgress((prev) => [...prev, { step: 'done', message: '已接受并写入 Wiki' }]);
    } catch (e: any) {
      setProgress((prev) => [...prev, { step: 'error', message: e.message }]);
    } finally { setLoading(false); }
  };

  const rejectResult = async () => {
    if (!result?.job?.id || !window.confirm('拒绝后 Wiki 不会被修改。继续？')) return;
    setLoading(true);
    try {
      await rejectResearchJob(result.job.id, activeProjectId);
      setResult(null);
      setProgress((prev) => [...prev, { step: 'done', message: '已拒绝，Wiki 未发生变化' }]);
    } catch (e: any) {
      setProgress((prev) => [...prev, { step: 'error', message: e.message }]);
    } finally { setLoading(false); }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>深度研究</h2>
      <p style={styles.desc}>输入主题，AI 联网搜索并生成 wiki 页面</p>
      {reviewId && <p style={styles.linkedHint}>此研究由审阅项发起，只有接受结果后审阅项才会结案。</p>}
      {searchConfigured === false && <p style={styles.errorHint}>请先在设置页配置 Tavily 或 SerpApi 及 API Key。</p>}

      <div style={styles.form}>
        <div style={styles.field}>
          <label style={styles.label}>研究主题</label>
          <input
            style={styles.input}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="例如：量子计算的最新进展"
            disabled={loading}
          />
        </div>

        <div style={styles.field}>
          <label style={styles.label}>搜索关键词（可选，逗号分隔）</label>
          <input
            style={styles.input}
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="关键词1, 关键词2, 关键词3"
            disabled={loading}
          />
        </div>

        <button
          style={styles.submitBtn}
          onClick={loading ? () => abortRef.current?.abort() : handleResearch}
          disabled={!loading && (!topic.trim() || searchConfigured !== true)}
        >
          {loading ? '停止研究' : '开始研究'}
        </button>
      </div>

      {progress.length > 0 && (
        <div style={styles.progress}>
          {progress.map((evt, i) => (
            <div key={i} style={styles.progressItem}>
              <span style={styles.progressStep}>[{evt.step}]</span>
              <span>{evt.message}</span>
            </div>
          ))}
        </div>
      )}

      {result && (
        <div style={styles.result}>
          <h3>研究结果</h3>
          {result.status === 'awaiting_review' && (
            <div style={styles.actions}>
              <span>结果尚未写入 Wiki</span>
              <button style={styles.acceptBtn} onClick={acceptResult} disabled={loading}>接受研究</button>
              <button style={styles.rejectBtn} onClick={rejectResult} disabled={loading}>拒绝</button>
            </div>
          )}
          <p>待生成页面: {result.proposals?.length || result.files_written?.length || 0}</p>
          <p>搜索结果: {result.search_results?.length || 0}</p>
          <p>审阅项: {result.reviews?.length || 0}</p>
          {result.search_results?.length > 0 && (
            <details style={styles.details}>
              <summary>查看搜索来源</summary>
              {result.search_results.map((source: any, i: number) => (
                <div key={i} style={styles.sourceItem}>
                  {source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.title || source.url}</a> : <span>{source.title}</span>}
                  <p>{source.snippet}</p>
                </div>
              ))}
            </details>
          )}
          {result.proposals?.map((page: any) => (
            <details key={page.path} style={styles.details}>
              <summary>{page.title} · {page.path}{page.replaces_existing ? ' （将合并现有页）' : ''}</summary>
              <pre style={styles.preview}>{page.content}</pre>
            </details>
          ))}
          {result.files_written?.map((f: string, i: number) => (
            <div key={i} style={styles.fileItem}>{f}</div>
          ))}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { flex: 1, padding: 24, maxWidth: 700, margin: '0 auto', overflowY: 'auto' },
  title: { fontSize: 20, fontWeight: 700, color: '#4a443d', margin: '0 0 8px' },
  desc: { fontSize: 14, color: '#8a8078', marginBottom: 20 },
  form: {
    padding: 20,
    backgroundColor: '#eae3db',
    borderRadius: 8,
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  field: { display: 'flex', flexDirection: 'column', gap: 4 },
  label: { fontSize: 13, color: '#6b5b4f', fontWeight: 600 },
  input: {
    padding: '10px 14px',
    border: '1px solid #c8bfb5',
    borderRadius: 8,
    fontSize: 14,
    backgroundColor: '#f5f0eb',
    color: '#4a443d',
    outline: 'none',
  },
  submitBtn: {
    padding: '10px 24px',
    backgroundColor: '#7a8b8f',
    color: '#f5f0eb',
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
    alignSelf: 'flex-start',
  },
  progress: {
    marginTop: 16,
    padding: 12,
    backgroundColor: '#eae3db',
    borderRadius: 8,
    fontSize: 13,
  },
  progressItem: {
    display: 'flex',
    gap: 8,
    padding: '4px 0',
    borderBottom: '1px solid #d5ccc3',
  },
  progressStep: { fontWeight: 600, color: '#7a8b8f', minWidth: 100 },
  result: {
    marginTop: 16,
    padding: 16,
    backgroundColor: '#eae3db',
    borderRadius: 8,
    fontSize: 14,
  },
  fileItem: {
    padding: '4px 8px',
    backgroundColor: '#d5ccc3',
    borderRadius: 4,
    marginTop: 4,
    fontSize: 13,
  },
  linkedHint: { padding: 10, backgroundColor: '#e5ddd3', color: '#6b5b4f', borderRadius: 6, fontSize: 13, marginBottom: 12 },
  errorHint: { padding: 10, backgroundColor: '#f4deda', color: '#9d3e38', borderRadius: 6, fontSize: 13, marginBottom: 12 },
  actions: { display: 'flex', alignItems: 'center', gap: 8, padding: 10, marginBottom: 10, border: '1px solid #c8bfb5', borderRadius: 6 },
  acceptBtn: { marginLeft: 'auto', padding: '6px 10px', border: 'none', borderRadius: 5, color: '#fff', backgroundColor: '#27845b', cursor: 'pointer' },
  rejectBtn: { padding: '6px 10px', border: 'none', borderRadius: 5, color: '#fff', backgroundColor: '#b84a45', cursor: 'pointer' },
  details: { marginTop: 10, padding: 8, backgroundColor: '#f5f0eb', borderRadius: 5 },
  sourceItem: { padding: 8, borderBottom: '1px solid #d5ccc3', lineHeight: 1.5 },
  preview: { whiteSpace: 'pre-wrap', maxHeight: 400, overflow: 'auto', fontSize: 12, marginTop: 8 },
};
