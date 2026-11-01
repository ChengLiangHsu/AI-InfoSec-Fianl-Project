<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import {
  type PlotItem,
  type NormalizedPoint,
  type GridGeneratorState,
  parseCoords,
} from '@/lib/usePlots'
import type { CanvasViewport } from '@/lib/useCanvasViewport'

const props = withDefaults(
  defineProps<{
    plots: PlotItem[]
    activeMode: 'view' | 'draw'
    drawTool?: 'rect' | 'polygon'
    selectedPlotNumber: number | null
    getPlotColor: (plot: PlotItem) => string
    viewport: CanvasViewport
    gridState?: GridGeneratorState
    previewPlots?: NormalizedPoint[][]
  }>(),
  {
    drawTool: 'rect',
    previewPlots: () => [],
  }
)

const emit = defineEmits<{
  (e: 'plot-drawn', points: NormalizedPoint[]): void
  (e: 'edit-plot', plot: PlotItem): void
  (e: 'update-plot-points', payload: { plotNumber: number; points: NormalizedPoint[] }): void
  (e: 'select-plot', plotNumber: number | null): void
  (e: 'update-grid-corner', payload: { index: number; point: NormalizedPoint }): void
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)

// 網格角點把手拖曳狀態
const draggingGridCornerIndex = ref<number | null>(null)

// 矩形拖曳拉框狀態
const isDraggingRect = ref(false)
const rectStartScreen = ref<{ x: number; y: number } | null>(null)
const rectStartNorm = ref<NormalizedPoint | null>(null)
const rectCurrentNorm = ref<NormalizedPoint | null>(null)

// 多邊形點繪狀態
const currentDrawingPoints = ref<NormalizedPoint[]>([])
const currentMousePos = ref<NormalizedPoint | null>(null)
const isNearStartPoint = ref(false)
const draggingVertexIndex = ref<number | null>(null)

const SNAP_THRESHOLD_PX = 18
const MIN_RECT_DRAG_PX = 8

function getCanvasRelativeCoords(e: MouseEvent): { screenX: number; screenY: number; norm: NormalizedPoint } {
  if (!canvasRef.value) {
    return { screenX: 0, screenY: 0, norm: { x: 0, y: 0 } }
  }
  const rect = canvasRef.value.getBoundingClientRect()
  const screenX = e.clientX - rect.left
  const screenY = e.clientY - rect.top
  const norm = props.viewport.screenToNormalized(screenX, screenY)
  return { screenX, screenY, norm }
}

function findPlotAtPoint(screenX: number, screenY: number): PlotItem | null {
  if (!canvasRef.value) return null
  const ctx = canvasRef.value.getContext('2d')
  if (!ctx) return null

  for (let i = props.plots.length - 1; i >= 0; i--) {
    const plot = props.plots[i]
    const pts = parseCoords(plot.coords)
    if (pts.length < 3) continue

    const path = new Path2D()
    const first = props.viewport.normalizedToScreen(pts[0])
    path.moveTo(first.x, first.y)
    for (let j = 1; j < pts.length; j++) {
      const sp = props.viewport.normalizedToScreen(pts[j])
      path.lineTo(sp.x, sp.y)
    }
    path.closePath()

    if (ctx.isPointInPath(path, screenX, screenY)) {
      return plot
    }
  }
  return null
}

function findVertexNearPoint(screenX: number, screenY: number, plot: PlotItem): number | null {
  const pts = parseCoords(plot.coords)
  const threshold = 12 // 螢幕點擊半徑 px
  for (let i = 0; i < pts.length; i++) {
    const sp = props.viewport.normalizedToScreen(pts[i])
    if (Math.hypot(sp.x - screenX, sp.y - screenY) <= threshold) {
      return i
    }
  }
  return null
}

function syncCanvasSize() {
  if (!canvasRef.value || !containerRef.value) return
  const rect = containerRef.value.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1
  canvasRef.value.width = rect.width * dpr
  canvasRef.value.height = rect.height * dpr
  drawCanvas()
}

function drawCanvas() {
  if (!canvasRef.value) return
  const ctx = canvasRef.value.getContext('2d')
  if (!ctx) return

  const dpr = window.devicePixelRatio || 1
  ctx.save()
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  ctx.scale(dpr, dpr)

  drawExistingPlots(ctx)
  drawDraggingRectPreview(ctx)
  drawCurrentDrawingPolyline(ctx)

  // 繪製自動網格動態預覽與 4 角錨點把手
  if (props.gridState?.isActive) {
    drawGridGeneratorOverlay(ctx)
  }

  ctx.restore()
}

