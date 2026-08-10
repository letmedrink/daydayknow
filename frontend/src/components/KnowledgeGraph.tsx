import { useMemo, useRef, useEffect, useState, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { WikiGraphNode, WikiGraphEdge } from '../types';

interface KnowledgeGraphProps {
  nodes: WikiGraphNode[];
  edges: WikiGraphEdge[];
  height?: number;
  highlight?: { nodeId: string; hop: number; searchIds?: Set<string> } | null;
  onNodeClick?: (nodeId: string) => void;
  onResetHighlight?: () => void;
}

const TYPE_COLORS: Record<string, string> = {
  entity: '#7a8b8f',
  concept: '#9b8ea6',
  source: '#8a9ea2',
  comparison: '#b5a67a',
  synthesis: '#b08888',
  finding: '#8aaa8a',
};

function hashColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const h = Math.abs(hash) % 60 + 30;
  return `hsl(${h}, 25%, 55%)`;
}

function getNodeColor(type: string): string {
  return TYPE_COLORS[type] || hashColor(type);
}

function bfsHighlight(startId: string, edges: WikiGraphEdge[], hop: number): Set<string> {
  const adj = new Map<string, string[]>();
  for (const e of edges) {
    if (!adj.has(e.source)) adj.set(e.source, []);
    if (!adj.has(e.target)) adj.set(e.target, []);
    adj.get(e.source)!.push(e.target);
    adj.get(e.target)!.push(e.source);
  }

  const visited = new Set<string>([startId]);
  let frontier = [startId];
  for (let depth = 0; depth < hop; depth++) {
    const next: string[] = [];
    for (const id of frontier) {
      for (const neighbor of (adj.get(id) || [])) {
        if (!visited.has(neighbor)) {
          visited.add(neighbor);
          next.push(neighbor);
        }
      }
    }
    frontier = next;
  }
  return visited;
}

