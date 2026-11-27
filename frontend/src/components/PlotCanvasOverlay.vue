<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import {
  type PlotItem,
  type PlotCanvasMode,
  type NormalizedPoint,
  type GridGeneratorState,
  type CellSpan,
  parseCoords,
  serializePoints,
  shiftPoints,
  calculateCellNormalizedSpan,
  generateSubplotPolygon,
  calculatePlotCentroid,
} from '@/lib/usePlots'
import type { CanvasViewport } from '@/lib/useCanvasViewport'

const props = withDefaults(
  defineProps<{
    plots: PlotItem[]
    activeMode: PlotCanvasMode
    drawTool?: 'rect' | 'polygon' | 'eraser'
    selectedPlotNumber?: number | null
    selectedPlotNumbers?: number[]
    getPlotColor: (plot: PlotItem) => string
    viewport: CanvasViewport
    gridState?: GridGeneratorState
    previewPlots?: NormalizedPoint[][]
    canEdit?: boolean
    isRotateToolActive?: boolean
    clickSelectOnPan?: boolean
  }>(),
  {
    drawTool: 'rect',
    previewPlots: () => [],
    canEdit: true,
    isRotateToolActive: false,
    clickSelectOnPan: false,
  }
)

const emit = defineEmits<{
  (e: 'plot-drawn', points: NormalizedPoint[]): void
  (e: 'edit-plot', plot: PlotItem): void
  (e: 'edit-plots', plots: PlotItem[]): void
  (e: 'update-plot-points', payload: { plotNumber: number; points: NormalizedPoint[] }): void
  (e: 'select-plot', plotNumber: number | null): void
  (e: 'select-plots', plotNumbers: number[]): void
  (e: 'update-grid-corner', payload: { index: number; point: NormalizedPoint }): void
  (e: 'update-grid-corners', corners: NormalizedPoint[]): void
  (e: 'move-grid', payload: { delta: { dx: number; dy: number } }): void
  (e: 'delete-plot', plotNumber: number): void
  (e: 'delete-plots', plotNumbers: number[]): void
  (e: 'duplicate-plot', plotNumber: number): void
  (e: 'duplicate-plots', plotNumbers: number[]): void
  (e: 'move-plot', payload: { plotNumber: number; delta: { dx: number; dy: number } }): void
  (e: 'move-plots', payload: { plotNumbers: number[]; delta: { dx: number; dy: number } }): void
  (e: 'toggle-exclude-grid-cell', cellIndex: number): void
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)
const isSelectingGridRegion = computed(() =>
  Boolean(props.gridState?.isActive && props.gridState.corners.length < 4)
)
const isEraserActive = computed(() =>
  Boolean(props.drawTool === 'eraser' && (props.activeMode === 'draw' || props.gridState?.isActive))
)

// 網格角點把手拖曳與懸停狀態
const draggingGridCornerIndex = ref<number | null>(null)
const hoveredGridCornerIndex = ref<number | null>(null)

// 網格整體拖曳與懸停狀態
const isDraggingWholeGrid = ref(false)
const isHoveringGridQuad = ref(false)
const gridDragStartNorm = ref<NormalizedPoint | null>(null)
const gridDragStartCorners = ref<NormalizedPoint[] | null>(null)

// 多選小區狀態統一收斂
const effectiveSelectedPlotNumbers = computed<number[]>(() => {
  if (props.selectedPlotNumbers && props.selectedPlotNumbers.length > 0) {
    return props.selectedPlotNumbers
  }
  if (props.selectedPlotNumber !== null && props.selectedPlotNumber !== undefined) {
    return [props.selectedPlotNumber]
  }
  return []
})

function isPlotSelected(plotNumber: number): boolean {
  return effectiveSelectedPlotNumbers.value.includes(plotNumber)
}

// 空白處框選（Rubber-band Selection）狀態
const isRubberBandSelecting = ref(false)
const rubberBandStartScreen = ref<{ x: number; y: number } | null>(null)
const rubberBandStartNorm = ref<NormalizedPoint | null>(null)
const rubberBandCurrentNorm = ref<NormalizedPoint | null>(null)
const isRubberBandModifier = ref(false)

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
const hoveredVertexIndex = ref<number | null>(null)

// 橡皮擦狀態
const isErasing = ref(false)
const hoveredPlotNumber = ref<number | null>(null)
const hoveredGridCellIndex = ref<number | null>(null)

// 整體小區拖曳移動 / Alt+拖曳複製狀態
const isDraggingWholePlot = ref(false)
const wholePlotDragStartNorm = ref<NormalizedPoint | null>(null)
const wholePlotCurrentDelta = ref<{ dx: number; dy: number }>({ dx: 0, dy: 0 })
const isAltDragging = ref(false)

// 步驟 4 檢視模式：平移與點擊選取並存候選狀態
const panClickCandidate = ref<{
  clientX: number
  clientY: number
  modifier: boolean
  hitPlotNumber: number | null
} | null>(null)

const SNAP_THRESHOLD_PX = 18
const MIN_RECT_DRAG_PX = 8
const HANDLE_RADIUS_PX = 12

// ==========================================
// 幾何與座標輔助子函式 (Single Responsibility)
// ==========================================

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

function findGridCellAtPoint(
  screenX: number,
  screenY: number
): { cellIndex: number; row: number; col: number; poly: NormalizedPoint[] } | null {
  if (!canvasRef.value || !props.gridState || !props.gridState.isActive || props.gridState.corners.length < 4) {
    return null
  }
  const ctx = canvasRef.value.getContext('2d')
  if (!ctx) return null

  const { rows, cols, corners } = props.gridState
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const span = calculateCellNormalizedSpan(c, r, props.gridState)
      const poly = generateSubplotPolygon(span, corners)
      if (poly.length < 3) continue

      const path = new Path2D()
      const first = props.viewport.normalizedToScreen(poly[0])
      path.moveTo(first.x, first.y)
      for (let j = 1; j < poly.length; j++) {
        const sp = props.viewport.normalizedToScreen(poly[j])
        path.lineTo(sp.x, sp.y)
      }
      path.closePath()

      if (ctx.isPointInPath(path, screenX, screenY)) {
        return { cellIndex: r * cols + c, row: r, col: c, poly }
      }
    }
  }
  return null
}

function findVertexNearPoint(screenX: number, screenY: number, plot: PlotItem): number | null {
  const pts = parseCoords(plot.coords)
  const threshold = 12
  for (let i = 0; i < pts.length; i++) {
    const sp = props.viewport.normalizedToScreen(pts[i])
    if (Math.hypot(sp.x - screenX, sp.y - screenY) <= threshold) {
      return i
    }
  }
  return null
}

function calculateCentroid(pts: NormalizedPoint[]): NormalizedPoint & { cx: number; cy: number } {
  const c = calculatePlotCentroid(pts)
  return {
    x: c.x,
    y: c.y,
    cx: c.x,
    cy: c.y,
  }
}