function drawGridGeneratorOverlay(ctx: CanvasRenderingContext2D) {
  if (!props.gridState || !props.gridState.isActive || props.gridState.corners.length < 4) return

  const corners = props.gridState.corners
  const screenCorners = corners.map((c) => props.viewport.normalizedToScreen(c))

  // 1. 繪製預覽子小區 (Subplots Preview)
  if (props.previewPlots && props.previewPlots.length > 0) {
    let plotIdx = 1
    for (const plotPoly of props.previewPlots) {
      if (plotPoly.length < 3) continue
      const spStart = props.viewport.normalizedToScreen(plotPoly[0])

      ctx.beginPath()
      ctx.moveTo(spStart.x, spStart.y)
      for (let j = 1; j < plotPoly.length; j++) {
        const sp = props.viewport.normalizedToScreen(plotPoly[j])
        ctx.lineTo(sp.x, sp.y)
      }
      ctx.closePath()

      // 填充淡紫色半透明背景
      ctx.fillStyle = 'rgba(168, 85, 247, 0.16)'
      ctx.fill()

      // 繪製虛線邊框
      ctx.strokeStyle = '#a855f7'
      ctx.lineWidth = 1.5
      ctx.setLineDash([4, 3])
      ctx.stroke()
      ctx.setLineDash([])

      // 繪製子小區中心編號標籤
      let sumX = 0
      let sumY = 0
      for (const p of plotPoly) {
        const sp = props.viewport.normalizedToScreen(p)
        sumX += sp.x
        sumY += sp.y
      }
      const cx = sumX / plotPoly.length
      const cy = sumY / plotPoly.length

      ctx.save()
      ctx.font = 'bold 10px system-ui, sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillStyle = 'rgba(255, 255, 255, 0.85)'
      ctx.beginPath()
      ctx.arc(cx, cy, 9, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = '#a855f7'
      ctx.lineWidth = 1
      ctx.stroke()

      ctx.fillStyle = '#7e22ce'
      ctx.fillText(`#${plotIdx}`, cx, cy)
      ctx.restore()

      plotIdx++
    }
  }

  // 2. 繪製母區四邊形邊界 (Bounding Quad)
  ctx.beginPath()
  ctx.moveTo(screenCorners[0].x, screenCorners[0].y)
  for (let i = 1; i < 4; i++) {
    ctx.lineTo(screenCorners[i].x, screenCorners[i].y)
  }
  ctx.closePath()
  ctx.strokeStyle = '#6b21a8'
  ctx.lineWidth = 2.2
  ctx.setLineDash([6, 4])
  ctx.stroke()
  ctx.setLineDash([])

  // 3. 繪製 4 個角點可拖曳把手 (Draggable Handles)
  const cornerLabels = ['TL', 'TR', 'BR', 'BL']
  for (let i = 0; i < 4; i++) {
    const sc = screenCorners[i]
    const isDragging = draggingGridCornerIndex.value === i

    // 外圈光暈與陰影
    ctx.save()
    ctx.beginPath()
    ctx.arc(sc.x, sc.y, isDragging ? 15 : 12, 0, Math.PI * 2)
    ctx.fillStyle = isDragging ? '#7e22ce' : '#9333ea'
    ctx.shadowColor = 'rgba(126, 34, 206, 0.6)'
    ctx.shadowBlur = 8
    ctx.fill()
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 2.5
    ctx.stroke()
    ctx.restore()

    // 內圈文字
    ctx.save()
    ctx.font = 'bold 9px system-ui, sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillStyle = '#ffffff'
    ctx.fillText(cornerLabels[i], sc.x, sc.y)
    ctx.restore()
  }
}

function drawExistingPlots(ctx: CanvasRenderingContext2D) {
  for (const plot of props.plots) {
    const pts = parseCoords(plot.coords)
    if (pts.length < 3) continue

    const isSelected = plot.plot_number === props.selectedPlotNumber
    const color = props.getPlotColor(plot)

    ctx.beginPath()
    const start = props.viewport.normalizedToScreen(pts[0])
    ctx.moveTo(start.x, start.y)
    for (let i = 1; i < pts.length; i++) {
      const sp = props.viewport.normalizedToScreen(pts[i])
      ctx.lineTo(sp.x, sp.y)
    }
    ctx.closePath()

    // 填充半透明色
    ctx.fillStyle = hexToRgba(color, isSelected ? 0.45 : 0.22)
    ctx.fill()

    // 邊框繪製
    ctx.strokeStyle = isSelected ? '#ffffff' : color
    ctx.lineWidth = isSelected ? 3 : 1.8
    if (isSelected) {
      ctx.shadowColor = 'rgba(0,0,0,0.6)'
      ctx.shadowBlur = 6
    }
    ctx.stroke()
    ctx.shadowBlur = 0

    // 繪製中心標籤
    drawPlotCentroidBadge(ctx, pts, plot, isSelected)

    // 若處於繪製模式且為選取的小區，繪製頂點手柄
    if (props.activeMode === 'draw' && isSelected) {
      drawPlotHandles(ctx, pts)
    }
  }
}

function drawDraggingRectPreview(ctx: CanvasRenderingContext2D) {
  if (!isDraggingRect.value || !rectStartNorm.value || !rectCurrentNorm.value) return

  const sp1 = props.viewport.normalizedToScreen(rectStartNorm.value)
  const sp2 = props.viewport.normalizedToScreen(rectCurrentNorm.value)
  const sx = Math.min(sp1.x, sp2.x)
  const sy = Math.min(sp1.y, sp2.y)
  const sw = Math.abs(sp2.x - sp1.x)
  const sh = Math.abs(sp2.y - sp1.y)

  ctx.save()
  // 填色預覽
  ctx.fillStyle = 'rgba(56, 189, 248, 0.25)'
  ctx.fillRect(sx, sy, sw, sh)

  // 邊框預覽
  ctx.strokeStyle = '#0284c7'
  ctx.lineWidth = 2
  ctx.setLineDash([6, 4])
  ctx.strokeRect(sx, sy, sw, sh)
  ctx.setLineDash([])

  // 四個角標記
  const corners = [
    { x: sx, y: sy },
    { x: sx + sw, y: sy },
    { x: sx + sw, y: sy + sh },
    { x: sx, y: sy + sh },
  ]
  for (const c of corners) {
    ctx.beginPath()
    ctx.arc(c.x, c.y, 4, 0, Math.PI * 2)
    ctx.fillStyle = '#38bdf8'
    ctx.fill()
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 1.5
    ctx.stroke()
  }
  ctx.restore()
}

function drawPlotHandles(ctx: CanvasRenderingContext2D, pts: NormalizedPoint[]) {
  for (let i = 0; i < pts.length; i++) {
    const sp = props.viewport.normalizedToScreen(pts[i])
    ctx.beginPath()
    ctx.arc(sp.x, sp.y, 5, 0, Math.PI * 2)
    ctx.fillStyle = '#ffffff'
    ctx.fill()
    ctx.strokeStyle = '#2563eb'
    ctx.lineWidth = 2
    ctx.stroke()
  }
}

function drawCurrentDrawingPolyline(ctx: CanvasRenderingContext2D) {
  if (currentDrawingPoints.value.length === 0) return

  const pts = currentDrawingPoints.value
  ctx.beginPath()
  const start = props.viewport.normalizedToScreen(pts[0])
  ctx.moveTo(start.x, start.y)
  for (let i = 1; i < pts.length; i++) {
    const sp = props.viewport.normalizedToScreen(pts[i])
    ctx.lineTo(sp.x, sp.y)
  }
  if (currentMousePos.value) {
    const curSp = props.viewport.normalizedToScreen(currentMousePos.value)
    ctx.lineTo(curSp.x, curSp.y)
  }
  ctx.strokeStyle = '#06b6d4'
  ctx.lineWidth = 2
  ctx.setLineDash([5, 3])
  ctx.stroke()
  ctx.setLineDash([])

  // 繪製頂點圓點
  for (let i = 0; i < pts.length; i++) {
    const sp = props.viewport.normalizedToScreen(pts[i])
    ctx.beginPath()
    ctx.arc(sp.x, sp.y, 4.5, 0, Math.PI * 2)
    ctx.fillStyle = i === 0 ? '#10b981' : '#06b6d4'
    ctx.fill()
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 1.5
    ctx.stroke()
  }

  // 起點吸附提示圈
  if (isNearStartPoint.value && pts.length >= 3) {
    const startSp = props.viewport.normalizedToScreen(pts[0])
    ctx.beginPath()
    ctx.arc(startSp.x, startSp.y, 10, 0, Math.PI * 2)
    ctx.strokeStyle = '#10b981'
    ctx.lineWidth = 2.5
    ctx.stroke()

    ctx.fillStyle = 'rgba(16, 185, 129, 0.35)'
    ctx.fill()
  }
}

function drawPlotCentroidBadge(
  ctx: CanvasRenderingContext2D,
  pts: NormalizedPoint[],
  plot: PlotItem,
  isSelected: boolean
) {
  let avgX = 0
  let avgY = 0
  for (const p of pts) {
    avgX += p.x
    avgY += p.y
  }
  avgX /= pts.length
  avgY /= pts.length

  const sp = props.viewport.normalizedToScreen({ x: avgX, y: avgY })

  let text = `#${plot.plot_number}`
  if (plot.is_control) {
    text += ' (CK)'
  } else if (plot.treatment) {
    text += ` (${plot.treatment}${plot.dose ? ' ' + plot.dose : ''})`
  }

  ctx.font = 'bold 11px system-ui, sans-serif'
  const textMetrics = ctx.measureText(text)
  const paddingX = 6
  const paddingY = 3.5
  const badgeW = textMetrics.width + paddingX * 2
  const badgeH = 18

  ctx.save()
  ctx.beginPath()
  roundRect(ctx, sp.x - badgeW / 2, sp.y - badgeH / 2, badgeW, badgeH, 4)
  ctx.fillStyle = isSelected ? 'rgba(30, 41, 59, 0.95)' : 'rgba(15, 23, 42, 0.8)'
  ctx.fill()
  ctx.strokeStyle = isSelected ? '#38bdf8' : 'rgba(255, 255, 255, 0.4)'
  ctx.lineWidth = isSelected ? 1.5 : 1
  ctx.stroke()

  ctx.fillStyle = '#ffffff'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(text, sp.x, sp.y)
  ctx.restore()
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number
) {
  ctx.moveTo(x + radius, y)
  ctx.lineTo(x + width - radius, y)
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius)
  ctx.lineTo(x + width, y + height - radius)
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
  ctx.lineTo(x + radius, y + height)
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius)
  ctx.lineTo(x, y + radius)
  ctx.quadraticCurveTo(x, y, x + radius, y)
}

