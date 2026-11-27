import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PlotCanvasOverlay from '@/components/PlotCanvasOverlay.vue'
import PlotToolbar from '@/components/PlotToolbar.vue'
import { useCanvasViewport, normalizeRotationDeg, clampPanBounds } from '@/lib/useCanvasViewport'
import { usePlots, type PlotCanvasMode, type PlotItem } from '@/lib/usePlots'

beforeEach(() => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null)
})

function createMountedCanvas(options?: {
  activeMode?: PlotCanvasMode
  drawTool?: 'rect' | 'polygon' | 'eraser'
  isRotateToolActive?: boolean
  gridActive?: boolean
  initialPlots?: PlotItem[]
}) {
  const plots = usePlots()
  if (options?.initialPlots) {
    plots.plots.value = options.initialPlots
  }
  if (options?.gridActive) {
    plots.startGridMode()
  }
  const viewport = useCanvasViewport()
  viewport.fitToViewport(1000, 1000, 1000, 1000, 0)

  const canvas = mount(PlotCanvasOverlay, {
    props: {
      plots: plots.plots.value,
      activeMode: options?.activeMode ?? 'pan',
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

  it('pans via Left-drag in default pan mode and rotates via Right-drag without selecting plots', async () => {
    const samplePlots: PlotItem[] = [
      {
        plot_number: 1,
        coords: JSON.stringify([
          [0.2, 0.2],
          [0.4, 0.2],
          [0.4, 0.4],
          [0.2, 0.4],
        ]),
        is_control: false,
        treatment: 'A',
        dose: '1x',
      },
    ]
    const { viewport, canvas } = createMountedCanvas({
      activeMode: 'pan',
      initialPlots: samplePlots,
    })

    // Left-drag pans without rotating or selecting plots
    const prevPanX = viewport.panX.value
    const prevPanY = viewport.panY.value
    await canvas.trigger('mousedown', { button: 0, clientX: 300, clientY: 300 })
    expect(viewport.isPanning.value).toBe(true)
    await canvas.trigger('mousemove', { clientX: 360, clientY: 340 })
    await canvas.trigger('mouseup', { button: 0, clientX: 360, clientY: 340 })
    expect(viewport.isPanning.value).toBe(false)
    expect(viewport.panX.value).toBeCloseTo(prevPanX + 60, 4)
    expect(viewport.panY.value).toBeCloseTo(prevPanY + 40, 4)
    expect(viewport.rotation.value).toBe(0)
    expect(canvas.emitted('select-plots')).toBeUndefined()
    expect(canvas.emitted('select-plot')).toBeUndefined()

    // Plain Right-drag rotates without panning (center shifted to 560, 540 after pan)
    await canvas.trigger('mousedown', { button: 2, clientX: 760, clientY: 540 })
    expect(viewport.isRotating.value).toBe(true)
    expect(viewport.isPanning.value).toBe(false)
    await canvas.trigger('mousemove', { clientX: 560, clientY: 340 })
    await canvas.trigger('mouseup', { button: 2, clientX: 560, clientY: 340 })
    expect(viewport.isRotating.value).toBe(false)
    expect(viewport.rotation.value).toBeCloseTo(-90, 1)
  })

  it('allows rubber-band plot selection only in select mode while keeping Right-drag as rotate', async () => {
    const samplePlots: PlotItem[] = [
      {
        plot_number: 7,
        coords: JSON.stringify([
          [0.2, 0.2],
          [0.4, 0.2],
          [0.4, 0.4],
          [0.2, 0.4],
        ]),
        is_control: false,
        treatment: 'A',
        dose: '1x',
      },
    ]
    const { viewport, canvas } = createMountedCanvas({
      activeMode: 'select',
      initialPlots: samplePlots,
    })

    // Left-drag rubber-band selects plot #7 (centroid at 300, 300)
    await canvas.trigger('mousedown', { button: 0, clientX: 150, clientY: 150 })
    expect(viewport.isPanning.value).toBe(false)
    await canvas.trigger('mousemove', { clientX: 450, clientY: 450 })
    await canvas.trigger('mouseup', { button: 0, clientX: 450, clientY: 450 })
    expect(canvas.emitted('select-plots')?.[0]).toEqual([[7]])

    // Right-drag still rotates in select mode
    await canvas.trigger('mousedown', { button: 2, clientX: 700, clientY: 500 })
    await canvas.trigger('mousemove', { clientX: 500, clientY: 700 })
    await canvas.trigger('mouseup', { button: 2, clientX: 500, clientY: 700 })
    expect(viewport.rotation.value).toBeCloseTo(90, 1)
  })

  it('defaults usePlots activeMode to pan and toggles select mode via PlotToolbar', async () => {
    const plots = usePlots()
    expect(plots.activeMode.value).toBe('pan')

    const toolbar = mount(PlotToolbar, {
      props: {
        plots: [],
        activeMode: plots.activeMode.value,
        drawTool: 'rect',
        selectedPlotNumber: null,
        isDirty: false,
        isSaving: false,
        isDrawing: false,
        gridState: plots.gridState.value,
      },
    })

    await toolbar.get('[data-testid="mode-select-button"]').trigger('click')
    expect(toolbar.emitted('update:activeMode')?.[0]).toEqual(['select'])

    await toolbar.setProps({ activeMode: 'select' })
    await toolbar.get('[data-testid="mode-select-button"]').trigger('click')
    expect(toolbar.emitted('update:activeMode')?.[1]).toEqual(['pan'])
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