interface RectBounds {
  minX: number
  maxX: number
  minY: number
  maxY: number
}

function calculateNormalizedRectBounds(p1: NormalizedPoint, p2: NormalizedPoint): RectBounds {
  return {
    minX: Math.min(p1.x, p2.x),
    maxX: Math.max(p1.x, p2.x),
    minY: Math.min(p1.y, p2.y),
    maxY: Math.max(p1.y, p2.y),
  }
}

function isCentroidInsideBounds(centroid: NormalizedPoint, bounds: RectBounds): boolean {
  return (
    centroid.x >= bounds.minX &&
    centroid.x <= bounds.maxX &&
    centroid.y >= bounds.minY &&
    centroid.y <= bounds.maxY
  )
}

function isPlotInsideActiveRubberBand(plot: PlotItem): boolean {
  if (!isRubberBandSelecting.value || !rubberBandStartNorm.value || !rubberBandCurrentNorm.value) {
    return false
  }
  const pts = parseCoords(plot.coords)
  if (pts.length < 3) return false
  const sp1 = props.viewport.normalizedToScreen(rubberBandStartNorm.value)
  const sp2 = props.viewport.normalizedToScreen(rubberBandCurrentNorm.value)
  const bounds = calculateNormalizedRectBounds(sp1, sp2)
  const centroidScreen = props.viewport.normalizedToScreen(calculateCentroid(pts))
  return isCentroidInsideBounds(centroidScreen, bounds)
}

function isPlotEffectivelyHighlighted(plot: PlotItem): boolean {
  if (isRubberBandSelecting.value) {
    const insideBox = isPlotInsideActiveRubberBand(plot)
    if (isRubberBandModifier.value) {
      return isPlotSelected(plot.plot_number) || insideBox
    }
    return insideBox
  }
  return isPlotSelected(plot.plot_number)
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number
): void {
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

// ==========================================
// 繪製子函式 (Sub-renderers)
// ==========================================

function drawSinglePreviewPlotCell(
  ctx: CanvasRenderingContext2D,
  poly: NormalizedPoint[],
  isExcluded: boolean,
  isHovered: boolean,
  displayLabel: string
): void {
  if (poly.length < 3) return
  const spStart = props.viewport.normalizedToScreen(poly[0])

  ctx.beginPath()
  ctx.moveTo(spStart.x, spStart.y)
  for (let j = 1; j < poly.length; j++) {
    const sp = props.viewport.normalizedToScreen(poly[j])
    ctx.lineTo(sp.x, sp.y)
  }
  ctx.closePath()

  if (isExcluded) {
    // 排除狀態：半透明深紅背景 + 紅色虛線
    ctx.fillStyle = 'rgba(239, 68, 68, 0.22)'
    ctx.fill()
    ctx.strokeStyle = '#ef4444'
    ctx.lineWidth = isHovered ? 2.2 : 1.5
    ctx.setLineDash([4, 3])
    ctx.stroke()
    ctx.setLineDash([])
  } else if (isHovered && props.drawTool === 'eraser') {
    // 橡皮擦懸停欲排除狀態：醒目紅橘色高亮
    ctx.fillStyle = 'rgba(244, 63, 94, 0.35)'
    ctx.fill()
    ctx.strokeStyle = '#f43f5e'
    ctx.lineWidth = 2.4
    ctx.setLineDash([3, 2])
    ctx.stroke()
    ctx.setLineDash([])
  } else {
    // 正常網格預覽：紫色半透明 + 紫色虛線
    ctx.fillStyle = 'rgba(168, 85, 247, 0.16)'
    ctx.fill()
    ctx.strokeStyle = '#a855f7'
    ctx.lineWidth = 1.5
    ctx.setLineDash([4, 3])
    ctx.stroke()
    ctx.setLineDash([])
  }

  // 繪製單元格中心標籤
  const centroidNorm = calculateCentroid(poly)
  const centroidScreen = props.viewport.normalizedToScreen(centroidNorm)

  ctx.save()
  ctx.font = 'bold 10px system-ui, sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'

  if (isExcluded) {
    ctx.fillStyle = 'rgba(239, 68, 68, 0.95)'
    ctx.beginPath()
    roundRect(ctx, centroidScreen.x - 22, centroidScreen.y - 9, 44, 18, 4)
    ctx.fill()
    ctx.fillStyle = '#ffffff'
    ctx.fillText('✖ 排除', centroidScreen.x, centroidScreen.y)
  } else if (isHovered && props.drawTool === 'eraser') {
    ctx.fillStyle = 'rgba(244, 63, 94, 0.95)'
    ctx.beginPath()
    roundRect(ctx, centroidScreen.x - 22, centroidScreen.y - 9, 44, 18, 4)
    ctx.fill()
    ctx.fillStyle = '#ffffff'
    ctx.fillText('✖ 消除', centroidScreen.x, centroidScreen.y)
  } else {
    ctx.fillStyle = 'rgba(255, 255, 255, 0.9)'
    ctx.beginPath()
    ctx.arc(centroidScreen.x, centroidScreen.y, 9.5, 0, Math.PI * 2)
    ctx.fill()
    ctx.strokeStyle = '#a855f7'
    ctx.lineWidth = 1
    ctx.stroke()

    ctx.fillStyle = '#7e22ce'
    ctx.fillText(displayLabel, centroidScreen.x, centroidScreen.y)
  }
  ctx.restore()
}

function drawGridBoundingQuad(ctx: CanvasRenderingContext2D, screenCorners: { x: number; y: number }[]): void {
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
}

function drawGridCornerHandles(
  ctx: CanvasRenderingContext2D,
  screenCorners: { x: number; y: number }[],
  draggingIndex: number | null,
  hoveredIndex: number | null
): void {
  const cornerLabels = ['TL', 'TR', 'BR', 'BL']
  for (let i = 0; i < 4; i++) {
    const sc = screenCorners[i]
    const isDragging = draggingIndex === i
    const isHovered = hoveredIndex === i

    ctx.save()
    ctx.beginPath()
    const radius = isDragging ? 15 : isHovered ? 14 : HANDLE_RADIUS_PX
    ctx.arc(sc.x, sc.y, radius, 0, Math.PI * 2)
    ctx.fillStyle = isDragging ? '#7e22ce' : isHovered ? '#a855f7' : '#9333ea'
    ctx.shadowColor = isHovered || isDragging ? 'rgba(126, 34, 206, 0.85)' : 'rgba(126, 34, 206, 0.6)'
    ctx.shadowBlur = isHovered || isDragging ? 12 : 8
    ctx.fill()
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = isHovered || isDragging ? 3 : 2.5
    ctx.stroke()
    ctx.restore()

    ctx.save()
    ctx.font = 'bold 9px system-ui, sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillStyle = '#ffffff'
    ctx.fillText(cornerLabels[i], sc.x, sc.y)
    ctx.restore()
  }
}

function drawGridGeneratorOverlay(ctx: CanvasRenderingContext2D): void {
  if (!props.gridState || !props.gridState.isActive || props.gridState.corners.length < 4) return

  const { rows, cols, corners } = props.gridState
  const screenCorners = corners.map((c) => props.viewport.normalizedToScreen(c))
  const excludedSet = new Set(props.gridState.excludedIndices || [])

  // 1. 遍歷網格所有單元格，繪製子小區預覽與排除標籤
  let activePlotCounter = 1
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const cellIdx = r * cols + c
      const span: CellSpan = calculateCellNormalizedSpan(c, r, props.gridState)
      const poly = generateSubplotPolygon(span, corners)
      const isExcluded = excludedSet.has(cellIdx)
      const isHovered = hoveredGridCellIndex.value === cellIdx
      const label = isExcluded ? '' : `#${activePlotCounter++}`

      drawSinglePreviewPlotCell(ctx, poly, isExcluded, isHovered, label)
    }
  }

  // 2. 繪製母區邊界框與 4 角錨點把手
  drawGridBoundingQuad(ctx, screenCorners)
  drawGridCornerHandles(ctx, screenCorners, draggingGridCornerIndex.value, hoveredGridCornerIndex.value)
}

