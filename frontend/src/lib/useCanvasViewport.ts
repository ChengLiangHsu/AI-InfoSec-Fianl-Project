import { ref, computed } from 'vue'
import type { NormalizedPoint } from './usePlots'

export const MIN_SCALE = 0.2
export const MAX_SCALE = 15.0
export const ZOOM_STEP = 1.25
export const ROTATE_STEP_DEG = 15

export function normalizeRotationDeg(deg: number): number {
  let normalized = (((deg + 180) % 360) + 360) % 360 - 180
  if (normalized <= -180) normalized += 360
  if (Object.is(normalized, -0)) normalized = 0
  return Number(normalized.toFixed(2))
}

export function clampPanBounds(
  targetPanX: number,
  targetPanY: number,
  currentWidth: number,
  currentHeight: number,
  viewportWidth: number,
  viewportHeight: number,
  minVisibleRatio = 0.2,
  rotationDeg = 0
): { panX: number; panY: number } {
  if (viewportWidth <= 0 || viewportHeight <= 0 || currentWidth <= 0 || currentHeight <= 0) {
    return { panX: targetPanX, panY: targetPanY }
  }

  let relMinX = 0
  let relMaxX = currentWidth
  let relMinY = 0
  let relMaxY = currentHeight

  if (rotationDeg !== 0) {
    const rad = (rotationDeg * Math.PI) / 180
    const cos = Math.cos(rad)
    const sin = Math.sin(rad)
    const xs = [0, currentWidth * cos, currentWidth * cos - currentHeight * sin, -currentHeight * sin]
    const ys = [0, currentWidth * sin, currentWidth * sin + currentHeight * cos, currentHeight * cos]
    relMinX = Math.min(...xs)
    relMaxX = Math.max(...xs)
    relMinY = Math.min(...ys)
    relMaxY = Math.max(...ys)
  }

  const bboxW = relMaxX - relMinX
  const bboxH = relMaxY - relMinY
  const minVisibleW = bboxW * minVisibleRatio
  const minVisibleH = bboxH * minVisibleRatio

  const minPanX = minVisibleW - relMaxX
  const maxPanX = viewportWidth - minVisibleW - relMinX

  const minPanY = minVisibleH - relMaxY
  const maxPanY = viewportHeight - minVisibleH - relMinY

  return {
    panX: Math.max(minPanX, Math.min(maxPanX, targetPanX)),
    panY: Math.max(minPanY, Math.min(maxPanY, targetPanY)),
  }
}

