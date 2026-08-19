import { useState, useEffect } from 'react';
import { fetchReviews, resolveReview } from '../lib/api';
import { useProject } from '../contexts/ProjectContext';
import { useNavigate } from 'react-router-dom';
import { usePreview } from '../contexts/PreviewContext';
import type { ReviewItem } from '../types';

const TYPE_LABELS: Record<string, string> = {
  contradiction: '矛盾',
  duplicate: '重复',
  'missing-page': '缺失页',
  suggestion: '建议',
};

export function ReviewPanel() {
  const { activeProjectId } = useProject();
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { openPreview } = usePreview();

  useEffect(() => {
    loadReviews();
  }, [activeProjectId]);

  const loadReviews = async () => {
    setLoading(true);
    try {
      const data = await fetchReviews(activeProjectId);
      setReviews(data.filter((r: ReviewItem) => !r.resolved));
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const startReviewWork = (item: ReviewItem, action: string) => {
    if (action === '跳过' || action === 'skip') {
      void handleResolve(item.id, 'skip');
      return;
    }
    const params = new URLSearchParams({ topic: item.title, review_id: item.id });
    if (item.searchQueries?.length) params.set('keywords', item.searchQueries.join(','));
    navigate(`/research?${params.toString()}`);
  };

  const createMissingPage = async (item: ReviewItem) => {
    const title = item.title.replace(/^缺失[:：]?\s*/, '') || '待补充页面';
    const path = window.prompt('新页面路径：', `concepts/${title.replace(/[\\/:*?"<>|]/g, '-')}.md`)?.trim();
    if (!path) return;
    const content = `---\ntitle: ${title}\ntype: concept\ntags: []\n---\n\n# ${title}\n\n${item.description || ''}\n`;
    try {
      await resolveReview(item.id, 'create_page', activeProjectId, { path, content });
      setReviews((prev) => prev.filter((review) => review.id !== item.id));
      window.dispatchEvent(new Event('wikiPagesUpdated'));
      openPreview(path);
      navigate('/wiki');
    } catch (e) { console.error(e); }
  };

  const mergeDuplicate = async (item: ReviewItem) => {
    const paths = item.affectedPages.map((path) => path.replace(/^wiki\//, ''));
    if (paths.length < 2) return;
    const target = window.prompt('保留哪个页面作为目标？', paths[0])?.trim();
    if (!target || !paths.includes(target)) return;
    const sources = paths.filter((path) => path !== target);
    if (!window.confirm(`把 ${sources.join('、')} 合并到 ${target}，并修复相关链接？`)) return;
    try {
      await resolveReview(item.id, 'merge_pages', activeProjectId, { target_path: target, source_paths: sources });
      setReviews((prev) => prev.filter((review) => review.id !== item.id));
      window.dispatchEvent(new Event('wikiPagesUpdated'));
      openPreview(target);
      navigate('/wiki');
    } catch (e) { console.error(e); }
  };

  const openAffectedPage = (item: ReviewItem) => {
    const path = item.affectedPages[0]?.replace(/^wiki\//, '');
    if (path) { openPreview(path); navigate('/wiki'); }
  };

  const handleResolve = async (id: string, action: string) => {
    try {
      await resolveReview(id, action, activeProjectId);
      setReviews((prev) => prev.filter((r) => r.id !== id));
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>审阅项</h2>
      <p style={styles.desc}>摄入过程中发现的需要人工判断的内容</p>

      {loading ? (
        <p style={styles.empty}>加载中...</p>
      ) : reviews.length === 0 ? (
        <p style={styles.empty}>暂无待审阅项</p>
      ) : (
        <div style={styles.list}>
          {reviews.map((item) => (
            <div key={item.id} style={styles.card}>
              <div style={styles.cardHeader}>
                <span style={{
                  ...styles.typeBadge,
                  backgroundColor: typeColor(item.type),
                }}>
                  {TYPE_LABELS[item.type] || item.type}
                </span>
                <span style={styles.cardTitle}>{item.title}</span>
              </div>
              {item.description && (
                <p style={styles.cardDesc}>{item.description}</p>
              )}
              {item.affectedPages.length > 0 && (
                <div style={styles.pages}>
                  相关页面: {item.affectedPages.map((p, i) => (
                    <button key={i} style={styles.pageTag} onClick={() => openPreview(p.replace(/^wiki\//, ''))}>{p}</button>
                  ))}
                </div>
              )}
              <div style={styles.actions}>
                {item.type === 'missing-page' && <button style={styles.actionBtn} onClick={() => createMissingPage(item)}>创建页面</button>}
                {item.type === 'duplicate' && item.affectedPages.length >= 2 && <button style={styles.actionBtn} onClick={() => mergeDuplicate(item)}>合并页面</button>}
                {(item.type === 'contradiction' || item.type === 'suggestion') && item.affectedPages.length > 0 && <button style={styles.actionBtn} onClick={() => openAffectedPage(item)}>打开页面处理</button>}
                <button style={styles.actionBtn} onClick={() => handleResolve(item.id, 'resolved_manually')}>标记已处理</button>
                <button style={styles.actionBtn} onClick={() => handleResolve(item.id, 'skip')}>跳过</button>
                {item.searchQueries && item.searchQueries.length > 0 && (
                  <button
                    style={{ ...styles.actionBtn, ...styles.researchBtn }}
                    onClick={() => startReviewWork(item, 'deep_research')}
                  >
                    深度研究
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function typeColor(type: string): string {
  switch (type) {
    case 'contradiction': return '#c0392b';
    case 'duplicate': return '#e67e22';
    case 'missing-page': return '#2980b9';
    case 'suggestion': return '#27ae60';
    default: return '#7a8b8f';
  }
}

const styles: Record<string, React.CSSProperties> = {
  container: { flex: 1, padding: 24, maxWidth: 700, margin: '0 auto', overflowY: 'auto' },
  title: { fontSize: 20, fontWeight: 700, color: '#4a443d', margin: '0 0 8px' },
  desc: { fontSize: 14, color: '#8a8078', marginBottom: 20 },
  empty: { color: '#a09890', textAlign: 'center', padding: 40 },
  list: { display: 'flex', flexDirection: 'column', gap: 12 },
  card: {
    padding: 16,
    backgroundColor: '#eae3db',
    borderRadius: 8,
    border: '1px solid #d5ccc3',
  },
  cardHeader: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 },
  typeBadge: {
    padding: '2px 10px',
    borderRadius: 10,
    fontSize: 11,
    color: '#fff',
    fontWeight: 600,
  },
  cardTitle: { fontSize: 15, fontWeight: 600, color: '#4a443d' },
  cardDesc: { fontSize: 13, color: '#6b5b4f', margin: '8px 0', lineHeight: 1.5 },
  pages: { fontSize: 12, color: '#8a8078', marginBottom: 8 },
  pageTag: {
    display: 'inline-block',
    padding: '1px 6px',
    backgroundColor: '#d5ccc3',
    borderRadius: 4,
    fontSize: 11,
    margin: '0 2px',
    border: 'none', cursor: 'pointer', color: '#6b5b4f',
  },
  actions: { display: 'flex', gap: 8, marginTop: 8 },
  actionBtn: {
    padding: '6px 14px',
    borderRadius: 6,
    border: '1px solid #c8bfb5',
    backgroundColor: '#f5f0eb',
    color: '#6b5b4f',
    fontSize: 13,
    cursor: 'pointer',
  },
  researchBtn: {
    backgroundColor: '#7a8b8f',
    color: '#f5f0eb',
    border: 'none',
  },
};
