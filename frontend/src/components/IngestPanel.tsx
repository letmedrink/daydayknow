import { useState, useRef } from 'react';
import { ingestFile } from '../lib/api';

export function IngestPanel() {
  const [progress, setProgress] = useState<any[]>([]);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    setLoading(true);
    setProgress([]);
    setResult(null);

    try {
      const res = await ingestFile(file, (evt) => {
        setProgress((prev) => [...prev, evt]);
      });
      setResult(res);
    } catch (e: any) {
      setProgress((prev) => [...prev, { step: 'error', message: e.message }]);
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>文档摄入</h2>
      <p style={styles.desc}>上传文档，AI 自动提取知识并生成 wiki 页面</p>

      <div
        style={styles.dropzone}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
      >
        {loading ? (
          <p>处理中...</p>
        ) : (
          <p>拖拽文件到此处，或点击选择</p>
        )}
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.pptx,.docx,.txt,.md,.csv,.json"
          style={{ display: 'none' }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
      </div>

      {progress.length > 0 && (
        <div style={styles.progress}>
          {progress.map((evt, i) => (
            <div key={i} style={styles.progressItem}>
              <span style={styles.progressStep}>[{evt.step}]</span>
              <span>{evt.message}</span>
              <span style={styles.progressPct}>{Math.round((evt.progress || 0) * 100)}%</span>
            </div>
          ))}
        </div>
      )}

      {result && (
        <div style={styles.result}>
          <h3>摄入结果</h3>
          <p>写入页面: {result.files_written?.length || 0}</p>
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
  dropzone: {
    border: '2px dashed #c8bfb5',
    borderRadius: 12,
    padding: 40,
    textAlign: 'center',
    color: '#a09890',
    cursor: 'pointer',
    backgroundColor: '#faf6f1',
    transition: 'border-color 0.15s',
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
  progressStep: { fontWeight: 600, color: '#7a8b8f', minWidth: 80 },
  progressPct: { marginLeft: 'auto', color: '#8a8078' },
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
