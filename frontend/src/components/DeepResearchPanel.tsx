import { useState } from 'react';
import { deepResearch } from '../lib/api';

export function DeepResearchPanel() {
  const [topic, setTopic] = useState('');
  const [keywords, setKeywords] = useState('');
  const [progress, setProgress] = useState<any[]>([]);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleResearch = async () => {
    if (!topic.trim()) return;

    setLoading(true);
    setProgress([]);
    setResult(null);

    const kwList = keywords.split(/[,，\n]/).map((k) => k.trim()).filter(Boolean);

    try {
      const res = await deepResearch(
        topic,
        kwList.length > 0 ? kwList : undefined,
        (evt) => setProgress((prev) => [...prev, evt]),
      );
      setResult(res);
    } catch (e: any) {
      setProgress((prev) => [...prev, { step: 'error', message: e.message }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>深度研究</h2>
      <p style={styles.desc}>输入主题，AI 联网搜索并生成 wiki 页面</p>

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
          onClick={handleResearch}
          disabled={loading || !topic.trim()}
        >
          {loading ? '研究中...' : '开始研究'}
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
          <p>生成页面: {result.files_written?.length || 0}</p>
          <p>搜索结果: {result.search_results?.length || 0}</p>
          <p>审阅项: {result.reviews?.length || 0}</p>
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
};
