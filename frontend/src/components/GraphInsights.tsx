import { useState, useEffect } from 'react';
import { fetchGraphInsights } from '../lib/api';
import type { GraphInsights as GraphInsightsType, SurprisingConnection, KnowledgeGap } from '../types';

interface GraphInsightsProps {
  onResearchClick: (query: string) => void;
  onNodeHighlight: (nodeId: string) => void;
}

export function GraphInsights({ onResearchClick, onNodeHighlight }: GraphInsightsProps) {
  const [insights, setInsights] = useState<GraphInsightsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'surprising' | 'gaps'>('surprising');

  useEffect(() => {
    fetchGraphInsights()
      .then(setInsights)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div style={styles.container}><div style={styles.loading}>分析图谱中...</div></div>;
  }

  if (!insights) return null;

  const { surprisingConnections, knowledgeGaps } = insights;
  const hasContent = surprisingConnections.length > 0 || knowledgeGaps.length > 0;

  if (!hasContent) {
    return (
      <div style={styles.container}>
        <div style={styles.empty}>图谱连接良好，暂无发现</div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.tabs}>
        <button
          style={{ ...styles.tab, ...(activeTab === 'surprising' ? styles.tabActive : {}) }}
          onClick={() => setActiveTab('surprising')}
        >
          意外连接 ({surprisingConnections.length})
        </button>
        <button
          style={{ ...styles.tab, ...(activeTab === 'gaps' ? styles.tabActive : {}) }}
          onClick={() => setActiveTab('gaps')}
        >
          知识缺口 ({knowledgeGaps.length})
        </button>
      </div>

      <div style={styles.content}>
        {activeTab === 'surprising' && surprisingConnections.map((item, i) => (
          <SurprisingCard key={i} item={item} onNodeHighlight={onNodeHighlight} />
        ))}
        {activeTab === 'gaps' && knowledgeGaps.map((item, i) => (
          <GapCard key={i} item={item} onResearchClick={onResearchClick} onNodeHighlight={onNodeHighlight} />
        ))}
      </div>
    </div>
  );
}

function SurprisingCard({ item, onNodeHighlight }: { item: SurprisingConnection; onNodeHighlight: (id: string) => void }) {
  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>
        <span style={styles.badge}>意外连接</span>
        <span style={styles.score}>得分 {item.score}</span>
      </div>
      <div style={styles.cardBody}>
        <span style={styles.link} onClick={() => onNodeHighlight(item.source)}>{item.sourceTitle}</span>
        <span style={styles.arrow}> ↔ </span>
        <span style={styles.link} onClick={() => onNodeHighlight(item.target)}>{item.targetTitle}</span>
      </div>
      <div style={styles.reasons}>
        {item.reasons.map((r, i) => <span key={i} style={styles.reasonTag}>{r}</span>)}
      </div>
    </div>
  );
}

function GapCard({ item, onResearchClick, onNodeHighlight }: { item: KnowledgeGap; onResearchClick: (q: string) => void; onNodeHighlight: (id: string) => void }) {
  const typeLabels: Record<string, string> = {
    isolated: '孤立节点',
    sparse_community: '稀疏社区',
    bridge: '桥接节点',
  };

  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>
        <span style={{ ...styles.badge, ...styles.badgeGap }}>{typeLabels[item.type] || item.type}</span>
        {item.title && (
          <span style={styles.link} onClick={() => item.nodeId && onNodeHighlight(item.nodeId)}>
            {item.title}
          </span>
        )}
      </div>
      <div style={styles.suggestion}>{item.suggestion}</div>
      <button style={styles.researchBtn} onClick={() => onResearchClick(item.searchQuery)}>
        深度研究
      </button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex', flexDirection: 'column', height: '100%',
    backgroundColor: '#ece6df', borderLeft: '1px solid #d5ccc3',
    width: 280, minWidth: 280,
  },
  loading: { padding: 20, textAlign: 'center', color: '#8a8078', fontSize: 13 },
  empty: { padding: 20, textAlign: 'center', color: '#8a8078', fontSize: 13 },
  tabs: {
    display: 'flex', borderBottom: '1px solid #d5ccc3',
  },
  tab: {
    flex: 1, padding: '8px 0', border: 'none', backgroundColor: 'transparent',
    color: '#8a8078', fontSize: 12, fontWeight: 600, cursor: 'pointer',
    borderBottom: '2px solid transparent',
  },
  tabActive: { color: '#4a443d', borderBottomColor: '#7a8b8f' },
  content: { flex: 1, overflowY: 'auto', padding: 10 },
  card: {
    backgroundColor: '#f5f0eb', borderRadius: 8, padding: 10,
    marginBottom: 8, border: '1px solid #d5ccc3',
  },
  cardHeader: {
    display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6,
  },
  badge: {
    fontSize: 10, fontWeight: 600, padding: '2px 6px', borderRadius: 4,
    backgroundColor: '#7a8b8f', color: '#f5f0eb',
  },
  badgeGap: { backgroundColor: '#c97a6b' },
  score: { fontSize: 11, color: '#8a8078' },
  cardBody: { fontSize: 13, color: '#4a443d', marginBottom: 4 },
  link: {
    color: '#7a8b8f', cursor: 'pointer', textDecoration: 'underline',
    textDecorationStyle: 'dotted',
  },
  arrow: { color: '#8a8078' },
  reasons: { display: 'flex', flexWrap: 'wrap', gap: 4 },
  reasonTag: {
    fontSize: 10, padding: '1px 6px', borderRadius: 4,
    backgroundColor: '#e0d9d2', color: '#6b5b4f',
  },
  suggestion: { fontSize: 12, color: '#58524a', marginBottom: 8, lineHeight: 1.4 },
  researchBtn: {
    padding: '4px 10px', borderRadius: 4, border: '1px solid #7a8b8f',
    backgroundColor: 'transparent', color: '#7a8b8f', fontSize: 11,
    fontWeight: 600, cursor: 'pointer',
  },
};
