import { useState, useEffect } from 'react';
import { fetchReviews, resolveReview } from '../lib/api';
import { useProject } from '../contexts/ProjectContext';
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
                    <span key={i} style={styles.pageTag}>{p}</span>
                  ))}
                </div>
              )}
              <div style={styles.actions}>
                {item.options.map((opt, i) => (
                  <button
                    key={i}
                    style={styles.actionBtn}
                    onClick={() => handleResolve(item.id, opt.action)}
                  >
                    {opt.label}
                  </button>
                ))}
                {item.searchQueries && item.searchQueries.length > 0 && (
                  <button
                    style={{ ...styles.actionBtn, ...styles.researchBtn }}
                    onClick={() => handleResolve(item.id, 'deep_research')}
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
