import { mount } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import PlotCanvasOverlay from '@/components/PlotCanvasOverlay.vue'
import PlotToolbar from '@/components/PlotToolbar.vue'
import { usePlots } from '@/lib/usePlots'
import { useCanvasViewport } from '@/lib/useCanvasViewport'

beforeEach(() => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null)
})

function setupGrid() {
  const plots = usePlots()
  const viewport = useCanvasViewport()
  viewport.setBaseDimensions(1000, 1000)
  plots.startGridMode()
  const canvas = mount(PlotCanvasOverlay, {
    props: {
      plots: [], activeMode: 'view', drawTool: 'rect',
      gridState: plots.gridState.value, viewport,
      getPlotColor: () => '#ffffff',
      'onUpdate-grid-corners': plots.updateGridCorners,
      'onUpdate-grid-corner': ({ index, point }) => plots.updateGridCorner(index, point),
    },
  })
  return { plots, viewport, canvas }
}

async function drag(canvas: ReturnType<typeof setupGrid>['canvas'], from: number[], to: number[]) {
  await canvas.trigger('mousedown', { button: 0, clientX: from[0], clientY: from[1] })
  await canvas.trigger('mousemove', { clientX: to[0], clientY: to[1] })
  await canvas.trigger('mouseup', { button: 0, clientX: to[0], clientY: to[1] })
}

it('starts fresh on every entry, keeps dimensions, and cannot generate before selection', () => {
  const plots = usePlots()
  plots.gridState.value.rows = 9
  plots.gridState.value.cols = 1
  plots.startGridMode()
  plots.updateGridCorners([{ x: .1, y: .1 }, { x: .4, y: .1 }, { x: .4, y: .8 }, { x: .1, y: .8 }])
  plots.toggleExcludeGridCell(1)
  plots.closeGridMode()
  plots.startGridMode()
  expect(plots.gridState.value.corners).toEqual([])
  expect(plots.gridState.value.excludedIndices).toEqual([])
  expect(plots.gridState.value.rows).toBe(9)
  expect(plots.gridState.value.cols).toBe(1)
  plots.confirmBatchGenerate()
  expect(plots.plots.value).toEqual([])
  expect(plots.isDirty.value).toBe(false)
  expect(plots.gridState.value.isActive).toBe(true)
})

it('frames a new region in either direction after zoom and pan, then allows corner adjustment', async () => {
  const { plots, viewport, canvas } = setupGrid()
  viewport.scale.value = 2
  viewport.panX.value = -100
  viewport.panY.value = -200
  await drag(canvas, [700, 600], [100, 200])
  expect(plots.gridState.value.corners).toEqual([
    { x: .1, y: .2 }, { x: .4, y: .2 }, { x: .4, y: .4 }, { x: .1, y: .4 },
  ])
  expect(canvas.emitted('plot-drawn')).toBeUndefined()
  expect(plots.plots.value).toHaveLength(0)
  await drag(canvas, [100, 200], [120, 220])
  expect(plots.gridState.value.corners[0]).toEqual({ x: .11, y: .21 })
  plots.confirmBatchGenerate()
  expect(plots.plots.value).toHaveLength(30)
})

it('ignores clicks and flat rectangles, and Escape cancels an unfinished selection', async () => {
  const { plots, canvas } = setupGrid()
  await drag(canvas, [100, 100], [100, 100])
  await drag(canvas, [100, 100], [400, 100])
  expect(plots.gridState.value.corners).toEqual([])
  await canvas.trigger('mousedown', { button: 0, clientX: 100, clientY: 100 })
  await canvas.trigger('mousemove', { clientX: 400, clientY: 400 })
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
  await canvas.trigger('mouseup', { button: 0, clientX: 400, clientY: 400 })
  expect(plots.gridState.value.corners).toEqual([])
  await drag(canvas, [100, 100], [400, 400])
  expect(plots.gridState.value.corners).toHaveLength(4)
})

it('cancels a partial frame on exit and prioritizes framing over a previous eraser tool', async () => {
  const { plots, canvas } = setupGrid()
  await canvas.setProps({ drawTool: 'eraser' })
  await canvas.trigger('mousedown', { button: 0, clientX: 100, clientY: 100 })
  plots.closeGridMode()
  await nextTick()
  await canvas.trigger('mouseup', { button: 0, clientX: 400, clientY: 400 })
  expect(canvas.emitted('plot-drawn')).toBeUndefined()
  plots.startGridMode()
  await nextTick()
  await drag(canvas, [100, 100], [400, 400])
  expect(plots.gridState.value.corners).toHaveLength(4)
  expect(canvas.emitted('delete-plot')).toBeUndefined()
})

it('shows configuration only after framing and offers a fresh selection', async () => {
  const plots = usePlots()
  plots.startGridMode()
  const toolbar = mount(PlotToolbar, { props: {
    plots: [], activeMode: 'view', drawTool: 'rect', selectedPlotNumber: null,
    isDirty: false, isSaving: false, isDrawing: false, gridState: plots.gridState.value,
    onStartGrid: plots.startGridMode,
  } })
  expect(toolbar.text()).toContain('拖曳框選網格範圍')
  expect(toolbar.text()).not.toContain('確認生成')
  plots.updateGridCorners([{ x: .1, y: .1 }, { x: .4, y: .1 }, { x: .4, y: .8 }, { x: .1, y: .8 }])
  await nextTick()
  expect(toolbar.text()).toContain('確認生成')
  await toolbar.findAll('button').find(button => button.text() === '重新框選')!.trigger('click')
  expect(plots.gridState.value.corners).toEqual([])
  expect(toolbar.text()).toContain('拖曳框選網格範圍')
})