function hexToRgba(hex: string, alpha: number): string {
  let c = hex.replace('#', '')
  if (c.length === 3) {
    c = c.split('').map((char) => char + char).join('')
  }
  const num = parseInt(c, 16)
  const r = (num >> 16) & 255
  const g = (num >> 8) & 255
  const b = num & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function onMouseDown(e: MouseEvent) {
  // 1. 滑鼠右鍵拖曳平移 (Pan)
  if (e.button === 2) {
    e.preventDefault()
    props.viewport.startPan(e.clientX, e.clientY)
    return
  }

  // 2. 僅滑鼠左鍵進行繪製與選取
  if (e.button !== 0) return

  const { screenX, screenY, norm } = getCanvasRelativeCoords(e)

  // 自動網格生成模式：檢查是否點擊在 4 個角點錨點把手上以進行拖曳
  if (props.gridState?.isActive) {
    if (props.gridState.corners && props.gridState.corners.length >= 4) {
      for (let i = 0; i < 4; i++) {
        const sc = props.viewport.normalizedToScreen(props.gridState.corners[i])
        if (Math.hypot(sc.x - screenX, sc.y - screenY) <= 18) {
          draggingGridCornerIndex.value = i
          return
        }
      }
    }
    return
  }

  // 檢視模式：點擊小區選取並彈窗編輯
  if (props.activeMode === 'view') {
    const hitPlot = findPlotAtPoint(screenX, screenY)
    if (hitPlot) {
      emit('select-plot', hitPlot.plot_number)
      emit('edit-plot', hitPlot)
    } else {
      emit('select-plot', null)
    }
    return
  }

  // 繪製模式
  if (props.activeMode === 'draw') {
    // 檢查是否點擊在已選取小區的頂點手柄上以進行拖曳
    if (props.selectedPlotNumber !== null && currentDrawingPoints.value.length === 0 && !isDraggingRect.value) {
      const selectedPlot = props.plots.find((p) => p.plot_number === props.selectedPlotNumber)
      if (selectedPlot) {
        const vIdx = findVertexNearPoint(screenX, screenY, selectedPlot)
        if (vIdx !== null) {
          draggingVertexIndex.value = vIdx
          return
        }
      }
    }

    // 矩形拖曳拉框工具
    if (props.drawTool === 'rect') {
      const hitPlot = findPlotAtPoint(screenX, screenY)
      if (hitPlot) {
        emit('select-plot', hitPlot.plot_number)
        emit('edit-plot', hitPlot)
      } else {
        emit('select-plot', null)
        isDraggingRect.value = true
        rectStartScreen.value = { x: screenX, y: screenY }
        rectStartNorm.value = { x: norm.x, y: norm.y }
        rectCurrentNorm.value = { x: norm.x, y: norm.y }
        drawCanvas()
      }
      return
    }

    // 多邊形點繪工具
    if (props.drawTool === 'polygon') {
      if (currentDrawingPoints.value.length > 0) {
        if (isNearStartPoint.value && currentDrawingPoints.value.length >= 3) {
          finishDrawing()
          return
        }
        currentDrawingPoints.value.push({ x: norm.x, y: norm.y })
        drawCanvas()
        return
      }

      const hitPlot = findPlotAtPoint(screenX, screenY)
      if (hitPlot) {
        emit('select-plot', hitPlot.plot_number)
        emit('edit-plot', hitPlot)
      } else {
        emit('select-plot', null)
        currentDrawingPoints.value = [{ x: norm.x, y: norm.y }]
        drawCanvas()
      }
    }
  }
}

function onMouseMove(e: MouseEvent) {
  // 1. 若處於右鍵平移中
  if (props.viewport.isPanning.value) {
    const w = containerRef.value?.clientWidth
    const h = containerRef.value?.clientHeight
    if (props.viewport.updatePan(e.clientX, e.clientY, w, h)) {
      drawCanvas()
    }
    return
  }

  const { screenX, screenY, norm } = getCanvasRelativeCoords(e)
  currentMousePos.value = norm

  // 2. 自動網格模式下拖曳 4 角錨點或懸停檢測
  if (props.gridState?.isActive) {
    if (draggingGridCornerIndex.value !== null) {
      emit('update-grid-corner', {
        index: draggingGridCornerIndex.value,
        point: norm,
      })
      drawCanvas()
      return
    }

    let isHoverHandle = false
    if (props.gridState.corners && props.gridState.corners.length >= 4) {
      for (let i = 0; i < 4; i++) {
        const sc = props.viewport.normalizedToScreen(props.gridState.corners[i])
        if (Math.hypot(sc.x - screenX, sc.y - screenY) <= 18) {
          isHoverHandle = true
          break
        }
      }
    }
    if (canvasRef.value) {
      canvasRef.value.style.cursor = isHoverHandle ? 'grab' : 'crosshair'
    }
    return
  }

  // 3. 頂點拖曳微調
  if (draggingVertexIndex.value !== null && props.selectedPlotNumber !== null) {
    const selectedPlot = props.plots.find((p) => p.plot_number === props.selectedPlotNumber)
    if (selectedPlot) {
      const pts = parseCoords(selectedPlot.coords)
      if (draggingVertexIndex.value >= 0 && draggingVertexIndex.value < pts.length) {
        pts[draggingVertexIndex.value] = { x: norm.x, y: norm.y }
        emit('update-plot-points', { plotNumber: selectedPlot.plot_number, points: pts })
      }
    }
    drawCanvas()
    return
  }

  // 3. 矩形拖曳中
  if (isDraggingRect.value && rectStartNorm.value) {
    rectCurrentNorm.value = norm
    drawCanvas()
    return
  }

  // 4. 多邊形起點吸附判定
  if (props.drawTool === 'polygon' && currentDrawingPoints.value.length >= 3) {
    const startSp = props.viewport.normalizedToScreen(currentDrawingPoints.value[0])
    const dist = Math.hypot(startSp.x - screenX, startSp.y - screenY)
    isNearStartPoint.value = dist <= SNAP_THRESHOLD_PX
  } else {
    isNearStartPoint.value = false
  }

  if (currentDrawingPoints.value.length > 0) {
    drawCanvas()
  }
}

function onMouseUp(e: MouseEvent) {
  if (draggingGridCornerIndex.value !== null) {
    draggingGridCornerIndex.value = null
    drawCanvas()
    return
  }

  if (e.button === 2 || props.viewport.isPanning.value) {
    props.viewport.endPan()
    return
  }

  // 矩形拖曳結束判定
  if (isDraggingRect.value && rectStartScreen.value && rectStartNorm.value && rectCurrentNorm.value) {
    const { screenX, screenY } = getCanvasRelativeCoords(e)
    const dist = Math.hypot(screenX - rectStartScreen.value.x, screenY - rectStartScreen.value.y)

    if (dist >= MIN_RECT_DRAG_PX) {
      const minX = Math.min(rectStartNorm.value.x, rectCurrentNorm.value.x)
      const maxX = Math.max(rectStartNorm.value.x, rectCurrentNorm.value.x)
      const minY = Math.min(rectStartNorm.value.y, rectCurrentNorm.value.y)
      const maxY = Math.max(rectStartNorm.value.y, rectCurrentNorm.value.y)

      const points: NormalizedPoint[] = [
        { x: minX, y: minY },
        { x: maxX, y: minY },
        { x: maxX, y: maxY },
        { x: minX, y: maxY },
      ]
      emit('plot-drawn', points)
    }

    isDraggingRect.value = false
    rectStartScreen.value = null
    rectStartNorm.value = null
    rectCurrentNorm.value = null
    drawCanvas()
    return
  }

  draggingVertexIndex.value = null
}

function onWheel(e: WheelEvent) {
  e.preventDefault()
  if (!canvasRef.value) return
  const rect = canvasRef.value.getBoundingClientRect()
  const screenX = e.clientX - rect.left
  const screenY = e.clientY - rect.top

  const factor = e.deltaY < 0 ? 1.15 : 0.87
  props.viewport.zoomAtScreenPoint(screenX, screenY, factor, rect.width, rect.height)
  drawCanvas()
}

function onDblClick() {
  if (props.activeMode === 'draw' && props.drawTool === 'polygon' && currentDrawingPoints.value.length >= 3) {
    finishDrawing()
  }
}

function finishDrawing() {
  if (currentDrawingPoints.value.length >= 3) {
    emit('plot-drawn', [...currentDrawingPoints.value])
  }
  currentDrawingPoints.value = []
  isNearStartPoint.value = false
  drawCanvas()
}

function undoLastPoint() {
  if (currentDrawingPoints.value.length > 0) {
    currentDrawingPoints.value.pop()
    drawCanvas()
  }
}

function cancelDrawing() {
  currentDrawingPoints.value = []
  isDraggingRect.value = false
  rectStartScreen.value = null
  rectStartNorm.value = null
  rectCurrentNorm.value = null
  isNearStartPoint.value = false
  drawCanvas()
}

defineExpose({
  undoLastPoint,
  cancelDrawing,
  syncCanvasSize,
  redraw: drawCanvas,
  isDrawing: () => isDraggingRect.value || currentDrawingPoints.value.length > 0,
})

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  nextTick(() => {
    syncCanvasSize()
    if (containerRef.value) {
      resizeObserver = new ResizeObserver(() => {
        syncCanvasSize()
      })
      resizeObserver.observe(containerRef.value)
    }
  })
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
})

