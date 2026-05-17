'use client'

import { useState, useEffect, useRef, useCallback } from 'react'

interface StarNode {
  id: string
  user_id: string
  term_id: string
  term_name: string
  domain: string
  x: number
  y: number
  confirmed_at: string
}

interface StarEdge {
  id: string
  user_id: string
  from_node_id: string
  to_node_id: string
  relation_type: string
  description: string
  discovered_at: string
}

interface StarMapData {
  nodes: StarNode[]
  edges: StarEdge[]
  stats: {
    total_nodes: number
    total_edges: number
    domains: string[]
  }
}

export default function StarMapPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [nodes, setNodes] = useState<StarNode[]>([])
  const [edges, setEdges] = useState<StarEdge[]>([])
  const [selectedNode, setSelectedNode] = useState<StarNode | null>(null)
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({ total_nodes: 0, total_edges: 0, domains: [] as string[] })

  const transformRef = useRef({ scale: 1, offsetX: 0, offsetY: 0 })
  const touchRef = useRef({ lastDist: 0, lastX: 0, lastY: 0, isDragging: false })

  const normalizeNodes = useCallback((rawNodes: StarNode[], canvasW: number, canvasH: number) => {
    if (rawNodes.length === 0) return rawNodes
    const padding = 80
    const minX = Math.min(...rawNodes.map(n => n.x))
    const maxX = Math.max(...rawNodes.map(n => n.x))
    const minY = Math.min(...rawNodes.map(n => n.y))
    const maxY = Math.max(...rawNodes.map(n => n.y))
    const rangeX = maxX - minX || 1
    const rangeY = maxY - minY || 1
    const scaleX = (canvasW - padding * 2) / rangeX
    const scaleY = (canvasH - padding * 2) / rangeY
    const scale = Math.min(scaleX, scaleY)
    const centerX = canvasW / 2
    const centerY = canvasH / 2
    const midX = (minX + maxX) / 2
    const midY = (minY + maxY) / 2
    return rawNodes.map(n => ({
      ...n,
      x: centerX + (n.x - midX) * scale,
      y: centerY + (n.y - midY) * scale,
    }))
  }, [])

  const fetchStarMapData = useCallback(async () => {
    try {
      setLoading(true)

      let userId = localStorage.getItem('daydayknow_user_id')
      if (!userId) {
        userId = 'user_' + Math.random().toString(36).substr(2, 9)
        localStorage.setItem('daydayknow_user_id', userId)
      }

      const response = await fetch('/api/star-map', {
        headers: { 'x-user-id': userId }
      })

      if (!response.ok) throw new Error('获取星图数据失败')

      const data: StarMapData = await response.json()
      setNodes(data.nodes)
      setEdges(data.edges)
      setStats(data.stats)
    } catch {
      const mockNodes: StarNode[] = [
        { id: '1', user_id: 'mock', term_id: '1', term_name: '流动性陷阱', domain: '宏观经济学', x: 150, y: 200, confirmed_at: new Date().toISOString() },
        { id: '2', user_id: 'mock', term_id: '2', term_name: '零利率下限', domain: '宏观经济学', x: 300, y: 150, confirmed_at: new Date().toISOString() },
        { id: '3', user_id: 'mock', term_id: '3', term_name: '量化宽松', domain: '宏观经济学', x: 250, y: 300, confirmed_at: new Date().toISOString() },
      ]
      const mockEdges: StarEdge[] = [
        { id: '1', user_id: 'mock', from_node_id: '1', to_node_id: '2', relation_type: 'same_domain', description: '同属宏观经济学领域', discovered_at: new Date().toISOString() },
        { id: '2', user_id: 'mock', from_node_id: '1', to_node_id: '3', relation_type: 'same_domain', description: '同属宏观经济学领域', discovered_at: new Date().toISOString() },
      ]
      setNodes(mockNodes)
      setEdges(mockEdges)
      setStats({ total_nodes: mockNodes.length, total_edges: mockEdges.length, domains: ['宏观经济学'] })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStarMapData()
  }, [fetchStarMapData])

  const drawStarMap = useCallback(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const rect = container.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    canvas.style.width = rect.width + 'px'
    canvas.style.height = rect.height + 'px'
    ctx.scale(dpr, dpr)

    const w = rect.width
    const h = rect.height

    const { scale, offsetX, offsetY } = transformRef.current

    ctx.clearRect(0, 0, w, h)

    const gradient = ctx.createLinearGradient(0, 0, 0, h)
    gradient.addColorStop(0, '#0f172a')
    gradient.addColorStop(1, '#1e293b')
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, w, h)

    const seed = 42
    for (let i = 0; i < 120; i++) {
      const sx = ((seed * (i + 1) * 9301 + 49297) % 233280) / 233280 * w
      const sy = ((seed * (i + 1) * 9301 + 49297 + 7) % 233280) / 233280 * h
      const sz = ((i * 7 + 3) % 5) * 0.4 + 0.3
      const opacity = ((i * 13 + 7) % 10) * 0.04 + 0.1
      ctx.beginPath()
      ctx.arc(sx, sy, sz, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(255, 255, 255, ${opacity})`
      ctx.fill()
    }

    ctx.save()
    ctx.translate(offsetX, offsetY)
    ctx.scale(scale, scale)

    const normalized = normalizeNodes(nodes, w, h)

    edges.forEach(edge => {
      const fromNode = normalized.find(n => n.id === edge.from_node_id)
      const toNode = normalized.find(n => n.id === edge.to_node_id)
      if (fromNode && toNode) {
        ctx.beginPath()
        ctx.moveTo(fromNode.x, fromNode.y)
        ctx.lineTo(toNode.x, toNode.y)
        ctx.strokeStyle = 'rgba(99, 102, 241, 0.6)'
        ctx.lineWidth = 2
        ctx.stroke()

        const midX = (fromNode.x + toNode.x) / 2
        const midY = (fromNode.y + toNode.y) / 2
        ctx.beginPath()
        ctx.arc(midX, midY, 3, 0, Math.PI * 2)
        ctx.fillStyle = 'rgba(99, 102, 241, 0.8)'
        ctx.fill()
      }
    })

    normalized.forEach(node => {
      const isSelected = selectedNode?.id === node.id
      const nodeSize = isSelected ? 8 : 6

      const glow = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, nodeSize * 3)
      glow.addColorStop(0, 'rgba(99, 102, 241, 0.8)')
      glow.addColorStop(1, 'rgba(99, 102, 241, 0)')
      ctx.beginPath()
      ctx.arc(node.x, node.y, nodeSize * 3, 0, Math.PI * 2)
      ctx.fillStyle = glow
      ctx.fill()

      ctx.beginPath()
      ctx.arc(node.x, node.y, nodeSize, 0, Math.PI * 2)
      ctx.fillStyle = isSelected ? '#818cf8' : '#6366f1'
      ctx.fill()
      ctx.strokeStyle = '#ffffff'
      ctx.lineWidth = 2
      ctx.stroke()

      ctx.font = isSelected ? 'bold 12px sans-serif' : '10px sans-serif'
      ctx.fillStyle = '#ffffff'
      ctx.textAlign = 'center'
      ctx.fillText(node.term_name, node.x, node.y + nodeSize + 15)
    })

    ctx.restore()
  }, [nodes, edges, selectedNode, normalizeNodes])

  useEffect(() => {
    drawStarMap()
  }, [nodes, edges, selectedNode, drawStarMap])

  useEffect(() => {
    const handleResize = () => drawStarMap()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [drawStarMap])

  const screenToCanvas = useCallback((clientX: number, clientY: number) => {
    const canvas = canvasRef.current
    if (!canvas) return { x: 0, y: 0 }
    const rect = canvas.getBoundingClientRect()
    const { scale, offsetX, offsetY } = transformRef.current
    return {
      x: (clientX - rect.left - offsetX) / scale,
      y: (clientY - rect.top - offsetY) / scale,
    }
  }, [])

  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const pos = screenToCanvas(e.clientX, e.clientY)
    const { scale } = transformRef.current
    const normalized = normalizeNodes(nodes, canvasRef.current?.getBoundingClientRect().width || 400, canvasRef.current?.getBoundingClientRect().height || 500)

    const clickedNode = normalized.find(node => {
      const distance = Math.sqrt(Math.pow(node.x - pos.x, 2) + Math.pow(node.y - pos.y, 2))
      return distance < 20 / scale
    })
    setSelectedNode(clickedNode || null)
  }, [nodes, screenToCanvas, normalizeNodes])

  // 双指缩放
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const getDistance = (t1: Touch, t2: Touch) => {
      return Math.sqrt(Math.pow(t1.clientX - t2.clientX, 2) + Math.pow(t1.clientY - t2.clientY, 2))
    }

    const getMidpoint = (t1: Touch, t2: Touch) => ({
      x: (t1.clientX + t2.clientX) / 2,
      y: (t1.clientY + t2.clientY) / 2,
    })

    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        e.preventDefault()
        touchRef.current.lastDist = getDistance(e.touches[0], e.touches[1])
        const mid = getMidpoint(e.touches[0], e.touches[1])
        touchRef.current.lastX = mid.x
        touchRef.current.lastY = mid.y
      } else if (e.touches.length === 1) {
        touchRef.current.isDragging = true
        touchRef.current.lastX = e.touches[0].clientX
        touchRef.current.lastY = e.touches[0].clientY
      }
    }

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        e.preventDefault()
        const dist = getDistance(e.touches[0], e.touches[1])
        const mid = getMidpoint(e.touches[0], e.touches[1])
        const { scale, offsetX, offsetY } = transformRef.current
        const scaleFactor = dist / touchRef.current.lastDist
        const newScale = Math.min(Math.max(scale * scaleFactor, 0.3), 5)

        const rect = canvas.getBoundingClientRect()
        const cx = mid.x - rect.left
        const cy = mid.y - rect.top

        transformRef.current = {
          scale: newScale,
          offsetX: cx - (cx - offsetX) * (newScale / scale) + (mid.x - touchRef.current.lastX),
          offsetY: cy - (cy - offsetY) * (newScale / scale) + (mid.y - touchRef.current.lastY),
        }

        touchRef.current.lastDist = dist
        touchRef.current.lastX = mid.x
        touchRef.current.lastY = mid.y
        drawStarMap()
      } else if (e.touches.length === 1 && touchRef.current.isDragging) {
        const dx = e.touches[0].clientX - touchRef.current.lastX
        const dy = e.touches[0].clientY - touchRef.current.lastY
        transformRef.current.offsetX += dx
        transformRef.current.offsetY += dy
        touchRef.current.lastX = e.touches[0].clientX
        touchRef.current.lastY = e.touches[0].clientY
        drawStarMap()
      }
    }

    const handleTouchEnd = () => {
      touchRef.current.isDragging = false
    }

    // 鼠标滚轮缩放
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault()
      const { scale, offsetX, offsetY } = transformRef.current
      const scaleFactor = e.deltaY < 0 ? 1.1 : 0.9
      const newScale = Math.min(Math.max(scale * scaleFactor, 0.3), 5)

      const rect = canvas.getBoundingClientRect()
      const cx = e.clientX - rect.left
      const cy = e.clientY - rect.top

      transformRef.current = {
        scale: newScale,
        offsetX: cx - (cx - offsetX) * (newScale / scale),
        offsetY: cy - (cy - offsetY) * (newScale / scale),
      }
      drawStarMap()
    }

    // 鼠标拖拽
    let isMouseDragging = false
    let lastMouseX = 0
    let lastMouseY = 0

    const handleMouseDown = (e: MouseEvent) => {
      isMouseDragging = true
      lastMouseX = e.clientX
      lastMouseY = e.clientY
      canvas.style.cursor = 'grabbing'
    }

    const handleMouseMove = (e: MouseEvent) => {
      if (!isMouseDragging) return
      transformRef.current.offsetX += e.clientX - lastMouseX
      transformRef.current.offsetY += e.clientY - lastMouseY
      lastMouseX = e.clientX
      lastMouseY = e.clientY
      drawStarMap()
    }

    const handleMouseUp = () => {
      isMouseDragging = false
      canvas.style.cursor = 'grab'
    }

    canvas.addEventListener('touchstart', handleTouchStart, { passive: false })
    canvas.addEventListener('touchmove', handleTouchMove, { passive: false })
    canvas.addEventListener('touchend', handleTouchEnd)
    canvas.addEventListener('wheel', handleWheel, { passive: false })
    canvas.addEventListener('mousedown', handleMouseDown)
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)

    return () => {
      canvas.removeEventListener('touchstart', handleTouchStart)
      canvas.removeEventListener('touchmove', handleTouchMove)
      canvas.removeEventListener('touchend', handleTouchEnd)
      canvas.removeEventListener('wheel', handleWheel)
      canvas.removeEventListener('mousedown', handleMouseDown)
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [drawStarMap])

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-gray-800 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto mb-4"></div>
          <p className="text-gray-300">加载星图中...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 to-gray-800">
      <header className="bg-gray-800/50 backdrop-blur-sm">
        <div className="max-w-lg mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white">我的知识星图</h1>
              <p className="text-sm text-gray-400">
                ✦ {stats.total_nodes}星 ═ {stats.total_edges}连
              </p>
              {stats.domains.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {stats.domains.map((domain, index) => (
                    <span key={index} className="px-2 py-1 bg-indigo-900/50 text-indigo-300 text-xs rounded-full">
                      {domain}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="text-right">
              <div className="text-2xl">🌌</div>
              <button
                onClick={fetchStarMapData}
                className="mt-2 px-3 py-1 text-xs text-gray-400 hover:text-white transition-colors"
              >
                刷新
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-6">
        <div className="relative">
          <div
            ref={containerRef}
            className="w-full h-[500px] rounded-2xl border border-gray-700 overflow-hidden"
          >
            <canvas
              ref={canvasRef}
              className="w-full h-full cursor-grab"
              onClick={handleCanvasClick}
            />
          </div>

          {selectedNode && (
            <div className="absolute bottom-4 left-4 right-4 bg-gray-800/90 backdrop-blur-sm rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-semibold text-white">
                  {selectedNode.term_name}
                </h3>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-gray-400 hover:text-white"
                >
                  ✕
                </button>
              </div>
              <p className="text-sm text-gray-300 mb-2">
                领域：{selectedNode.domain}
              </p>
              <p className="text-xs text-gray-400">
                确认时间：{new Date(selectedNode.confirmed_at).toLocaleDateString()}
              </p>
            </div>
          )}
        </div>

        <div className="mt-6 text-center text-gray-400 text-sm">
          {nodes.length > 0 ? (
            <>
              <p>点击星星查看详情</p>
              <p>双指缩放 / 滚轮缩放 / 拖拽移动</p>
            </>
          ) : (
            <div className="py-8">
              <div className="text-4xl mb-4">✨</div>
              <p className="text-lg mb-2">你的知识星空等待点亮</p>
              <p className="mb-4">捕获术语并确认掌握后，它们会出现在这里</p>
              <button
                onClick={() => window.location.href = '/'}
                className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
              >
                去捕获术语
              </button>
            </div>
          )}
        </div>
      </main>

      <nav className="fixed bottom-0 left-0 right-0 bg-gray-800/80 backdrop-blur-sm border-t border-gray-700">
        <div className="max-w-lg mx-auto px-4 py-2">
          <div className="flex justify-around">
            <button
              onClick={() => window.location.href = '/star-map'}
              className="flex flex-col items-center py-2 text-indigo-400"
            >
              <span className="text-xl">⭐</span>
              <span className="text-xs mt-1">星图</span>
            </button>
            <button
              onClick={() => window.location.href = '/daily'}
              className="flex flex-col items-center py-2 text-gray-400 hover:text-indigo-400 transition-colors"
            >
              <span className="text-xl">📰</span>
              <span className="text-xs mt-1">日报</span>
            </button>
            <button
              onClick={() => window.location.href = '/'}
              className="flex flex-col items-center py-2 text-gray-400 hover:text-indigo-400 transition-colors"
            >
              <span className="text-xl">🎯</span>
              <span className="text-xs mt-1">捕获</span>
            </button>
          </div>
        </div>
      </nav>

      <div className="h-20"></div>
    </div>
  )
}