function drawSingleExistingPlot(
  ctx: CanvasRenderingContext2D,
  plot: PlotItem,
  pts: NormalizedPoint[],
  isSelected: boolean,
  isEraserHover: boolean
): void {
  if (pts.length < 3) return

  ctx.beginPath()
  const start = props.viewport.normalizedToScreen(pts[0])
  ctx.moveTo(start.x, start.y)
  for (let i = 1; i < pts.length; i++) {
    const sp = props.viewport.normalizedToScreen(pts[i])
    ctx.lineTo(sp.x, sp.y)
  }
  ctx.closePath()

  if (isEraserHover) {
    // 橡皮擦滑過待刪除標記
    ctx.fillStyle = 'rgba(239, 68, 68, 0.35)'
    ctx.fill()
    ctx.strokeStyle = '#ef4444'
    ctx.lineWidth = 2.6
    ctx.setLineDash([4, 3])
    ctx.stroke()
    ctx.setLineDash([])
    drawPlotCentroidBadge(ctx, pts, plot, isSelected, true)
    return
  }

  const color = props.getPlotColor(plot)
  ctx.fillStyle = hexToRgba(color, isSelected ? 0.45 : 0.22)
  ctx.fill()

  ctx.strokeStyle = isSelected ? '#ffffff' : color
  ctx.lineWidth = isSelected ? 3 : 1.8
  if (isSelected) {
    ctx.shadowColor = 'rgba(0,0,0,0.6)'
    ctx.shadowBlur = 6
  }
  ctx.stroke()
  ctx.shadowBlur = 0

  drawPlotCentroidBadge(ctx, pts, plot, isSelected, false)
}

function drawGhostDuplicatePreview(
  ctx: CanvasRenderingContext2D,
  plot: PlotItem,
  delta: { dx: number; dy: number }
): void {
  const pts = parseCoords(plot.coords)
  if (pts.length < 3) return
  const shifted = shiftPoints(pts, delta.dx, delta.dy)

  ctx.beginPath()
  const start = props.viewport.normalizedToScreen(shifted[0])
  ctx.moveTo(start.x, start.y)
  for (let i = 1; i < shifted.length; i++) {
    const sp = props.viewport.normalizedToScreen(shifted[i])
    ctx.lineTo(sp.x, sp.y)
  }
  ctx.closePath()

  ctx.fillStyle = 'rgba(16, 185, 129, 0.3)'
  ctx.fill()
  ctx.strokeStyle = '#10b981'
  ctx.lineWidth = 2.2
  ctx.setLineDash([5, 3])
  ctx.stroke()
  ctx.setLineDash([])

  const centroid = calculateCentroid(shifted)
  const sp = props.viewport.normalizedToScreen(centroid)
  ctx.save()
  ctx.font = 'bold 10px system-ui, sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = '#10b981'
  ctx.beginPath()
  roundRect(ctx, sp.x - 26, sp.y - 9, 52, 18, 4)
  ctx.fill()
  ctx.fillStyle = '#ffffff'
  ctx.fillText('+ 複製副本', sp.x, sp.y)
  ctx.restore()
}

function drawExistingPlots(ctx: CanvasRenderingContext2D): void {
  for (const plot of props.plots) {
    const rawPts = parseCoords(plot.coords)
    if (rawPts.length < 3) continue

    const isSelected = isPlotEffectivelyHighlighted(plot)
    const isEraserHover = isEraserActive.value && hoveredPlotNumber.value === plot.plot_number

    // 若正在拖曳移動（非 Alt 複製模式），渲染平移後位置
    let pts = rawPts
    if (isSelected && isDraggingWholePlot.value && !isAltDragging.value) {
      pts = shiftPoints(rawPts, wholePlotCurrentDelta.value.dx, wholePlotCurrentDelta.value.dy)
    }

    drawSingleExistingPlot(ctx, plot, pts, isSelected, isEraserHover)

    // 只有在「選取模式」且「單選」且未拖曳時繪製頂點手柄（多選或拉框預覽時隱藏手柄）
    if (
      props.activeMode === 'select' &&
      isSelected &&
      effectiveSelectedPlotNumbers.value.length === 1 &&
      !isRubberBandSelecting.value &&
      !isDraggingWholePlot.value &&
      !props.gridState?.isActive
    ) {
      drawPlotHandles(ctx, pts)
    }

    // 若處於 Alt 拖曳複製中，渲染幽靈副本
    if (isSelected && isDraggingWholePlot.value && isAltDragging.value) {
      drawGhostDuplicatePreview(ctx, plot, wholePlotCurrentDelta.value)
    }
  }
}

function drawRubberBandPreview(ctx: CanvasRenderingContext2D): void {
  if (!isRubberBandSelecting.value || !rubberBandStartNorm.value || !rubberBandCurrentNorm.value) return

  const sp1 = props.viewport.normalizedToScreen(rubberBandStartNorm.value)
  const sp2 = props.viewport.normalizedToScreen(rubberBandCurrentNorm.value)
  const sx = Math.min(sp1.x, sp2.x)
  const sy = Math.min(sp1.y, sp2.y)
  const sw = Math.abs(sp2.x - sp1.x)
  const sh = Math.abs(sp2.y - sp1.y)

  ctx.save()
  ctx.fillStyle = 'rgba(59, 130, 246, 0.15)'
  ctx.fillRect(sx, sy, sw, sh)

  ctx.strokeStyle = '#3b82f6'
  ctx.lineWidth = 1.5
  ctx.setLineDash([4, 4])
  ctx.strokeRect(sx, sy, sw, sh)
  ctx.restore()
}

