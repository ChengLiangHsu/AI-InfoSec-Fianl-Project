import { ref, computed } from 'vue'
import type { NormalizedPoint } from './usePlots'

export const MIN_SCALE = 0.2
export const MAX_SCALE = 15.0
export const ZOOM_STEP = 1.25

export function clampPanBounds(
  targetPanX: number,
  targetPanY: number,
  currentWidth: number,
  currentHeight: number,
  viewportWidth: number,
  viewportHeight: number,
  minVisibleRatio = 0.2
): { panX: number; panY: number } {
  if (viewportWidth <= 0 || viewportHeight <= 0 || currentWidth <= 0 || currentHeight <= 0) {
    return { panX: targetPanX, panY: targetPanY }
  }

  const minVisibleW = currentWidth * minVisibleRatio
  const minVisibleH = currentHeight * minVisibleRatio

  const minPanX = minVisibleW - currentWidth
  const maxPanX = viewportWidth - minVisibleW

  const minPanY = minVisibleH - currentHeight
  const maxPanY = viewportHeight - minVisibleH

  return {
    panX: Math.max(minPanX, Math.min(maxPanX, targetPanX)),
    panY: Math.max(minPanY, Math.min(maxPanY, targetPanY)),
  }
}

export function useCanvasViewport() {
  const panX = ref(0)
  const panY = ref(0)
  const scale = ref(1.0)
  const baseWidth = ref(0)
  const baseHeight = ref(0)
  const isPanning = ref(false)

  const dragStartX = ref(0)
  const dragStartY = ref(0)

  const zoomPercentage = computed(() => Math.round(scale.value * 100))

  function clampScale(val: number): number {
    return Math.max(MIN_SCALE, Math.min(MAX_SCALE, val))
  }

  function setBaseDimensions(width: number, height: number): void {
    baseWidth.value = width
    baseHeight.value = height
  }

  function zoomAtScreenPoint(
    screenX: number,
    screenY: number,
    factor: number,
    viewportWidth?: number,
    viewportHeight?: number
  ): void {
    if (baseWidth.value <= 0 || baseHeight.value <= 0) return
    const newScale = clampScale(scale.value * factor)
    if (newScale === scale.value) return

    const ratio = newScale / scale.value
    let nextPanX = screenX - (screenX - panX.value) * ratio
    let nextPanY = screenY - (screenY - panY.value) * ratio

    if (viewportWidth && viewportHeight) {
      const clamped = clampPanBounds(
        nextPanX,
        nextPanY,
        baseWidth.value * newScale,
        baseHeight.value * newScale,
        viewportWidth,
        viewportHeight
      )
      nextPanX = clamped.panX
      nextPanY = clamped.panY
    }

    panX.value = nextPanX
    panY.value = nextPanY
    scale.value = newScale
  }

  function zoomIn(viewportWidth?: number, viewportHeight?: number): void {
    const cx = viewportWidth ? viewportWidth / 2 : panX.value + (baseWidth.value * scale.value) / 2
    const cy = viewportHeight ? viewportHeight / 2 : panY.value + (baseHeight.value * scale.value) / 2
    zoomAtScreenPoint(cx, cy, ZOOM_STEP, viewportWidth, viewportHeight)
  }

  function zoomOut(viewportWidth?: number, viewportHeight?: number): void {
    const cx = viewportWidth ? viewportWidth / 2 : panX.value + (baseWidth.value * scale.value) / 2
    const cy = viewportHeight ? viewportHeight / 2 : panY.value + (baseHeight.value * scale.value) / 2
    zoomAtScreenPoint(cx, cy, 1 / ZOOM_STEP, viewportWidth, viewportHeight)
  }

  function startPan(screenX: number, screenY: number): void {
    isPanning.value = true
    dragStartX.value = screenX
    dragStartY.value = screenY
  }

  function updatePan(
    screenX: number,
    screenY: number,
    viewportWidth?: number,
    viewportHeight?: number
  ): boolean {
    if (!isPanning.value) return false
    const dx = screenX - dragStartX.value
    const dy = screenY - dragStartY.value

    let nextPanX = panX.value + dx
    let nextPanY = panY.value + dy

    if (viewportWidth && viewportHeight) {
      const clamped = clampPanBounds(
        nextPanX,
        nextPanY,
        baseWidth.value * scale.value,
        baseHeight.value * scale.value,
        viewportWidth,
        viewportHeight
      )
      nextPanX = clamped.panX
      nextPanY = clamped.panY
    }

    panX.value = nextPanX
    panY.value = nextPanY
    dragStartX.value = screenX
    dragStartY.value = screenY
    return true
  }

  function endPan(): void {
    isPanning.value = false
  }

  function fitToViewport(
    viewportWidth: number,
    viewportHeight: number,
    imageNaturalWidth: number,
    imageNaturalHeight: number,
    padding = 32
  ): void {
    if (viewportWidth <= 0 || viewportHeight <= 0 || imageNaturalWidth <= 0 || imageNaturalHeight <= 0) {
      return
    }

    const availW = Math.max(100, viewportWidth - padding * 2)
    const availH = Math.max(100, viewportHeight - padding * 2)
    const imgAspect = imageNaturalWidth / imageNaturalHeight
    const viewportAspect = availW / availH

    let fittedW: number
    let fittedH: number

    if (imgAspect > viewportAspect) {
      fittedW = availW
      fittedH = availW / imgAspect
    } else {
      fittedH = availH
      fittedW = availH * imgAspect
    }

    baseWidth.value = fittedW
    baseHeight.value = fittedH
    scale.value = 1.0
    panX.value = (viewportWidth - fittedW) / 2
    panY.value = (viewportHeight - fittedH) / 2
  }

  function screenToNormalized(screenX: number, screenY: number): NormalizedPoint {
    const currentW = baseWidth.value * scale.value
    const currentH = baseHeight.value * scale.value
    if (currentW <= 0 || currentH <= 0) {
      return { x: 0, y: 0 }
    }
    const nx = (screenX - panX.value) / currentW
    const ny = (screenY - panY.value) / currentH
    return {
      x: Math.max(0, Math.min(1, nx)),
      y: Math.max(0, Math.min(1, ny)),
    }
  }

  function normalizedToScreen(pt: NormalizedPoint): { x: number; y: number } {
    const currentW = baseWidth.value * scale.value
    const currentH = baseHeight.value * scale.value
    return {
      x: panX.value + pt.x * currentW,
      y: panY.value + pt.y * currentH,
    }
  }

  function resetTransform(): void {
    scale.value = 1.0
    panX.value = 0
    panY.value = 0
    isPanning.value = false
  }

  return {
    panX,
    panY,
    scale,
    baseWidth,
    baseHeight,
    isPanning,
    zoomPercentage,
    setBaseDimensions,
    zoomAtScreenPoint,
    zoomIn,
    zoomOut,
    startPan,
    updatePan,
    endPan,
    fitToViewport,
    screenToNormalized,
    normalizedToScreen,
    resetTransform,
    clampPanBounds,
  }
}

export type CanvasViewport = ReturnType<typeof useCanvasViewport>

