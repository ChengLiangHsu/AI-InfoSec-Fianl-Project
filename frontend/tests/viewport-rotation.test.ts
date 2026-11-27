import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PlotCanvasOverlay from '@/components/PlotCanvasOverlay.vue'
import { useCanvasViewport, normalizeRotationDeg, clampPanBounds } from '@/lib/useCanvasViewport'
import { usePlots } from '@/lib/usePlots'

beforeEach(() => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null)
})

function createMountedCanvas(options?: {
  activeMode?: 'view' | 'draw'
  drawTool?: 'rect' | 'polygon' | 'eraser'
  isRotateToolActive?: boolean
  gridActive?: boolean
}) {
  const plots = usePlots()
  if (options?.gridActive) {
    plots.startGridMode()
  }
  const viewport = useCanvasViewport()
  viewport.fitToViewport(1000, 1000, 1000, 1000, 0)

  const canvas = mount(PlotCanvasOverlay, {
    props: {
      plots: plots.plots.value,
      activeMode: options?.activeMode ?? 'view',
      drawTool: options?.drawTool ?? 'rect',
      isRotateToolActive: options?.isRotateToolActive ?? false,
      gridState: plots.gridState.value,
      viewport,
      getPlotColor: () => '#ffffff',
      'onUpdate-grid-corners': plots.updateGridCorners,
    },
  })

  return { plots, viewport, canvas }
}

describe('useCanvasViewport rotation math', () => {
  it('normalizes rotation angles into (-180, 180]', () => {
    expect(normalizeRotationDeg(0)).toBe(0)
    expect(normalizeRotationDeg(360)).toBe(0)
    expect(normalizeRotationDeg(-180)).toBe(180)
    expect(normalizeRotationDeg(190)).toBe(-170)
    expect(normalizeRotationDeg(-190)).toBe(170)
  })

  it('round-trips screenToNormalized and normalizedToScreen under pan, scale, and rotation', () => {
    const viewport = useCanvasViewport()
    viewport.setBaseDimensions(800, 600)
    viewport.scale.value = 1.75
    viewport.panX.value = 140
    viewport.panY.value = 95
    viewport.rotation.value = 37

    const original = { x: 0.32, y: 0.68 }
    const screen = viewport.normalizedToScreen(original)
    const recovered = viewport.screenToNormalized(screen.x, screen.y)

    expect(recovered.x).toBeCloseTo(original.x, 5)
    expect(recovered.y).toBeCloseTo(original.y, 5)
  })

  it('keeps the pivot image point stationary during rotation and zoom', () => {
    const viewport = useCanvasViewport()
    viewport.fitToViewport(1000, 800, 1000, 800, 0)

    const pivot = { x: 620, y: 340 }
    const beforeNorm = viewport.screenToNormalized(pivot.x, pivot.y)

    viewport.rotateAtScreenPoint(pivot.x, pivot.y, 42, 1000, 800)
    const afterRotateNorm = viewport.screenToNormalized(pivot.x, pivot.y)
    expect(afterRotateNorm.x).toBeCloseTo(beforeNorm.x, 5)
    expect(afterRotateNorm.y).toBeCloseTo(beforeNorm.y, 5)

    viewport.zoomAtScreenPoint(pivot.x, pivot.y, 1.5, 1000, 800)
    const afterZoomNorm = viewport.screenToNormalized(pivot.x, pivot.y)
    expect(afterZoomNorm.x).toBeCloseTo(beforeNorm.x, 5)
    expect(afterZoomNorm.y).toBeCloseTo(beforeNorm.y, 5)
  })

  it('clamps pan bounds using rotated bounding box dimensions', () => {
    const clamped = clampPanBounds(900, 900, 600, 400, 800, 800, 0.2, 90)
    // At 90deg, image spans x: [panX - 400, panX], y: [panY, panY + 600]
    // maxPanX = 800 - 0.2*400 - (-400) = 1120, so panX=900 is valid
    expect(clamped.panX).toBe(900)
    // maxPanY = 800 - 0.2*600 - 0 = 680, so panY=900 clamps to 680
    expect(clamped.panY).toBe(680)
  })
})