export function useCanvasViewport() {
  const panX = ref(0)
  const panY = ref(0)
  const scale = ref(1.0)
  const rotation = ref(0)
  const baseWidth = ref(0)
  const baseHeight = ref(0)
  const isPanning = ref(false)
  const isRotating = ref(false)
  const rotatePivotX = ref(0)
  const rotatePivotY = ref(0)

  const dragStartX = ref(0)
  const dragStartY = ref(0)
  const rotateLastAngle = ref<number | null>(null)

  const zoomPercentage = computed(() => Math.round(scale.value * 100))
  const rotationDegrees = computed(() => Math.round(rotation.value))

  function clampScale(val: number): number {
    return Math.max(MIN_SCALE, Math.min(MAX_SCALE, val))
  }

  function setBaseDimensions(width: number, height: number): void {
    baseWidth.value = width
    baseHeight.value = height
  }

  function getDefaultPivot(viewportWidth?: number, viewportHeight?: number): { x: number; y: number } {
    if (viewportWidth && viewportHeight) {
      return { x: viewportWidth / 2, y: viewportHeight / 2 }
    }
    return normalizedToScreen({ x: 0.5, y: 0.5 })
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
        viewportHeight,
        0.2,
        rotation.value
      )
      nextPanX = clamped.panX
      nextPanY = clamped.panY
    }

    panX.value = nextPanX
    panY.value = nextPanY
    scale.value = newScale
  }

  function zoomIn(viewportWidth?: number, viewportHeight?: number): void {
    const pivot = getDefaultPivot(viewportWidth, viewportHeight)
    zoomAtScreenPoint(pivot.x, pivot.y, ZOOM_STEP, viewportWidth, viewportHeight)
  }

  function zoomOut(viewportWidth?: number, viewportHeight?: number): void {
    const pivot = getDefaultPivot(viewportWidth, viewportHeight)
    zoomAtScreenPoint(pivot.x, pivot.y, 1 / ZOOM_STEP, viewportWidth, viewportHeight)
  }

  function rotateAtScreenPoint(
    pivotX: number,
    pivotY: number,
    deltaDeg: number,
    viewportWidth?: number,
    viewportHeight?: number
  ): void {
    if (baseWidth.value <= 0 || baseHeight.value <= 0 || deltaDeg === 0) return
    const nextRotation = normalizeRotationDeg(rotation.value + deltaDeg)
    const rad = (deltaDeg * Math.PI) / 180
    const cos = Math.cos(rad)
    const sin = Math.sin(rad)

    const ox = panX.value - pivotX
    const oy = panY.value - pivotY
    let nextPanX = pivotX + ox * cos - oy * sin
    let nextPanY = pivotY + ox * sin + oy * cos

    if (viewportWidth && viewportHeight) {
      const clamped = clampPanBounds(
        nextPanX,
        nextPanY,
        baseWidth.value * scale.value,
        baseHeight.value * scale.value,
        viewportWidth,
        viewportHeight,
        0.2,
        nextRotation
      )
      nextPanX = clamped.panX
      nextPanY = clamped.panY
    }

    panX.value = nextPanX
    panY.value = nextPanY
    rotation.value = nextRotation
  }

  function rotateBy(deltaDeg: number, viewportWidth?: number, viewportHeight?: number): void {
    const pivot = getDefaultPivot(viewportWidth, viewportHeight)
    rotateAtScreenPoint(pivot.x, pivot.y, deltaDeg, viewportWidth, viewportHeight)
  }

  function resetRotation(viewportWidth?: number, viewportHeight?: number): void {
    if (rotation.value === 0) return
    rotateBy(-rotation.value, viewportWidth, viewportHeight)
    rotation.value = 0
  }

  function startRotate(screenX: number, screenY: number, pivotX: number, pivotY: number): void {
    isRotating.value = true
    rotatePivotX.value = pivotX
    rotatePivotY.value = pivotY
    const dist = Math.hypot(screenX - pivotX, screenY - pivotY)
    rotateLastAngle.value = dist >= 12 ? Math.atan2(screenY - pivotY, screenX - pivotX) : null
  }

  function updateRotate(
    screenX: number,
    screenY: number,
    viewportWidth?: number,
    viewportHeight?: number
  ): boolean {
    if (!isRotating.value) return false
    const dist = Math.hypot(screenX - rotatePivotX.value, screenY - rotatePivotY.value)
    if (dist < 12) return false

    const currentAngle = Math.atan2(screenY - rotatePivotY.value, screenX - rotatePivotX.value)
    if (rotateLastAngle.value === null) {
      rotateLastAngle.value = currentAngle
      return false
    }

    let deltaRad = currentAngle - rotateLastAngle.value
    if (deltaRad > Math.PI) deltaRad -= Math.PI * 2
    if (deltaRad < -Math.PI) deltaRad += Math.PI * 2
    rotateLastAngle.value = currentAngle

    const deltaDeg = (deltaRad * 180) / Math.PI
    if (Math.abs(deltaDeg) < 0.001) return false

    rotateAtScreenPoint(rotatePivotX.value, rotatePivotY.value, deltaDeg, viewportWidth, viewportHeight)
    return true
  }

  function endRotate(): void {
    isRotating.value = false
    rotateLastAngle.value = null
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
        viewportHeight,
        0.2,
        rotation.value
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
    rotation.value = 0
    isRotating.value = false
    panX.value = (viewportWidth - fittedW) / 2
    panY.value = (viewportHeight - fittedH) / 2
  }

  function screenToNormalized(screenX: number, screenY: number): NormalizedPoint {
    const currentW = baseWidth.value * scale.value
    const currentH = baseHeight.value * scale.value
    if (currentW <= 0 || currentH <= 0) {
      return { x: 0, y: 0 }
    }
    const dx = screenX - panX.value
    const dy = screenY - panY.value

    let localX = dx
    let localY = dy
    if (rotation.value !== 0) {
      const rad = (rotation.value * Math.PI) / 180
      const cos = Math.cos(rad)
      const sin = Math.sin(rad)
      localX = dx * cos + dy * sin
      localY = -dx * sin + dy * cos
    }

    const nx = localX / currentW
    const ny = localY / currentH
    return {
      x: Math.max(0, Math.min(1, nx)),
      y: Math.max(0, Math.min(1, ny)),
    }
  }

  function normalizedToScreen(pt: NormalizedPoint): { x: number; y: number } {
    const currentW = baseWidth.value * scale.value
    const currentH = baseHeight.value * scale.value
    const localX = pt.x * currentW
    const localY = pt.y * currentH

    if (rotation.value === 0) {
      return {
        x: panX.value + localX,
        y: panY.value + localY,
      }
    }

    const rad = (rotation.value * Math.PI) / 180
    const cos = Math.cos(rad)
    const sin = Math.sin(rad)
    return {
      x: panX.value + localX * cos - localY * sin,
      y: panY.value + localX * sin + localY * cos,
    }
  }

  function resetTransform(): void {
    scale.value = 1.0
    rotation.value = 0
    panX.value = 0
    panY.value = 0
    isPanning.value = false
    isRotating.value = false
    rotateLastAngle.value = null
  }

  return {
    panX,
    panY,
    scale,
    rotation,
    baseWidth,
    baseHeight,
    isPanning,
    isRotating,
    rotatePivotX,
    rotatePivotY,
    zoomPercentage,
    rotationDegrees,
    setBaseDimensions,
    zoomAtScreenPoint,
    zoomIn,
    zoomOut,
    rotateAtScreenPoint,
    rotateBy,
    resetRotation,
    startRotate,
    updateRotate,
    endRotate,
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

