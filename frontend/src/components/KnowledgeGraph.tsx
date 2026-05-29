import { useMemo, useRef, useEffect, useState, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { KgNode, KgEdge } from '../types';

interface KnowledgeGraphProps {
  nodes: KgNode[];
  edges: KgEdge[];
  height?: number;
  highlight?: { nodeId: string; hop: number } | null;
  onNodeClick?: (nodeId: string) => void;
  onResetHighlight?: () => void;
}

const DOMAIN_COLORS: Record<string, string> = {
  AI: '#7a8b8f',
  ML: '#9b8ea6',
  CS: '#8a9ea2',
  Math: '#b5a67a',
  Physics: '#b08888',
  Bio: '#8aaa8a',
};

function hashColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const h = Math.abs(hash) % 60 + 30;
  return `hsl(${h}, 25%, 55%)`;
}

function getNodeColor(domain: string | null): string {
  if (!domain) return '#a09890';
  return DOMAIN_COLORS[domain] || hashColor(domain);
}

/** BFS to find all nodes within N hops of startNode */
function bfsHighlight(startId: string, edges: KgEdge[], hop: number): Set<string> {
  const adj = new Map<string, string[]>();
  for (const e of edges) {
    if (!adj.has(e.from_node_id)) adj.set(e.from_node_id, []);
    if (!adj.has(e.to_node_id)) adj.set(e.to_node_id, []);
    adj.get(e.from_node_id)!.push(e.to_node_id);
    adj.get(e.to_node_id)!.push(e.from_node_id);
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

interface TooltipData {
  name: string;
  domain: string | null;
  description: string | null;
  confidence: number;
}

export function KnowledgeGraph({ nodes, edges, height = 300, highlight, onNodeClick, onResetHighlight }: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<any>(null);
  const [tooltip, setTooltip] = useState<{ left: number; top: number; data: TooltipData } | null>(null);

  const nodeMap = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  /** Set of highlighted node IDs, or null if no highlight */
  const highlightedIds = useMemo(() => {
    if (!highlight) return null;
    return bfsHighlight(highlight.nodeId, edges, highlight.hop);
  }, [highlight, edges]);

  const graphData = useMemo(() => {
    const degreeMap = new Map<string, number>();
    for (const e of edges) {
      degreeMap.set(e.from_node_id, (degreeMap.get(e.from_node_id) || 0) + 1);
      degreeMap.set(e.to_node_id, (degreeMap.get(e.to_node_id) || 0) + 1);
    }

    const graphNodes = nodes.map((n) => ({
      id: n.id,
      name: n.name,
      domain: n.domain,
      color: getNodeColor(n.domain),
      size: 4 + Math.min((degreeMap.get(n.id) || 0) * 2, 8),
    }));

    const links = edges.map((e) => ({
      source: e.from_node_id,
      target: e.to_node_id,
      label: e.relation_type,
      strength: e.strength,
    }));

    return { nodes: graphNodes, links };
  }, [nodes, edges]);

  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.d3ReheatSimulation();
    }
  }, [graphData]);

  const handleNodeHover = useCallback((node: any) => {
    if (!node || !fgRef.current || !containerRef.current) {
      setTooltip(null);
      return;
    }

    const original = nodeMap.get(node.id);
    if (!original) return;

    const { x: screenX, y: screenY } = fgRef.current.graph2ScreenCoords(node.x, node.y);
    const rect = containerRef.current.getBoundingClientRect();

    const tipW = 200;
    const tipH = 90;

    const left = Math.max(0, Math.min(screenX - rect.left + 16, rect.width - tipW));
    const top = Math.max(0, Math.min(screenY - rect.top - tipH - 8, rect.height - tipH));

    setTooltip({
      left,
      top,
      data: {
        name: original.name,
        domain: original.domain,
        description: original.description,
        confidence: original.confidence,
      },
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
        width={containerRef.current?.clientWidth || 400}
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
        linkLabel="label"
        linkWidth={(link: any) => {
          const alpha = linkOpacity(link);
          return alpha < 0.5 ? 0.3 : Math.max(link.strength * 1.5, 0.5);
        }}
        linkColor={() => '#c8bfb5'}
        linkCanvasObject={(link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          if (!link.label) return;
          const alpha = linkOpacity(link);
          if (alpha < 0.5) return;
          const start = link.source;
          const end = link.target;
          if (typeof start !== 'object' || typeof end !== 'object') return;
          const midX = (start.x + end.x) / 2;
          const midY = (start.y + end.y) / 2;
          const fontSize = 8 / globalScale;
          ctx.font = `${fontSize}px sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = '#8a8078';
          ctx.fillText(link.label, midX, midY - 4 / globalScale);
        }}
        linkCanvasObjectMode={() => 'after'}
        cooldownTicks={100}
        onEngineStop={() => {
          fgRef.current?.pauseAnimation();
        }}
        onNodeHover={handleNodeHover}
        onNodeClick={(node: any) => {
          if (onNodeClick && node?.id) onNodeClick(node.id);
        }}
        onBackgroundClick={() => {
          if (onResetHighlight) onResetHighlight();
        }}
        enableZoomInteraction={true}
        enablePanInteraction={true}
      />

      {tooltip && (
        <div
          style={{
            position: 'absolute',
            left: tooltip.left,
            top: tooltip.top,
            backgroundColor: '#4a443d',
            color: '#e8e0d8',
            padding: '10px 14px',
            borderRadius: 8,
            fontSize: 12,
            width: 200,
            pointerEvents: 'none',
            zIndex: 10,
            boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{tooltip.data.name}</div>
          {tooltip.data.domain && (
            <div style={{ color: '#b0a89e', marginBottom: 4 }}>领域: {tooltip.data.domain}</div>
          )}
          {tooltip.data.description && (
            <div style={{ color: '#c8bfb5', lineHeight: 1.4 }}>{tooltip.data.description}</div>
          )}
          <div style={{ color: '#8a8078', marginTop: 4 }}>置信度: {(tooltip.data.confidence * 100).toFixed(0)}%</div>
        </div>
      )}
    </div>
  );
}