describe('PlotCanvasOverlay mouse rotation interactions', () => {
  it('rotates the viewport via middle-mouse drag around center', async () => {
    const { viewport, canvas } = createMountedCanvas()

    // Image center is (500, 500). Drag from (700, 500) [0deg] to (500, 700) [+90deg]
    await canvas.trigger('mousedown', { button: 1, clientX: 700, clientY: 500 })
    expect(viewport.isRotating.value).toBe(true)

    await canvas.trigger('mousemove', { clientX: 500, clientY: 700 })
    expect(viewport.rotation.value).toBeCloseTo(90, 1)

    await canvas.trigger('mouseup', { button: 1, clientX: 500, clientY: 700 })
    expect(viewport.isRotating.value).toBe(false)
  })

  it('rotates via Shift+Right-drag while keeping plain Right-drag as pan', async () => {
    const { viewport, canvas } = createMountedCanvas()

    // Shift + Right-drag rotates
    await canvas.trigger('mousedown', { button: 2, shiftKey: true, clientX: 700, clientY: 500 })
    await canvas.trigger('mousemove', { clientX: 500, clientY: 300 })
    await canvas.trigger('mouseup', { button: 2, clientX: 500, clientY: 300 })
    expect(viewport.rotation.value).toBeCloseTo(-90, 1)
    expect(viewport.isPanning.value).toBe(false)

    // Plain Right-drag pans without changing rotation
    const prevPanX = viewport.panX.value
    const prevRotation = viewport.rotation.value
    await canvas.trigger('mousedown', { button: 2, clientX: 300, clientY: 300 })
    expect(viewport.isPanning.value).toBe(true)
    await canvas.trigger('mousemove', { clientX: 360, clientY: 340 })
    await canvas.trigger('mouseup', { button: 2, clientX: 360, clientY: 340 })
    expect(viewport.panX.value).toBeCloseTo(prevPanX + 60, 4)
    expect(viewport.rotation.value).toBe(prevRotation)
  })

  it('rotates via Alt+Wheel without zooming, while plain Wheel zooms without rotating', async () => {
    const { viewport, canvas } = createMountedCanvas()

    canvas.element.dispatchEvent(
      new WheelEvent('wheel', {
        altKey: true,
        deltaY: -100,
        clientX: 500,
        clientY: 500,
        bubbles: true,
        cancelable: true,
      })
    )
    expect(viewport.rotation.value).toBe(5)
    expect(viewport.scale.value).toBe(1)

    canvas.element.dispatchEvent(
      new WheelEvent('wheel', {
        altKey: false,
        deltaY: -100,
        clientX: 500,
        clientY: 500,
        bubbles: true,
        cancelable: true,
      })
    )
    expect(viewport.rotation.value).toBe(5)
    expect(viewport.scale.value).toBeGreaterThan(1)
  })

  it('rotates via Left-drag when rotate tool mode is active without drawing plots', async () => {
    const { viewport, canvas } = createMountedCanvas({
      activeMode: 'draw',
      drawTool: 'rect',
      isRotateToolActive: true,
    })

    await canvas.trigger('mousedown', { button: 0, clientX: 700, clientY: 500 })
    await canvas.trigger('mousemove', { clientX: 500, clientY: 700 })
    await canvas.trigger('mouseup', { button: 0, clientX: 500, clientY: 700 })

    expect(viewport.rotation.value).toBeCloseTo(90, 1)
    expect(canvas.emitted('plot-drawn')).toBeUndefined()
  })

  it('draws screen-aligned rectangles in normalized space when viewport is rotated 90 degrees', async () => {
    const { viewport, canvas } = createMountedCanvas({
      activeMode: 'draw',
      drawTool: 'rect',
    })

    // Rotate 90deg clockwise around center (500, 500)
    viewport.rotateAtScreenPoint(500, 500, 90)

    await canvas.trigger('mousedown', { button: 0, clientX: 300, clientY: 400 })
    await canvas.trigger('mousemove', { clientX: 700, clientY: 600 })
    await canvas.trigger('mouseup', { button: 0, clientX: 700, clientY: 600 })

    const emitted = canvas.emitted('plot-drawn')
    expect(emitted).toHaveLength(1)
    const points = emitted![0][0] as Array<{ x: number; y: number }>
    expect(points).toHaveLength(4)

    // Verify each emitted normalized corner maps back to the exact screen rectangle corners
    const expectedScreen = [
      { x: 300, y: 400 },
      { x: 700, y: 400 },
      { x: 700, y: 600 },
      { x: 300, y: 600 },
    ]
    points.forEach((pt, i) => {
      const sp = viewport.normalizedToScreen(pt)
      expect(sp.x).toBeCloseTo(expectedScreen[i].x, 4)
      expect(sp.y).toBeCloseTo(expectedScreen[i].y, 4)
    })
  })
})