function drawDraggingRectPreview(ctx: CanvasRenderingContext2D): void {
  if (!isDraggingRect.value || !rectStartNorm.value || !rectCurrentNorm.value) return

  const sp1 = props.viewport.normalizedToScreen(rectStartNorm.value)
  const sp2 = props.viewport.normalizedToScreen(rectCurrentNorm.value)
  const sx = Math.min(sp1.x, sp2.x)
  const sy = Math.min(sp1.y, sp2.y)
  const sw = Math.abs(sp2.x - sp1.x)
  const sh = Math.abs(sp2.y - sp1.y)

  ctx.save()
  ctx.fillStyle = 'rgba(56, 189, 248, 0.25)'
  ctx.fillRect(sx, sy, sw, sh)

  ctx.strokeStyle = '#0284c7'
  ctx.lineWidth = 2
  ctx.setLineDash([6, 4])
  ctx.strokeRect(sx, sy, sw, sh)
  ctx.setLineDash([])

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

function drawPlotHandles(ctx: CanvasRenderingContext2D, pts: NormalizedPoint[]): void {
  for (let i = 0; i < pts.length; i++) {
    const sp = props.viewport.normalizedToScreen(pts[i])
    const isHovered = hoveredVertexIndex.value === i
    const isDragging = draggingVertexIndex.value === i

    ctx.save()
    ctx.beginPath()
    ctx.arc(sp.x, sp.y, isHovered || isDragging ? 7 : 5, 0, Math.PI * 2)
    ctx.fillStyle = isHovered || isDragging ? '#3b82f6' : '#ffffff'
    ctx.fill()
    ctx.strokeStyle = isHovered || isDragging ? '#ffffff' : '#2563eb'
    ctx.lineWidth = isHovered || isDragging ? 2.5 : 2
    ctx.stroke()
    ctx.restore()
  }
}

function drawCurrentDrawingPolyline(ctx: CanvasRenderingContext2D): void {
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
  isSelected: boolean,
  isEraserHover: boolean
): void {
  const centroid = calculateCentroid(pts)
  const sp = props.viewport.normalizedToScreen(centroid)

  let text = `#${plot.plot_number}`
  if (isEraserHover) {
    text = `✖ 消除 #${plot.plot_number}`
  } else if (plot.is_control) {
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

  if (isEraserHover) {
    ctx.fillStyle = 'rgba(239, 68, 68, 0.95)'
    ctx.fill()
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 1
    ctx.stroke()
  } else {
    ctx.fillStyle = isSelected ? 'rgba(30, 41, 59, 0.95)' : 'rgba(15, 23, 42, 0.8)'
    ctx.fill()
    ctx.strokeStyle = isSelected ? '#38bdf8' : 'rgba(255, 255, 255, 0.4)'
    ctx.lineWidth = isSelected ? 1.5 : 1
    ctx.stroke()
  }

  ctx.fillStyle = '#ffffff'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(text, sp.x, sp.y)
  ctx.restore()
}

function drawRotationIndicator(ctx: CanvasRenderingContext2D): void {
  if (!props.viewport.isRotating.value) return
  const px = props.viewport.rotatePivotX.value
  const py = props.viewport.rotatePivotY.value
  const label = `${props.viewport.rotationDegrees.value}°`

  ctx.save()
  ctx.beginPath()
  ctx.arc(px, py, 8, 0, Math.PI * 2)
  ctx.strokeStyle = 'rgba(168, 85, 247, 0.9)'
  ctx.lineWidth = 1.5
  ctx.stroke()

  ctx.beginPath()
  ctx.moveTo(px - 14, py)
  ctx.lineTo(px + 14, py)
  ctx.moveTo(px, py - 14)
  ctx.lineTo(px, py + 14)
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.75)'
  ctx.lineWidth = 1
  ctx.stroke()

  ctx.font = 'bold 11px ui-monospace, SFMono-Regular, Menlo, monospace'
  const textW = ctx.measureText(label).width
  const badgeW = textW + 14
  const badgeH = 20
  const badgeX = px - badgeW / 2
  const badgeY = py - 34

  ctx.fillStyle = 'rgba(24, 24, 27, 0.92)'
  ctx.beginPath()
  roundRect(ctx, badgeX, badgeY, badgeW, badgeH, 5)
  ctx.fill()
  ctx.strokeStyle = 'rgba(168, 85, 247, 0.85)'
  ctx.lineWidth = 1
  ctx.stroke()

  ctx.fillStyle = '#ffffff'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(label, px, badgeY + badgeH / 2)
  ctx.restore()
}

// ==========================================
// 主繪製調度器 (Main Orchestrator)
// ==========================================

function drawCanvas(): void {
  if (!canvasRef.value) return
  const ctx = canvasRef.value.getContext('2d')
  if (!ctx) return

  const dpr = window.devicePixelRatio || 1
  ctx.save()
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  ctx.scale(dpr, dpr)

  drawExistingPlots(ctx)
  drawDraggingRectPreview(ctx)
  drawRubberBandPreview(ctx)
  drawCurrentDrawingPolyline(ctx)

  if (props.gridState?.isActive) {
    drawGridGeneratorOverlay(ctx)
  }

  drawRotationIndicator(ctx)

  ctx.restore()
}

function syncCanvasSize(): void {
  if (!canvasRef.value || !containerRef.value) return
  const rect = containerRef.value.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1
  canvasRef.value.width = rect.width * dpr
  canvasRef.value.height = rect.height * dpr
  drawCanvas()
}

// ==========================================
// 滑鼠事件處理子函式 (Event Handlers)
// ==========================================

function handleEraserDown(screenX: number, screenY: number): void {
  if (props.gridState?.isActive) {
    const hitCell = findGridCellAtPoint(screenX, screenY)
    if (hitCell) {
      emit('toggle-exclude-grid-cell', hitCell.cellIndex)
      isErasing.value = true
    }
    return
  }

  const hitPlot = findPlotAtPoint(screenX, screenY)
  if (hitPlot) {
    emit('delete-plot', hitPlot.plot_number)
    isErasing.value = true
  }
}

function handleEraserMove(screenX: number, screenY: number): void {
  if (props.gridState?.isActive) {
    const hitCell = findGridCellAtPoint(screenX, screenY)
    hoveredGridCellIndex.value = hitCell ? hitCell.cellIndex : null
    if (isErasing.value && hitCell) {
      const excluded = new Set(props.gridState.excludedIndices || [])
      if (!excluded.has(hitCell.cellIndex)) {
        emit('toggle-exclude-grid-cell', hitCell.cellIndex)
      }
    }
  } else {
    const hitPlot = findPlotAtPoint(screenX, screenY)
    hoveredPlotNumber.value = hitPlot ? hitPlot.plot_number : null
    if (isErasing.value && hitPlot) {
      emit('delete-plot', hitPlot.plot_number)
    }
  }
  drawCanvas()
}

function findGridCornerAtPoint(screenX: number, screenY: number): number | null {
  if (!props.gridState?.corners || props.gridState.corners.length < 4) return null
  const threshold = 18
  for (let i = 0; i < 4; i++) {
    const sc = props.viewport.normalizedToScreen(props.gridState.corners[i])
    if (Math.hypot(sc.x - screenX, sc.y - screenY) <= threshold) {
      return i
    }
  }
  return null
}

function handleGridHandleDown(screenX: number, screenY: number): boolean {
  const hitIndex = findGridCornerAtPoint(screenX, screenY)
  if (hitIndex !== null) {
    draggingGridCornerIndex.value = hitIndex
    return true
  }
  return false
}

function isPointInGridQuad(screenX: number, screenY: number): boolean {
  if (!canvasRef.value || !props.gridState?.isActive || !props.gridState.corners || props.gridState.corners.length < 4) {
    return false
  }
  const ctx = canvasRef.value.getContext('2d')
  if (!ctx) return false

  const screenCorners = props.gridState.corners.map((c) => props.viewport.normalizedToScreen(c))
  const path = new Path2D()
  path.moveTo(screenCorners[0].x, screenCorners[0].y)
  for (let i = 1; i < 4; i++) {
    path.lineTo(screenCorners[i].x, screenCorners[i].y)
  }
  path.closePath()
  return ctx.isPointInPath(path, screenX, screenY)
}

function calculateRigidClampedCorners(
  startCorners: NormalizedPoint[],
  totalDx: number,
  totalDy: number
): NormalizedPoint[] {
  let minX = 1
  let maxX = 0
  let minY = 1
  let maxY = 0
  for (const c of startCorners) {
    if (c.x < minX) minX = c.x
    if (c.x > maxX) maxX = c.x
    if (c.y < minY) minY = c.y
    if (c.y > maxY) maxY = c.y
  }

  const clampedDx = Math.max(-minX, Math.min(1 - maxX, totalDx))
  const clampedDy = Math.max(-minY, Math.min(1 - maxY, totalDy))

  return startCorners.map((c) => ({
    x: Math.max(0, Math.min(1, Number((c.x + clampedDx).toFixed(5)))),
    y: Math.max(0, Math.min(1, Number((c.y + clampedDy).toFixed(5)))),
  }))
}

function handleGridQuadDown(screenX: number, screenY: number, norm: NormalizedPoint): boolean {
  if (isPointInGridQuad(screenX, screenY) && props.gridState?.corners && props.gridState.corners.length === 4) {
    isDraggingWholeGrid.value = true
    gridDragStartNorm.value = { x: norm.x, y: norm.y }
    gridDragStartCorners.value = props.gridState.corners.map((c) => ({ ...c }))
    return true
  }
  return false
}

function handleGridDragMove(norm: NormalizedPoint): void {
  if (!gridDragStartNorm.value || !gridDragStartCorners.value) return
  const totalDx = norm.x - gridDragStartNorm.value.x
  const totalDy = norm.y - gridDragStartNorm.value.y

  const shiftedCorners = calculateRigidClampedCorners(gridDragStartCorners.value, totalDx, totalDy)
  emit('update-grid-corners', shiftedCorners)
}

function finishGridDrag(): void {
  isDraggingWholeGrid.value = false
  gridDragStartNorm.value = null
  gridDragStartCorners.value = null
}

function handleGridHoverMove(screenX: number, screenY: number): void {
  const hitCorner = findGridCornerAtPoint(screenX, screenY)
  if (hoveredGridCornerIndex.value !== hitCorner) {
    hoveredGridCornerIndex.value = hitCorner
  }
  const isInsideQuad = hitCorner === null ? isPointInGridQuad(screenX, screenY) : false
  if (isHoveringGridQuad.value !== isInsideQuad) {
    isHoveringGridQuad.value = isInsideQuad
  }
  drawCanvas()
}

function handleViewModeDown(
  screenX: number,
  screenY: number,
  norm: NormalizedPoint,
  e: MouseEvent
): void {
  // 1. 先檢驗是否點擊於選中小區的頂點手柄 (僅在允許編輯且僅單選時)
  if (
    props.canEdit &&
    effectiveSelectedPlotNumbers.value.length === 1 &&
    currentDrawingPoints.value.length === 0 &&
    !isDraggingRect.value
  ) {
    const singleNumber = effectiveSelectedPlotNumbers.value[0]
    const selectedPlot = props.plots.find((p) => p.plot_number === singleNumber)
    if (selectedPlot) {
      const vIdx = findVertexNearPoint(screenX, screenY, selectedPlot)
      if (vIdx !== null) {
        draggingVertexIndex.value = vIdx
        return
      }
    }
  }

  // 2. 檢驗是否點擊中小區多邊形本體
  const hitPlot = findPlotAtPoint(screenX, screenY)
  const isModifier = e.shiftKey || e.ctrlKey || e.metaKey

  if (hitPlot) {
    if (isModifier) {
      // 組合鍵點選：加選/減選切換
      const cur = effectiveSelectedPlotNumbers.value
      const next = cur.includes(hitPlot.plot_number)
        ? cur.filter((n) => n !== hitPlot.plot_number)
        : [...cur, hitPlot.plot_number]
      emit('select-plots', next)
      if (next.length <= 1) {
        emit('select-plot', next.length === 1 ? next[0] : null)
      }
    } else {
      // 若點擊未選中小區，切換為單選該小區
      if (!isPlotSelected(hitPlot.plot_number)) {
        emit('select-plots', [hitPlot.plot_number])
        emit('select-plot', hitPlot.plot_number)
      }
      if (props.canEdit) {
        isDraggingWholePlot.value = true
        wholePlotDragStartNorm.value = { x: norm.x, y: norm.y }
        wholePlotCurrentDelta.value = { dx: 0, dy: 0 }
        isAltDragging.value = e.altKey
      }
    }
    return
  }

  // 3. 點擊空白處：啟動框選（Rubber-band Box Selection）
  isRubberBandSelecting.value = true
  rubberBandStartScreen.value = { x: screenX, y: screenY }
  rubberBandStartNorm.value = { x: norm.x, y: norm.y }
  rubberBandCurrentNorm.value = { x: norm.x, y: norm.y }
  isRubberBandModifier.value = isModifier
}

function startRectDrag(screenX: number, screenY: number, norm: NormalizedPoint): void {
  isDraggingRect.value = true
  rectStartScreen.value = { x: screenX, y: screenY }
  rectStartNorm.value = { ...norm }
  rectCurrentNorm.value = { ...norm }
  drawCanvas()
}

function handleDrawModeDown(
  screenX: number,
  screenY: number,
  norm: NormalizedPoint
): void {
  // 繪圖模式與選取交互徹底解耦：不檢驗或修改既有小區選取，專注於新小區幾何繪製
  if (props.drawTool === 'rect') {
    startRectDrag(screenX, screenY, norm)
  } else if (props.drawTool === 'polygon') {
    if (currentDrawingPoints.value.length > 0) {
      if (isNearStartPoint.value && currentDrawingPoints.value.length >= 3) {
        finishDrawing()
        return
      }
      currentDrawingPoints.value.push({ x: norm.x, y: norm.y })
      drawCanvas()
    } else {
      currentDrawingPoints.value = [{ x: norm.x, y: norm.y }]
      drawCanvas()
    }
  }
}

function finishWholePlotDrag(): void {
  if (isDraggingWholePlot.value && effectiveSelectedPlotNumbers.value.length > 0) {
    const delta = wholePlotCurrentDelta.value
    const dist = Math.hypot(delta.dx, delta.dy)
    if (dist >= 0.004) {
      if (isAltDragging.value) {
        if (effectiveSelectedPlotNumbers.value.length === 1) {
          emit('duplicate-plot', effectiveSelectedPlotNumbers.value[0])
        } else {
          emit('duplicate-plots', effectiveSelectedPlotNumbers.value)
        }
      } else {
        if (effectiveSelectedPlotNumbers.value.length === 1) {
          emit('move-plot', { plotNumber: effectiveSelectedPlotNumbers.value[0], delta })
        } else {
          emit('move-plots', { plotNumbers: effectiveSelectedPlotNumbers.value, delta })
        }
      }
    }
    // 距離小於 0.004 為單擊純選取，維持選取狀態，嚴禁觸發 emit('edit-plot')
  }
  isDraggingWholePlot.value = false
  wholePlotDragStartNorm.value = null
  wholePlotCurrentDelta.value = { dx: 0, dy: 0 }
  isAltDragging.value = false
}

function finishRubberBandSelection(screenX: number, screenY: number): void {
  if (
    !isRubberBandSelecting.value ||
    !rubberBandStartScreen.value ||
    !rubberBandStartNorm.value ||
    !rubberBandCurrentNorm.value
  ) {
    isRubberBandSelecting.value = false
    return
  }

  const dist = Math.hypot(
    screenX - rubberBandStartScreen.value.x,
    screenY - rubberBandStartScreen.value.y
  )

  if (dist >= MIN_RECT_DRAG_PX) {
    const sp1 = props.viewport.normalizedToScreen(rubberBandStartNorm.value)
    const sp2 = props.viewport.normalizedToScreen(rubberBandCurrentNorm.value)
    const bounds = calculateNormalizedRectBounds(sp1, sp2)

    const newlySelected: number[] = []
    for (const plot of props.plots) {
      const pts = parseCoords(plot.coords)
      if (pts.length < 3) continue
      const centroidScreen = props.viewport.normalizedToScreen(calculateCentroid(pts))
      if (isCentroidInsideBounds(centroidScreen, bounds)) {
        newlySelected.push(plot.plot_number)
      }
    }

    let finalSelected: number[] = []
    if (isRubberBandModifier.value) {
      finalSelected = Array.from(new Set([...effectiveSelectedPlotNumbers.value, ...newlySelected]))
    } else {
      finalSelected = newlySelected
    }

    emit('select-plots', finalSelected)
    if (finalSelected.length <= 1) {
      emit('select-plot', finalSelected.length === 1 ? finalSelected[0] : null)
    }
  } else {
    emit('select-plots', [])
    emit('select-plot', null)
  }

  isRubberBandSelecting.value = false
  rubberBandStartScreen.value = null
  rubberBandStartNorm.value = null
  rubberBandCurrentNorm.value = null
  isRubberBandModifier.value = false
  drawCanvas()
}

function finishRectDrag(screenX: number, screenY: number): void {
  if (isDraggingRect.value && rectStartScreen.value && rectStartNorm.value && rectCurrentNorm.value) {
    const dist = Math.hypot(screenX - rectStartScreen.value.x, screenY - rectStartScreen.value.y)
    if (dist >= MIN_RECT_DRAG_PX) {
      const sp1 = props.viewport.normalizedToScreen(rectStartNorm.value)
      const sp2 = props.viewport.normalizedToScreen(rectCurrentNorm.value)
      const minSx = Math.min(sp1.x, sp2.x)
      const maxSx = Math.max(sp1.x, sp2.x)
      const minSy = Math.min(sp1.y, sp2.y)
      const maxSy = Math.max(sp1.y, sp2.y)

      const points: NormalizedPoint[] = [
        props.viewport.screenToNormalized(minSx, minSy),
        props.viewport.screenToNormalized(maxSx, minSy),
        props.viewport.screenToNormalized(maxSx, maxSy),
        props.viewport.screenToNormalized(minSx, maxSy),
      ]
      if (isSelectingGridRegion.value) {
        if (maxSx - minSx >= MIN_RECT_DRAG_PX && maxSy - minSy >= MIN_RECT_DRAG_PX) {
          emit('update-grid-corners', points)
        }
      } else {
        emit('plot-drawn', points)
      }
    }
    isDraggingRect.value = false
    rectStartScreen.value = null
    rectStartNorm.value = null
    rectCurrentNorm.value = null
  }
}

function getViewportPivot(): { x: number; y: number } {
  const rect = canvasRef.value?.getBoundingClientRect()
  if (rect && rect.width > 0 && rect.height > 0) {
    return { x: rect.width / 2, y: rect.height / 2 }
  }
  return props.viewport.normalizedToScreen({ x: 0.5, y: 0.5 })
}

// ==========================================
// 滑鼠主流程調度 (Event Orchestrators)
// ==========================================

function onMouseDown(e: MouseEvent): void {
  const isRotateTrigger =
    e.button === 2 ||
    e.button === 1 ||
    (e.button === 0 && props.isRotateToolActive)

  if (isRotateTrigger) {
    e.preventDefault()
    const { screenX, screenY } = getCanvasRelativeCoords(e)
    const pivot = getViewportPivot()
    props.viewport.startRotate(screenX, screenY, pivot.x, pivot.y)
    drawCanvas()
    return
  }

  if (e.button !== 0) return

  const { screenX, screenY, norm } = getCanvasRelativeCoords(e)

  if (isSelectingGridRegion.value) {
    startRectDrag(screenX, screenY, norm)
    return
  }

  if (isEraserActive.value) {
    handleEraserDown(screenX, screenY)
    return
  }

  if (props.gridState?.isActive) {
    if (handleGridHandleDown(screenX, screenY)) {
      return
    }
    if (handleGridQuadDown(screenX, screenY, norm)) {
      return
    }
    e.preventDefault()
    props.viewport.startPan(e.clientX, e.clientY)
    return
  }

  if (props.activeMode === 'pan') {
    e.preventDefault()
    if (props.clickSelectOnPan && !props.canEdit) {
      const hitPlot = findPlotAtPoint(screenX, screenY)
      panClickCandidate.value = {
        clientX: e.clientX,
        clientY: e.clientY,
        modifier: e.shiftKey || e.ctrlKey || e.metaKey,
        hitPlotNumber: hitPlot ? hitPlot.plot_number : null,
      }
    } else {
      panClickCandidate.value = null
    }
    props.viewport.startPan(e.clientX, e.clientY)
    return
  }

  if (props.activeMode === 'select') {
    handleViewModeDown(screenX, screenY, norm, e)
    return
  }

  if (props.activeMode === 'draw') {
    handleDrawModeDown(screenX, screenY, norm)
  }
}

function onMouseMove(e: MouseEvent): void {
  if (props.viewport.isRotating.value) {
    const { screenX, screenY } = getCanvasRelativeCoords(e)
    const w = containerRef.value?.clientWidth
    const h = containerRef.value?.clientHeight
    if (props.viewport.updateRotate(screenX, screenY, w, h)) {
      drawCanvas()
    }
    return
  }

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

  if (isSelectingGridRegion.value) {
    if (isDraggingRect.value) {
      rectCurrentNorm.value = norm
      drawCanvas()
    }
    return
  }

  if (isEraserActive.value) {
    handleEraserMove(screenX, screenY)
    return
  }

  if (props.gridState?.isActive) {
    if (draggingGridCornerIndex.value !== null) {
      emit('update-grid-corner', {
        index: draggingGridCornerIndex.value,
        point: norm,
      })
      drawCanvas()
    } else if (isDraggingWholeGrid.value && gridDragStartNorm.value && gridDragStartCorners.value) {
      handleGridDragMove(norm)
      drawCanvas()
    } else if (!isEraserActive.value) {
      handleGridHoverMove(screenX, screenY)
    }
    return
  }

  // 頂點微調拖曳中
  if (draggingVertexIndex.value !== null && effectiveSelectedPlotNumbers.value.length === 1) {
    const singleNumber = effectiveSelectedPlotNumbers.value[0]
    const selectedPlot = props.plots.find((p) => p.plot_number === singleNumber)
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

  // 整體小區拖曳中
  if (isDraggingWholePlot.value && wholePlotDragStartNorm.value) {
    wholePlotCurrentDelta.value = {
      dx: norm.x - wholePlotDragStartNorm.value.x,
      dy: norm.y - wholePlotDragStartNorm.value.y,
    }
    drawCanvas()
    return
  }

  // 空白處框選拖曳中
  if (isRubberBandSelecting.value) {
    rubberBandCurrentNorm.value = norm
    drawCanvas()
    return
  }

  // 矩形拖曳拉框中
  if (isDraggingRect.value && rectStartNorm.value) {
    rectCurrentNorm.value = norm
    drawCanvas()
    return
  }

  // 選取模式下懸停選中小區頂點把手檢測 (僅在單選時)
  if (
    props.activeMode === 'select' &&
    effectiveSelectedPlotNumbers.value.length === 1 &&
    !props.gridState?.isActive &&
    !isDraggingWholePlot.value &&
    draggingVertexIndex.value === null
  ) {
    const singleNumber = effectiveSelectedPlotNumbers.value[0]
    const selectedPlot = props.plots.find((p) => p.plot_number === singleNumber)
    const hitIdx = selectedPlot ? findVertexNearPoint(screenX, screenY, selectedPlot) : null
    if (hoveredVertexIndex.value !== hitIdx) {
      hoveredVertexIndex.value = hitIdx
      drawCanvas()
    }
  } else if (hoveredVertexIndex.value !== null && draggingVertexIndex.value === null) {
    hoveredVertexIndex.value = null
    drawCanvas()
  }

  // 多邊形點繪起點吸附
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

function onMouseUp(e: MouseEvent): void {
  isErasing.value = false

  if (draggingGridCornerIndex.value !== null) {
    draggingGridCornerIndex.value = null
    drawCanvas()
    return
  }

  if (isDraggingWholeGrid.value) {
    finishGridDrag()
    drawCanvas()
    return
  }

  if (draggingVertexIndex.value !== null) {
    draggingVertexIndex.value = null
    drawCanvas()
    return
  }

  if (props.viewport.isRotating.value) {
    props.viewport.endRotate()
    drawCanvas()
    return
  }

  if (props.viewport.isPanning.value) {
    props.viewport.endPan()
    const candidate = panClickCandidate.value
    panClickCandidate.value = null
    if (candidate && props.clickSelectOnPan && !props.canEdit) {
      const moveDist = Math.hypot(e.clientX - candidate.clientX, e.clientY - candidate.clientY)
      if (moveDist <= 5) {
        if (candidate.hitPlotNumber !== null) {
          if (candidate.modifier) {
            const cur = effectiveSelectedPlotNumbers.value
            const next = cur.includes(candidate.hitPlotNumber)
              ? cur.filter((n) => n !== candidate.hitPlotNumber)
              : [...cur, candidate.hitPlotNumber]
            emit('select-plots', next)
            if (next.length <= 1) {
              emit('select-plot', next.length === 1 ? next[0] : null)
            }
          } else {
            emit('select-plots', [candidate.hitPlotNumber])
            emit('select-plot', candidate.hitPlotNumber)
          }
        } else if (!candidate.modifier) {
          emit('select-plots', [])
          emit('select-plot', null)
        }
      }
    }
    return
  }

  const { screenX, screenY, norm } = getCanvasRelativeCoords(e)

  if (isDraggingWholePlot.value) {
    finishWholePlotDrag()
    drawCanvas()
    return
  }

  if (isRubberBandSelecting.value) {
    finishRubberBandSelection(screenX, screenY)
    return
  }

  if (isDraggingRect.value) {
    rectCurrentNorm.value = norm
    finishRectDrag(screenX, screenY)
    drawCanvas()
    return
  }

  draggingVertexIndex.value = null
}

function onMouseLeave(e: MouseEvent): void {
  panClickCandidate.value = null
  hoveredGridCornerIndex.value = null
  isHoveringGridQuad.value = false
  hoveredVertexIndex.value = null
  if (isRubberBandSelecting.value) {
    isRubberBandSelecting.value = false
    rubberBandStartScreen.value = null
    rubberBandStartNorm.value = null
    rubberBandCurrentNorm.value = null
    isRubberBandModifier.value = false
    drawCanvas()
  }
  onMouseUp(e)
}

function onWheel(e: WheelEvent): void {
  e.preventDefault()
  if (!canvasRef.value) return
  const rect = canvasRef.value.getBoundingClientRect()
  const screenX = e.clientX - rect.left
  const screenY = e.clientY - rect.top

  if (e.altKey) {
    const deltaDeg = e.deltaY < 0 ? 5 : -5
    const pivot = getViewportPivot()
    props.viewport.rotateAtScreenPoint(pivot.x, pivot.y, deltaDeg, rect.width, rect.height)
    drawCanvas()
    return
  }

  const factor = e.deltaY < 0 ? 1.15 : 0.87
  props.viewport.zoomAtScreenPoint(screenX, screenY, factor, rect.width, rect.height)
  drawCanvas()
}

function onDblClick(e: MouseEvent): void {
  if (props.activeMode === 'draw' && props.drawTool === 'polygon' && currentDrawingPoints.value.length >= 3) {
    finishDrawing()
    return
  }

  if (props.activeMode === 'select' && props.canEdit && !props.gridState?.isActive) {
    const { screenX, screenY } = getCanvasRelativeCoords(e)
    const hitPlot = findPlotAtPoint(screenX, screenY)
    if (hitPlot) {
      if (effectiveSelectedPlotNumbers.value.includes(hitPlot.plot_number) && effectiveSelectedPlotNumbers.value.length > 1) {
        const selectedPlots = props.plots.filter((p) => effectiveSelectedPlotNumbers.value.includes(p.plot_number))
        emit('edit-plots', selectedPlots)
      } else {
        emit('select-plots', [hitPlot.plot_number])
        emit('select-plot', hitPlot.plot_number)
        emit('edit-plot', hitPlot)
      }
    }
  }
}

function onKeyDown(e: KeyboardEvent): void {
  const targetTag = (e.target as HTMLElement)?.tagName?.toLowerCase()
  if (targetTag === 'input' || targetTag === 'textarea' || targetTag === 'select') return

  if (e.key === 'Delete' || e.key === 'Backspace') {
    if (props.canEdit && effectiveSelectedPlotNumbers.value.length > 0 && !isDraggingRect.value && currentDrawingPoints.value.length === 0) {
      e.preventDefault()
      if (effectiveSelectedPlotNumbers.value.length === 1) {
        emit('delete-plot', effectiveSelectedPlotNumbers.value[0])
      } else {
        emit('delete-plots', [...effectiveSelectedPlotNumbers.value])
      }
    }
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'd') {
    if (props.canEdit && effectiveSelectedPlotNumbers.value.length > 0) {
      e.preventDefault()
      if (effectiveSelectedPlotNumbers.value.length === 1) {
        emit('duplicate-plot', effectiveSelectedPlotNumbers.value[0])
      } else {
        emit('duplicate-plots', [...effectiveSelectedPlotNumbers.value])
      }
    }
  } else if (e.key === 'Escape') {
    cancelDrawing()
    emit('select-plots', [])
    emit('select-plot', null)
  }
}

function finishDrawing(): void {
  if (currentDrawingPoints.value.length >= 3) {
    emit('plot-drawn', [...currentDrawingPoints.value])
  }
  currentDrawingPoints.value = []
  isNearStartPoint.value = false
  drawCanvas()
}

function undoLastPoint(): void {
  if (currentDrawingPoints.value.length > 0) {
    currentDrawingPoints.value.pop()
    drawCanvas()
  }
}

function cancelDrawing(): void {
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
  window.addEventListener('keydown', onKeyDown)
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
  window.removeEventListener('keydown', onKeyDown)
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
    props.selectedPlotNumbers,
    props.gridState?.isActive,
    props.gridState?.corners,
    props.gridState?.rows,
    props.gridState?.cols,
    props.gridState?.marginRatio,
    props.gridState?.scaleX,
    props.gridState?.scaleY,
    props.gridState?.paddingRatio,
    props.gridState?.offsetX,
    props.gridState?.offsetY,
    props.gridState?.excludedIndices,
    props.previewPlots,
    props.viewport.scale.value,
    props.viewport.rotation.value,
    props.viewport.isRotating.value,
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
    draggingVertexIndex.value = null
    hoveredVertexIndex.value = null
    if (newMode !== 'draw') {
      cancelDrawing()
    }
    if (newMode !== 'select') {
      isRubberBandSelecting.value = false
      rubberBandStartScreen.value = null
      rubberBandStartNorm.value = null
      rubberBandCurrentNorm.value = null
      isRubberBandModifier.value = false
      isDraggingWholePlot.value = false
    }
    if (newMode === 'draw') {
      emit('select-plots', [])
      emit('select-plot', null)
    }
  }
)

watch(
  () => props.gridState?.isActive,
  (active) => {
    cancelDrawing()
    finishGridDrag()
    draggingGridCornerIndex.value = null
    hoveredGridCornerIndex.value = null
    isHoveringGridQuad.value = false
    isRubberBandSelecting.value = false
    isDraggingWholePlot.value = false
    if (active) {
      draggingVertexIndex.value = null
      hoveredVertexIndex.value = null
      emit('select-plots', [])
      emit('select-plot', null)
    }
  }
)
</script>

<template>
  <div
    ref="containerRef"
    class="absolute inset-0 pointer-events-auto select-none"
    :class="{
      'cursor-grab': !viewport.isPanning.value && !viewport.isRotating.value && (isRotateToolActive || (activeMode === 'pan' && !gridState?.isActive) || (gridState?.isActive && !isSelectingGridRegion && !isEraserActive && hoveredGridCornerIndex === null && draggingGridCornerIndex === null && !isHoveringGridQuad && !isDraggingWholeGrid) || (gridState?.isActive && hoveredGridCornerIndex !== null && draggingGridCornerIndex === null && !isEraserActive) || (activeMode === 'select' && hoveredVertexIndex !== null && draggingVertexIndex === null && !gridState?.isActive)),
      'cursor-grabbing': viewport.isPanning.value || viewport.isRotating.value || draggingGridCornerIndex !== null || draggingVertexIndex !== null || isDraggingWholeGrid,
      'cursor-move': !isRotateToolActive && !viewport.isRotating.value && !viewport.isPanning.value && ((gridState?.isActive && isHoveringGridQuad && hoveredGridCornerIndex === null && draggingGridCornerIndex === null && !isDraggingWholeGrid && !isEraserActive) || isDraggingWholePlot),
      'cursor-pointer': !isRotateToolActive && !viewport.isRotating.value && !viewport.isPanning.value && ((activeMode === 'select' && !gridState?.isActive && hoveredVertexIndex === null && draggingVertexIndex === null && !isRubberBandSelecting) || (isEraserActive && !isSelectingGridRegion)),
      'cursor-crosshair': !isRotateToolActive && !viewport.isRotating.value && !viewport.isPanning.value && (isSelectingGridRegion || (activeMode === 'draw' && !isEraserActive && !gridState?.isActive) || isRubberBandSelecting),
    }"
    @mousedown="onMouseDown"
    @mousemove="onMouseMove"
    @mouseup="onMouseUp"
    @mouseleave="onMouseLeave"
    @wheel="onWheel"
    @auxclick.prevent
    @contextmenu.prevent
    @dblclick="onDblClick"
  >
    <canvas ref="canvasRef" class="w-full h-full block" />
  </div>
</template>
