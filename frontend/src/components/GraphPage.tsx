import { useState, useEffect, useRef, useMemo } from 'react';
import { fetchKnowledge } from '../lib/api';
import { KnowledgeGraph } from './KnowledgeGraph';
import type { KgNode, KgEdge } from '../types';

export function GraphPage() {
  const [allNodes, setAllNodes] = useState<KgNode[]>([]);
  const [allEdges, setAllEdges] = useState<KgEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  // Filter state
  const [selectedDomains, setSelectedDomains] = useState<Set<string>>(new Set());
  const [minConfidence, setMinConfidence] = useState(0);
  const [selectedRelations, setSelectedRelations] = useState<Set<string>>(new Set());

  // N-hop highlight state
  const [highlight, setHighlight] = useState<{ nodeId: string; hop: number } | null>(null);
  const [currentHop, setCurrentHop] = useState(1);

  useEffect(() => {
    fetchKnowledge()
      .then((data) => {
        setAllNodes(data.nodes);
        setAllEdges(data.edges);
        // Initialize filters to include all
        const domains = new Set<string>();
        const relations = new Set<string>();
        data.nodes.forEach((n) => { if (n.domain) domains.add(n.domain); });
        data.edges.forEach((e) => relations.add(e.relation_type));
        setSelectedDomains(domains);
        setSelectedRelations(relations);
      })
      .catch((err) => console.error('Failed to load knowledge:', err))
      .finally(() => setLoading(false));
  }, []);

  // Extract unique domains and relations for filter UI
  const domains = useMemo(() => {
    const d = new Set<string>();
    allNodes.forEach((n) => { if (n.domain) d.add(n.domain); });
    return [...d].sort();
  }, [allNodes]);

  const relations = useMemo(() => {
    const r = new Set<string>();
    allEdges.forEach((e) => r.add(e.relation_type));
    return [...r].sort();
  }, [allEdges]);

  // Apply filters
  const filteredNodes = useMemo(() => {
    return allNodes.filter((n) => {
      if (n.domain && !selectedDomains.has(n.domain)) return false;
      if (n.confidence < minConfidence) return false;
      return true;
    });
  }, [allNodes, selectedDomains, minConfidence]);

  const filteredNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  const filteredEdges = useMemo(() => {
    return allEdges.filter((e) => {
      if (!filteredNodeIds.has(e.from_node_id) || !filteredNodeIds.has(e.to_node_id)) return false;
      if (!selectedRelations.has(e.relation_type)) return false;
      return true;
    });
  }, [allEdges, filteredNodeIds, selectedRelations]);

  const toggleDomain = (d: string) => {
    setSelectedDomains((prev) => {
      const next = new Set(prev);
      if (next.has(d)) next.delete(d); else next.add(d);
      return next;
    });
  };

  const toggleRelation = (r: string) => {
    setSelectedRelations((prev) => {
      const next = new Set(prev);
      if (next.has(r)) next.delete(r); else next.add(r);
      return next;
    });
  };

  const handleNodeClick = (nodeId: string) => {
    setCurrentHop(1);
    setHighlight({ nodeId, hop: 1 });
  };

  const handleResetHighlight = () => {
    setHighlight(null);
    setCurrentHop(1);
  };

  const handleHopChange = (hop: number) => {
    if (highlight) {
      setCurrentHop(hop);
      setHighlight({ ...highlight, hop });
    }
  };

  const highlightedNode = highlight ? allNodes.find((n) => n.id === highlight.nodeId) : null;

  return (
    <div ref={containerRef} style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>知识图谱</h1>
        <span style={styles.stats}>
          {filteredNodes.length}/{allNodes.length} 个概念，{filteredEdges.length}/{allEdges.length} 条关系
        </span>
      </div>

      {/* Filter toolbar */}
      {!loading && allNodes.length > 0 && (
        <div style={styles.toolbar}>
          {/* Domain filter */}
          {domains.length > 0 && (
            <div style={styles.filterGroup}>
              <span style={styles.filterLabel}>领域:</span>
              {domains.map((d) => (
                <label key={d} style={styles.checkLabel}>
                  <input
                    type="checkbox"
                    checked={selectedDomains.has(d)}
                    onChange={() => toggleDomain(d)}
                    style={styles.checkbox}
                  />
                  {d}
                </label>
              ))}
            </div>
          )}

          {/* Confidence slider */}
          <div style={styles.filterGroup}>
            <span style={styles.filterLabel}>置信度 ≥ {minConfidence.toFixed(1)}</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.1}
              value={minConfidence}
              onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
              style={styles.slider}
            />
          </div>

          {/* Relation type filter */}
          {relations.length > 0 && (
            <div style={styles.filterGroup}>
              <span style={styles.filterLabel}>关系:</span>
              {relations.map((r) => (
                <label key={r} style={styles.checkLabel}>
                  <input
                    type="checkbox"
                    checked={selectedRelations.has(r)}
                    onChange={() => toggleRelation(r)}
                    style={styles.checkbox}
                  />
                  {r}
                </label>
              ))}
            </div>
          )}

          {/* N-hop controls */}
          {highlightedNode && (
            <div style={styles.filterGroup}>
              <span style={styles.filterLabel}>
                查看「{highlightedNode.name}」的
              </span>
              <button
                style={{ ...styles.hopBtn, ...(currentHop === 1 ? styles.hopBtnActive : {}) }}
                onClick={() => handleHopChange(1)}
              >
                1 跳邻居
              </button>
              <button
                style={{ ...styles.hopBtn, ...(currentHop === 2 ? styles.hopBtnActive : {}) }}
                onClick={() => handleHopChange(2)}
              >
                2 跳邻居
              </button>
              <button style={styles.resetBtn} onClick={handleResetHighlight}>
                重置
              </button>
            </div>
          )}
        </div>
      )}

      <div style={styles.graphArea}>
        {loading ? (
          <div style={styles.center}>加载中...</div>
        ) : filteredNodes.length === 0 ? (
          <div style={styles.center}>
            <p style={styles.emptyTitle}>{allNodes.length === 0 ? '暂无知识图谱' : '无匹配结果'}</p>
            <p style={styles.emptyHint}>
              {allNodes.length === 0
                ? '对话结束后系统会自动提取概念和关系'
                : '尝试调整筛选条件'}
            </p>
          </div>
        ) : (
          <KnowledgeGraph
            nodes={filteredNodes}
            edges={filteredEdges}
            height={(containerRef.current?.clientHeight || 600) - 60 - (highlightedNode ? 40 : 0)}
            highlight={highlight}
            onNodeClick={handleNodeClick}
            onResetHighlight={handleResetHighlight}
          />
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    height: '100vh',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#f5f0eb',
  },
  header: {
    display: 'flex',
    alignItems: 'baseline',
    gap: 12,
    padding: '16px 20px',
    borderBottom: '1px solid #d5ccc3',
    backgroundColor: '#eae3db',
  },
  title: {
    fontSize: 18,
    fontWeight: 700,
    color: '#4a443d',
    margin: 0,
  },
  stats: {
    fontSize: 13,
    color: '#8a8078',
  },
  toolbar: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: '4px 16px',
    padding: '8px 20px',
    borderBottom: '1px solid #e0d9d2',
    backgroundColor: '#ece6df',
    fontSize: 12,
  },
  filterGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    flexWrap: 'wrap',
  },
  filterLabel: {
    fontWeight: 500,
    color: '#58524a',
    whiteSpace: 'nowrap' as const,
  },
  checkLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: 3,
    color: '#58524a',
    cursor: 'pointer',
    padding: '2px 6px',
    borderRadius: 4,
    backgroundColor: '#f5f0eb',
    fontSize: 12,
  },
  checkbox: {
    accentColor: '#7a8b8f',
    margin: 0,
  },
  slider: {
    width: 80,
    accentColor: '#7a8b8f',
  },
  hopBtn: {
    padding: '3px 10px',
    border: '1px solid #d5cec6',
    borderRadius: 4,
    backgroundColor: '#f5f0eb',
    color: '#58524a',
    cursor: 'pointer',
    fontSize: 12,
  },
  hopBtnActive: {
    backgroundColor: '#7a8b8f',
    color: '#f5f0eb',
    borderColor: '#7a8b8f',
  },
  resetBtn: {
    padding: '3px 10px',
    border: '1px solid #c97a6b',
    borderRadius: 4,
    backgroundColor: 'transparent',
    color: '#c97a6b',
    cursor: 'pointer',
    fontSize: 12,
  },
  graphArea: {
    flex: 1,
    overflow: 'hidden',
  },
  center: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#a09890',
  },
  emptyTitle: { fontSize: 16, fontWeight: 600, color: '#8a8078', margin: 0 },
  emptyHint: { fontSize: 13, marginTop: 8 },
};
