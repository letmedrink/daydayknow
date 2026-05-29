import { useState } from 'react';
import { importContent } from '../lib/api';

export function ImportPanel({ onImported }: { onImported?: () => void }) {
  const [content, setContent] = useState('');
  const [sourceName, setSourceName] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ nodes: number; edges: number; error?: string } | null>(null);

  const handleImport = async () => {
    if (!content.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const data = await importContent(content.trim(), sourceName.trim() || undefined);
      setResult({ nodes: data.nodes.length, edges: data.edges.length, error: data.error });
      if (!data.error) {
        setContent('');
        setSourceName('');
        onImported?.();
      }
    } catch (err) {
      setResult({ nodes: 0, edges: 0, error: String(err) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>导入知识</h2>
      <p style={styles.desc}>粘贴文本内容，系统将自动提取知识概念并加入图谱。</p>

      <label style={styles.label}>来源名称（可选）</label>
      <input
        style={styles.input}
        value={sourceName}
        onChange={(e) => setSourceName(e.target.value)}
        placeholder="如：机器学习笔记"
      />

      <label style={styles.label}>文本内容</label>
      <textarea
        style={styles.textarea}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="粘贴要导入的文本内容..."
      />

      <button
        style={{ ...styles.btn, opacity: loading || !content.trim() ? 0.5 : 1 }}
        onClick={handleImport}
        disabled={loading || !content.trim()}
      >
        {loading ? '导入中...' : '导入'}
      </button>

      {result && (
        <div style={{ ...styles.result, color: result.error ? '#c97a6b' : '#7a8b8f' }}>
          {result.error
            ? result.error
            : `成功提取 ${result.nodes} 个概念、${result.edges} 条关系`}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    padding: '32px 48px',
    maxWidth: 720,
    margin: '0 auto',
  },
  title: {
    fontSize: 22,
    fontWeight: 600,
    color: '#4a443d',
    margin: '0 0 4px',
  },
  desc: {
    fontSize: 14,
    color: '#7a756d',
    margin: '0 0 24px',
  },
  label: {
    fontSize: 13,
    fontWeight: 500,
    color: '#58524a',
    marginBottom: 4,
  },
  input: {
    padding: '8px 12px',
    border: '1px solid #d5cec6',
    borderRadius: 6,
    fontSize: 14,
    marginBottom: 16,
    outline: 'none',
    backgroundColor: '#faf8f5',
    color: '#4a443d',
  },
  textarea: {
    flex: 1,
    minHeight: 200,
    padding: '12px',
    border: '1px solid #d5cec6',
    borderRadius: 6,
    fontSize: 14,
    resize: 'vertical',
    outline: 'none',
    marginBottom: 16,
    fontFamily: 'inherit',
    backgroundColor: '#faf8f5',
    color: '#4a443d',
  },
  btn: {
    padding: '10px 24px',
    backgroundColor: '#7a8b8f',
    color: '#f5f0eb',
    border: 'none',
    borderRadius: 6,
    fontSize: 14,
    fontWeight: 500,
    cursor: 'pointer',
    alignSelf: 'flex-start',
  },
  result: {
    marginTop: 16,
    fontSize: 14,
    padding: '10px 14px',
    backgroundColor: '#f5f0eb',
    borderRadius: 6,
  },
};