watch(
  () => [
    props.plots,
    props.activeMode,
    props.drawTool,
    props.selectedPlotNumber,
    props.gridState?.isActive,
    props.gridState?.corners,
    props.gridState?.rows,
    props.gridState?.cols,
    props.gridState?.marginRatio,
    props.previewPlots,
    props.viewport.scale.value,
    props.viewport.panX.value,
    props.viewport.panY.value,
    props.viewport.baseWidth.value,
    props.viewport.baseHeight.value,
  ],
  () => {
    nextTick(() => {
      drawCanvas()
    })
  },
  { deep: true }
)

watch(
  () => props.activeMode,
  (newMode) => {
    if (newMode !== 'draw') {
      cancelDrawing()
    }
  }
)
</script>

<template>
  <div
    ref="containerRef"
    class="absolute inset-0 pointer-events-auto select-none"
    :class="{
      'cursor-grab': viewport.isPanning.value,
      'cursor-pointer': activeMode === 'view' && !gridState?.isActive,
      'cursor-crosshair': activeMode === 'draw' && !gridState?.isActive && !viewport.isPanning.value,
      'cursor-default': gridState?.isActive && !viewport.isPanning.value,
    }"
    @mousedown="onMouseDown"
    @mousemove="onMouseMove"
    @mouseup="onMouseUp"
    @mouseleave="onMouseUp"
    @wheel="onWheel"
    @contextmenu.prevent
    @dblclick="onDblClick"
  >
    <canvas ref="canvasRef" class="w-full h-full block" />
  </div>
</template>
