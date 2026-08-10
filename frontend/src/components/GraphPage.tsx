import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { fetchWikiGraph, searchGraph, deepResearch } from '../lib/api';
import { useProject } from '../contexts/ProjectContext';
import { KnowledgeGraph } from './KnowledgeGraph';
import { GraphInsights } from './GraphInsights';
import type { WikiGraphNode, WikiGraphEdge } from '../types';

export function GraphPage() {
  const { activeProjectId } = useProject();
  const [allNodes, setAllNodes] = useState<WikiGraphNode[]>([]);
  const [allEdges, setAllEdges] = useState<WikiGraphEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [highlight, setHighlight] = useState<{ nodeId: string; hop: number } | null>(null);
  const [currentHop, setCurrentHop] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Set<string>>(new Set());
  const [hideIsolated, setHideIsolated] = useState(false);
  const [showInsights, setShowInsights] = useState(false);

  useEffect(() => {
    fetchWikiGraph(activeProjectId)
      .then((data) => {
        setAllNodes(data.nodes);
        setAllEdges(data.edges);
        const types = new Set<string>();
        data.nodes.forEach((n) => types.add(n.type));
        setSelectedTypes(types);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const types = useMemo(() => {
    const t = new Set<string>();
    allNodes.forEach((n) => t.add(n.type));
    return [...t].sort();
  }, [allNodes]);

  // 搜索
  const handleSearch = useCallback(async (q: string) => {
    setSearchQuery(q);
    if (!q.trim()) {
      setSearchResults(new Set());
      return;
    }
    try {
      const result = await searchGraph(q, activeProjectId);
      setSearchResults(new Set(result.nodes.map((n: any) => n.id)));
    } catch {
      setSearchResults(new Set());
    }
  }, []);

  // 过滤
  const filteredNodes = useMemo(() => {
    let nodes = allNodes.filter((n) => selectedTypes.has(n.type));

    // 隐藏孤立节点
    if (hideIsolated) {
      const connectedIds = new Set<string>();
      for (const e of allEdges) {
        connectedIds.add(e.source);
        connectedIds.add(e.target);
      }
      nodes = nodes.filter((n) => connectedIds.has(n.id));
    }

    return nodes;
  }, [allNodes, selectedTypes, hideIsolated, allEdges]);

  const filteredNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  const filteredEdges = useMemo(() => {
    return allEdges.filter((e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target));
  }, [allEdges, filteredNodeIds]);

  // 搜索高亮
  const effectiveHighlight = useMemo(() => {
    if (searchResults.size > 0) {
      return { nodeId: [...searchResults][0], hop: 0, searchIds: searchResults };
    }
    return highlight;
  }, [searchResults, highlight]);

  const toggleType = (t: string) => {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t); else next.add(t);
      return next;
    });
  };

  const handleNodeClick = (nodeId: string) => {
    setSearchResults(new Set());
    setCurrentHop(1);
    setHighlight({ nodeId, hop: 1 });
  };

  const handleResetHighlight = () => {
    setHighlight(null);
    setCurrentHop(1);
    setSearchResults(new Set());
    setSearchQuery('');
  };

  const handleHopChange = (hop: number) => {
    if (highlight) {
      setCurrentHop(hop);
      setHighlight({ ...highlight, hop });
    }
  };

  const handleResearchFromInsights = (query: string) => {
    deepResearch(query, undefined, undefined, activeProjectId).catch(console.error);
  };

  const handleHighlightFromInsights = (nodeId: string) => {
    setSearchResults(new Set());
    setCurrentHop(1);
    setHighlight({ nodeId, hop: 1 });
  };

  const highlightedNode = highlight ? allNodes.find((n) => n.id === highlight.nodeId) : null;

  return (
    <div ref={containerRef} style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>知识图谱</h1>
        <span style={styles.stats}>
          {filteredNodes.length}/{allNodes.length} 个节点，{filteredEdges.length}/{allEdges.length} 条关系
        </span>
      </div>

      {!loading && allNodes.length > 0 && (
        <div style={styles.toolbar}>
          {/* 搜索 */}
          <div style={styles.searchBox}>
            <input
              style={styles.searchInput}
              placeholder="搜索节点..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
            />
            {searchResults.size > 0 && (
              <span style={styles.searchCount}>{searchResults.size} 个匹配</span>
            )}
          </div>

          {/* 类型过滤 */}
          {types.length > 0 && (
            <div style={styles.filterGroup}>
              <span style={styles.filterLabel}>类型:</span>
              {types.map((t) => (
                <label key={t} style={styles.checkLabel}>
                  <input
                    type="checkbox"
                    checked={selectedTypes.has(t)}
                    onChange={() => toggleType(t)}
                    style={styles.checkbox}
                  />
                  {t}
                </label>
              ))}
            </div>
          )}

          {/* 过滤选项 */}
          <div style={styles.filterGroup}>
            <label style={styles.checkLabel}>
              <input
                type="checkbox"
                checked={hideIsolated}
                onChange={() => setHideIsolated(!hideIsolated)}
                style={styles.checkbox}
              />
              隐藏孤立节点
            </label>
            <button
              style={{ ...styles.hopBtn, ...(showInsights ? styles.hopBtnActive : {}) }}
              onClick={() => setShowInsights(!showInsights)}
            >
              洞察
            </button>
          </div>

          {/* 高亮控制 */}
          {highlightedNode && (
            <div style={styles.filterGroup}>
              <span style={styles.filterLabel}>查看「{highlightedNode.title}」的</span>
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
              <button style={styles.resetBtn} onClick={handleResetHighlight}>重置</button>
            </div>
          )}
        </div>
      )}

      <div style={styles.mainArea}>
        <div style={styles.graphArea}>
          {loading ? (
            <div style={styles.center}>加载中...</div>
          ) : filteredNodes.length === 0 ? (
            <div style={styles.center}>
              <p style={styles.emptyTitle}>{allNodes.length === 0 ? '暂无知识图谱' : '无匹配结果'}</p>
              <p style={styles.emptyHint}>
                {allNodes.length === 0 ? '上传文档或对话后自动生成知识图谱' : '尝试调整筛选条件'}
              </p>
            </div>
          ) : (
            <KnowledgeGraph
              nodes={filteredNodes}
              edges={filteredEdges}
              height={(containerRef.current?.clientHeight || 600) - 60}
              highlight={effectiveHighlight}
              onNodeClick={handleNodeClick}
              onResetHighlight={handleResetHighlight}
            />
          )}
        </div>

        {showInsights && allNodes.length > 0 && (
          <GraphInsights
            onResearchClick={handleResearchFromInsights}
            onNodeHighlight={handleHighlightFromInsights}
          />
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { flex: 1, height: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: '#f5f0eb' },
  header: {
    display: 'flex', alignItems: 'baseline', gap: 12,
    padding: '16px 20px', borderBottom: '1px solid #d5ccc3', backgroundColor: '#eae3db',
  },
  title: { fontSize: 18, fontWeight: 700, color: '#4a443d', margin: 0 },
  stats: { fontSize: 13, color: '#8a8078' },
  toolbar: {
    display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '4px 16px',
    padding: '8px 20px', borderBottom: '1px solid #e0d9d2', backgroundColor: '#ece6df', fontSize: 12,
  },
  searchBox: { display: 'flex', alignItems: 'center', gap: 6 },
  searchInput: {
    padding: '4px 8px', border: '1px solid #c8bfb5', borderRadius: 4,
    fontSize: 12, backgroundColor: '#f5f0eb', color: '#4a443d', outline: 'none', width: 140,
  },
  searchCount: { fontSize: 11, color: '#8a8078' },
  filterGroup: { display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' },
  filterLabel: { fontWeight: 500, color: '#58524a', whiteSpace: 'nowrap' as const },
  checkLabel: {
    display: 'flex', alignItems: 'center', gap: 3, color: '#58524a',
    cursor: 'pointer', padding: '2px 6px', borderRadius: 4, backgroundColor: '#f5f0eb', fontSize: 12,
  },
  checkbox: { accentColor: '#7a8b8f', margin: 0 },
  hopBtn: {
    padding: '3px 10px', border: '1px solid #d5cec6', borderRadius: 4,
    backgroundColor: '#f5f0eb', color: '#58524a', cursor: 'pointer', fontSize: 12,
  },
  hopBtnActive: { backgroundColor: '#7a8b8f', color: '#f5f0eb', borderColor: '#7a8b8f' },
  resetBtn: {
    padding: '3px 10px', border: '1px solid #c97a6b', borderRadius: 4,
    backgroundColor: 'transparent', color: '#c97a6b', cursor: 'pointer', fontSize: 12,
  },
  mainArea: { flex: 1, display: 'flex', overflow: 'hidden' },
  graphArea: { flex: 1, overflow: 'hidden' },
  center: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#a09890' },
  emptyTitle: { fontSize: 16, fontWeight: 600, color: '#8a8078', margin: 0 },
  emptyHint: { fontSize: 13, marginTop: 8 },
};