export function KnowledgeGraph({ nodes, edges, height = 300, highlight, onNodeClick, onResetHighlight }: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<any>(null);
  const [tooltip, setTooltip] = useState<{ left: number; top: number; data: any } | null>(null);
  const [containerWidth, setContainerWidth] = useState(400);

  // 监听容器宽度变化
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width;
        if (w > 0) setContainerWidth(w);
      }
    });
    ro.observe(el);
    // 初始宽度
    if (el.clientWidth > 0) setContainerWidth(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  const nodeMap = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  const highlightedIds = useMemo(() => {
    if (!highlight) return null;
    if (highlight.searchIds && highlight.searchIds.size > 0) return highlight.searchIds;
    return bfsHighlight(highlight.nodeId, edges, highlight.hop);
  }, [highlight, edges]);

  const graphData = useMemo(() => {
    const maxLinkCount = Math.max(...nodes.map((n) => n.linkCount || 0), 1);

    const graphNodes = nodes.map((n) => ({
      id: n.id,
      name: n.title,
      type: n.type,
      color: getNodeColor(n.type),
      size: 5 + Math.sqrt((n.linkCount || 0) / maxLinkCount) * 12,
    }));

    const maxWeight = Math.max(...edges.map((e) => e.weight || 1), 1);
    const links = edges.map((e) => ({
      source: e.source,
      target: e.target,
      label: e.type,
      weight: e.weight || 1,
      normalizedWeight: (e.weight || 1) / maxWeight,
    }));

    return { nodes: graphNodes, links };
  }, [nodes, edges]);

  useEffect(() => {
    if (!fgRef.current) return;
    const n = nodes.length;
    // 节点越多，斥力越大，间距越宽
    const chargeStrength = n > 200 ? -200 : n > 80 ? -150 : -100;
    // 链接距离：节点越少越宽松
    const linkDistance = n > 200 ? 60 : n > 80 ? 80 : 120;

    const fg = fgRef.current;
    // 配置斥力
    const charge = fg.d3Force('charge');
    if (charge) charge.strength(chargeStrength);
    // 配置链接力
    const link = fg.d3Force('link');
    if (link) link.distance(linkDistance);
    // 配置居中力
    const center = fg.d3Force('center');
    if (center) center.strength(0.05);

    fg.d3ReheatSimulation();
  }, [graphData, nodes.length, containerWidth]);

  const handleNodeHover = useCallback((node: any) => {
    if (!node || !fgRef.current || !containerRef.current) {
      setTooltip(null);
      return;
    }
    const original = nodeMap.get(node.id);
    if (!original) return;

    const { x: screenX, y: screenY } = fgRef.current.graph2ScreenCoords(node.x, node.y);
    const rect = containerRef.current.getBoundingClientRect();
    const left = Math.max(0, Math.min(screenX - rect.left + 16, rect.width - 200));
    const top = Math.max(0, Math.min(screenY - rect.top - 98, rect.height - 90));

    setTooltip({
      left, top,
      data: { title: original.title, type: original.type, tags: original.tags, linkCount: original.linkCount },
    });
  }, [nodeMap]);

  const nodeOpacity = useCallback((node: any) => {
    if (!highlightedIds) return 1;
    return highlightedIds.has(node.id) ? 1 : 0.12;
  }, [highlightedIds]);

  const linkOpacity = useCallback((link: any) => {
    if (!highlightedIds) return 1;
    const srcId = typeof link.source === 'object' ? link.source.id : link.source;
    const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
    return (highlightedIds.has(srcId) && highlightedIds.has(tgtId)) ? 1 : 0.06;
  }, [highlightedIds]);

  if (nodes.length === 0) {
    return <div style={{ textAlign: 'center', padding: 20, color: '#a09890' }}>暂无图谱数据</div>;
  }

  return (
    <div ref={containerRef} style={{ height, width: '100%', position: 'relative' }}>
      <ForceGraph2D
        ref={fgRef}
        graphData={graphData}
        width={containerWidth}
        height={height}
        nodeLabel="name"
        nodeColor="color"
        nodeVal="size"
        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const label = node.name;
          const fontSize = 10 / globalScale;
          const alpha = nodeOpacity(node);
          ctx.globalAlpha = alpha;
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.size, 0, 2 * Math.PI, false);
          ctx.fillStyle = node.color;
          ctx.fill();
          ctx.font = `${fontSize}px sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = '#4a443d';
          ctx.fillText(label, node.x, node.y + node.size + fontSize);
          ctx.globalAlpha = 1;
        }}
        linkWidth={(link: any) => {
          const alpha = linkOpacity(link);
          if (alpha < 0.5) return 0.3;
          const w = link.normalizedWeight || 0.5;
          return 0.5 + w * 2.5;
        }}
        linkColor={(link: any) => {
          const alpha = linkOpacity(link);
          if (alpha < 0.5) return 'rgba(200,191,181,0.15)';
          const w = link.normalizedWeight || 0.5;
          const intensity = Math.round(140 + w * 60);
          return `rgb(${intensity}, ${intensity - 9}, ${intensity - 15})`;
        }}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        cooldownTicks={150}
        onEngineStop={() => fgRef.current?.pauseAnimation()}
        onNodeHover={handleNodeHover}
        onNodeClick={(node: any) => { if (onNodeClick && node?.id) onNodeClick(node.id); }}
        onBackgroundClick={() => { if (onResetHighlight) onResetHighlight(); }}
        enableZoomInteraction={true}
        enablePanInteraction={true}
      />

      {tooltip && (
        <div style={{
          position: 'absolute', left: tooltip.left, top: tooltip.top,
          backgroundColor: '#4a443d', color: '#e8e0d8', padding: '10px 14px',
          borderRadius: 8, fontSize: 12, width: 200, pointerEvents: 'none',
          zIndex: 10, boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
        }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{tooltip.data.title}</div>
          <div style={{ color: '#b0a89e', marginBottom: 2 }}>类型: {tooltip.data.type}</div>
          {tooltip.data.linkCount > 0 && (
            <div style={{ color: '#b0a89e', marginBottom: 2 }}>连接数: {tooltip.data.linkCount}</div>
          )}
          {tooltip.data.tags?.length > 0 && (
            <div style={{ color: '#c8bfb5' }}>标签: {tooltip.data.tags.join(', ')}</div>
          )}
        </div>
      )}
    </div>
  );
}
