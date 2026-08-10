import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ingestFile, fetchReviews, fetchWikiPages } from '../lib/api';
import { usePreview } from '../contexts/PreviewContext';
import { useProject } from '../contexts/ProjectContext';
import { refreshWikiPagesCache } from './ChatWindow';
import { theme } from '../lib/theme';
import type { ReviewItem } from '../types';

const STEP_LABELS: Record<string, string> = {
  parse: '解析文档',
  cache: '检查缓存',
  images: '处理图片',
  analyze: 'AI 分析',
  generate: '生成 Wiki',
  write: '写入文件',
  reviews: '生成审阅项',
  done: '完成',
  error: '错误',
};

export function IngestPanel() {
  const [progress, setProgress] = useState(0);
  const [step, setStep] = useState('');
  const [message, setMessage] = useState('');
  const [result, setResult] = useState<any>(null);
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { activeProjectId } = useProject();

  // 摄入完成后自动加载审阅项
  useEffect(() => {
    if (result) {
      fetchReviews(activeProjectId)
        .then((data) => setReviews(data.filter((r: ReviewItem) => !r.resolved)))
        .catch(() => {});
    }
  }, [result, activeProjectId]);

  const handleFile = async (file: File) => {
    // 检查是否已导入过同名文件
    try {
      const data = await fetchWikiPages(activeProjectId);
      const allPages = data.pages || [];
      const baseName = file.name.replace(/\.[^/.]+$/, '');
      const existing = allPages.find((p: any) =>
        p.name?.replace(/\.md$/, '') === baseName ||
        p.path?.includes(baseName)
      );
      if (existing) {
        const ok = window.confirm(`"${file.name}" 已导入过（${existing.path}），是否重新导入？`);
        if (!ok) return;
      }
    } catch (_) {
      // 忽略检查失败，继续导入
    }

    setLoading(true);
    setProgress(0);
    setStep('');
    setMessage('');
    setResult(null);
    setReviews([]);

    try {
      const res = await ingestFile(file, (evt) => {
        setProgress(evt.progress || 0);
        setStep(evt.step || '');
        setMessage(evt.message || '');
      }, activeProjectId);
      setResult(res);
      setProgress(1);
      setStep('done');
      setMessage('摄入完成');
      // 刷新 wiki 页面缓存，确保链接可解析
      refreshWikiPagesCache(activeProjectId);
      window.dispatchEvent(new Event('wikiPagesUpdated'));
    } catch (e: any) {
      setStep('error');
      setMessage(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const { openPreview } = usePreview();

  const handleFileClick = (path: string) => {
    // 后端返回 wiki/xxx.md，API 期望 xxx.md
    const clean = path.replace(/^wiki\//, '');
    openPreview(clean);
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

      {/* 进度条 */}
      {(loading || result) && (
        <div style={styles.progressSection}>
          <div style={styles.progressBarOuter}>
            <div
              style={{
                ...styles.progressBarInner,
                width: `${Math.round(progress * 100)}%`,
                backgroundColor: step === 'error' ? '#c0392b' : '#7a8b8f',
              }}
            />
          </div>
          <div style={styles.progressInfo}>
            <span style={styles.progressStep}>
              {STEP_LABELS[step] || step}
            </span>
            <span style={styles.progressMessage}>{message}</span>
            <span style={styles.progressPct}>{Math.round(progress * 100)}%</span>
          </div>
        </div>
      )}

      {/* 摄入结果 */}
      {result && (
        <div style={styles.result}>
          <h3 style={styles.resultTitle}>摄入结果</h3>

          {/* 统计 */}
          <div style={styles.statsRow}>
            <div style={styles.statCard}>
              <span style={styles.statNum}>{result.files_written?.length || 0}</span>
              <span style={styles.statLabel}>Wiki 页面</span>
            </div>
            <div style={styles.statCard}>
              <span style={styles.statNum}>{result.reviews?.length || 0}</span>
              <span style={styles.statLabel}>待审阅</span>
            </div>
          </div>

          {/* 文件列表 - 可点击预览 */}
          {result.files_written?.length > 0 && (
            <div style={styles.section}>
              <h4 style={styles.sectionTitle}>生成的页面</h4>
              {result.files_written.map((f: string, i: number) => (
                <div
                  key={i}
                  style={styles.fileItem}
                  onClick={() => handleFileClick(f)}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = theme.accent;
                    e.currentTarget.style.color = theme.text.inverse;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = theme.bg.raised;
                    e.currentTarget.style.color = theme.text.primary;
                  }}
                >
                  <span style={styles.fileIcon}>📄</span>
                  <span style={styles.filePath}>{f}</span>
                  <span style={styles.fileArrow}>→</span>
                </div>
              ))}
            </div>
          )}

          {/* 审阅项预览 */}
          {reviews.length > 0 && (
            <div style={styles.section}>
              <h4 style={styles.sectionTitle}>
                待审阅内容
                <button
                  style={styles.viewAllBtn}
                  onClick={() => navigate('/reviews')}
                >
                  查看全部 →
                </button>
              </h4>
              {reviews.slice(0, 3).map((item) => (
                <div key={item.id} style={styles.reviewCard}>
                  <div style={styles.reviewHeader}>
                    <span style={{
                      ...styles.reviewBadge,
                      backgroundColor: reviewTypeColor(item.type),
                    }}>
                      {reviewTypeLabel(item.type)}
                    </span>
                    <span style={styles.reviewTitle}>{item.title}</span>
                  </div>
                  {item.description && (
                    <p style={styles.reviewDesc}>{item.description}</p>
                  )}
                </div>
              ))}
              {reviews.length > 3 && (
                <div style={styles.moreHint}>
                  还有 {reviews.length - 3} 项待审阅...
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function reviewTypeLabel(type: string): string {
  const map: Record<string, string> = {
    contradiction: '矛盾',
    duplicate: '重复',
    'missing-page': '缺失页',
    suggestion: '建议',
  };
  return map[type] || type;
}

function reviewTypeColor(type: string): string {
  switch (type) {
    case 'contradiction': return '#c0392b';
    case 'duplicate': return '#e67e22';
    case 'missing-page': return '#2980b9';
    case 'suggestion': return '#27ae60';
    default: return '#7a8b8f';
  }
}

const styles: Record<string, React.CSSProperties> = {
  container: { flex: 1, padding: 28, maxWidth: 720, margin: '0 auto', overflowY: 'auto', fontFamily: theme.font },
  title: { fontSize: 20, fontWeight: 700, color: theme.text.primary, margin: '0 0 8px', letterSpacing: '-0.3px' },
  desc: { fontSize: 14, color: theme.text.secondary, marginBottom: 20 },
  dropzone: {
    border: `2px dashed ${theme.border.medium}`,
    borderRadius: theme.radius.lg, padding: 40,
    textAlign: 'center', color: theme.text.tertiary,
    cursor: 'pointer', backgroundColor: theme.bg.raised,
    transition: 'border-color 0.15s',
  },
  progressSection: { marginTop: 16 },
  progressBarOuter: {
    height: 4, backgroundColor: theme.bg.raised,
    borderRadius: 2, overflow: 'hidden',
  },
  progressBarInner: {
    height: '100%', borderRadius: 2,
    transition: 'width 0.3s ease',
  },
  progressInfo: {
    display: 'flex', alignItems: 'center',
    gap: 8, marginTop: 8, fontSize: 13,
  },
  progressStep: { fontWeight: 600, color: theme.accent },
  progressMessage: { color: theme.text.primary, flex: 1 },
  progressPct: { color: theme.text.secondary, fontWeight: 500 },
  result: { marginTop: 20 },
  resultTitle: { fontSize: 16, fontWeight: 700, color: theme.text.primary, margin: '0 0 12px' },
  statsRow: { display: 'flex', gap: 12, marginBottom: 16 },
  statCard: {
    flex: 1, display: 'flex', flexDirection: 'column',
    alignItems: 'center', padding: '14px 0',
    backgroundColor: theme.bg.raised, borderRadius: theme.radius.md,
    border: `1px solid ${theme.border.light}`,
  },
  statNum: { fontSize: 24, fontWeight: 700, color: theme.text.primary },
  statLabel: { fontSize: 12, color: theme.text.secondary, marginTop: 2 },
  section: { marginBottom: 16 },
  sectionTitle: {
    fontSize: 14, fontWeight: 600, color: theme.text.primary,
    margin: '0 0 8px', display: 'flex',
    alignItems: 'center', justifyContent: 'space-between',
  },
  fileItem: {
    display: 'flex', alignItems: 'center', gap: 8,
    padding: '8px 12px', backgroundColor: theme.bg.raised,
    borderRadius: theme.radius.sm, marginTop: 4,
    fontSize: 13, color: theme.text.primary,
    cursor: 'pointer', transition: 'all 0.12s',
    border: `1px solid ${theme.border.light}`,
  },
  fileIcon: { fontSize: 14 },
  filePath: { flex: 1, fontFamily: theme.fontMono, fontSize: 12 },
  fileArrow: { color: theme.text.tertiary, fontSize: 14 },
  viewAllBtn: {
    background: 'none', border: 'none',
    color: theme.accent, fontSize: 12,
    cursor: 'pointer', fontWeight: 500,
  },
  reviewCard: {
    padding: '10px 12px', backgroundColor: theme.bg.raised,
    borderRadius: theme.radius.sm, marginTop: 6,
    border: `1px solid ${theme.border.light}`,
  },
  reviewHeader: { display: 'flex', alignItems: 'center', gap: 8 },
  reviewBadge: {
    padding: '1px 8px', borderRadius: 10,
    fontSize: 11,
    color: '#fff',
    fontWeight: 600,
  },
  reviewTitle: { fontSize: 13, fontWeight: 600, color: theme.text.primary },
  reviewDesc: { fontSize: 12, color: theme.text.secondary, margin: '6px 0 0', lineHeight: 1.5 },
  moreHint: { fontSize: 12, color: theme.text.tertiary, textAlign: 'center', padding: '8px 0' },
};
