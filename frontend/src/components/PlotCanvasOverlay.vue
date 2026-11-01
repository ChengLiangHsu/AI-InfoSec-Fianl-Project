<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import {
  type PlotItem,
  type NormalizedPoint,
  parseCoords,
} from '@/lib/usePlots'
import type { CanvasViewport } from '@/lib/useCanvasViewport'

const props = defineProps<{
  plots: PlotItem[]
  activeMode: 'view' | 'draw' | 'assign'
  selectedPlotNumber: number | null
  getPlotColor: (plot: PlotItem) => string
  viewport: CanvasViewport
}>()

const emit = defineEmits<{
  (e: 'add-plot', points: NormalizedPoint[]): void
  (e: 'update-plot-points', payload: { plotNumber: number; points: NormalizedPoint[] }): void
  (e: 'select-plot', plotNumber: number | null): void
  (e: 'assign-plot', plotNumber: number): void
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)

// 繪製中的暫態資料
const currentDrawingPoints = ref<NormalizedPoint[]>([])
const currentMousePos = ref<NormalizedPoint | null>(null)
const isNearStartPoint = ref(false)
const draggingVertexIndex = ref<number | null>(null)

const SNAP_THRESHOLD_PX = 18

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
  drawCurrentDrawingPolyline(ctx)

  ctx.restore()
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

    // 邊框繪製（固定螢幕像素寬度）
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

  // 2. 僅滑鼠左鍵進行幾何標註與操作
  if (e.button !== 0) return

  const { screenX, screenY, norm } = getCanvasRelativeCoords(e)

  if (props.activeMode === 'assign') {
    const hitPlot = findPlotAtPoint(screenX, screenY)
    if (hitPlot) {
      emit('assign-plot', hitPlot.plot_number)
      emit('select-plot', hitPlot.plot_number)
    }
    return
  }

  if (props.activeMode === 'view') {
    const hitPlot = findPlotAtPoint(screenX, screenY)
    emit('select-plot', hitPlot ? hitPlot.plot_number : null)
    return
  }

  if (props.activeMode === 'draw') {
    // 檢查是否點擊在已選取小區的頂點手柄上以進行拖曳
    if (props.selectedPlotNumber !== null && currentDrawingPoints.value.length === 0) {
      const selectedPlot = props.plots.find((p) => p.plot_number === props.selectedPlotNumber)
      if (selectedPlot) {
        const vIdx = findVertexNearPoint(screenX, screenY, selectedPlot)
        if (vIdx !== null) {
          draggingVertexIndex.value = vIdx
          return
        }
      }
    }

    // 若已在繪製中
    if (currentDrawingPoints.value.length > 0) {
      // 靠近起點吸附閉合
      if (isNearStartPoint.value && currentDrawingPoints.value.length >= 3) {
        finishDrawing()
        return
      }
      // 加入新頂點
      currentDrawingPoints.value.push({ x: norm.x, y: norm.y })
      drawCanvas()
      return
    }

    // 尚未開始繪製：若點到既有小區則選取它
    const hitPlot = findPlotAtPoint(screenX, screenY)
    if (hitPlot) {
      emit('select-plot', hitPlot.plot_number)
    } else {
      // 點在空白處：開啟新小區繪製
      emit('select-plot', null)
      currentDrawingPoints.value = [{ x: norm.x, y: norm.y }]
      drawCanvas()
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

  // 2. 頂點拖曳微調
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

  // 3. 繪製中的起點吸附判定
  if (currentDrawingPoints.value.length >= 3) {
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
  if (e.button === 2 || props.viewport.isPanning.value) {
    props.viewport.endPan()
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
  if (props.activeMode === 'draw' && currentDrawingPoints.value.length >= 3) {
    finishDrawing()
  }
}

function finishDrawing() {
  if (currentDrawingPoints.value.length >= 3) {
    emit('add-plot', [...currentDrawingPoints.value])
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
  isNearStartPoint.value = false
  drawCanvas()
}

defineExpose({
  undoLastPoint,
  cancelDrawing,
  syncCanvasSize,
  redraw: drawCanvas,
  isDrawing: () => currentDrawingPoints.value.length > 0,
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
    props.selectedPlotNumber,
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
      currentDrawingPoints.value = []
      isNearStartPoint.value = false
      drawCanvas()
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
      'cursor-pointer': activeMode === 'assign' || activeMode === 'view',
      'cursor-crosshair': activeMode === 'draw' && !viewport.isPanning.value,
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
