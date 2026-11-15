import { flushPromises, mount } from '@vue/test-utils'
import { expect, it, vi } from 'vitest'
import App from '@/App.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import StepNavigationHUD from '@/components/StepNavigationHUD.vue'
import PlotCanvasOverlay from '@/components/PlotCanvasOverlay.vue'
import PlotStatisticsPanel from '@/components/PlotStatisticsPanel.vue'

it('connects plot selection, edited geometry, multi-selection, and spectral switching in App', async () => {
  const project = { id: 'field-1', name: '測試田區', progress: 100, images: 10 }
  const plots = [31, 32].map(plot_number => ({ plot_number, coords: '[[0,0],[1,0],[0,1]]', is_control: true, treatment: '', dose: '' }))
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    const data = url.endsWith('odm-task-formulas') ? [{ id: 'VARI' }]
      : url.endsWith('odm-task-list') ? [project]
      : url.includes('/plots/') ? plots : {}
    return Promise.resolve(new Response(JSON.stringify({ result: true, data })))
  }))
  const wrapper = mount(App, { global: { stubs: {
    AppSidebar: true, DroneHomeUpload: true, ProjectScenarioCard: true, PlotToolbar: true,
    PlotCanvasOverlay: { template: '<div />', methods: { redraw() {}, syncCanvasSize() {} } },
    PlotTreatmentDialog: true, CopyPlotsDialog: true,
  } } })
  await flushPromises()
  wrapper.getComponent(AppSidebar).vm.$emit('update:selectedProject', project)
  await flushPromises()
  wrapper.getComponent(StepNavigationHUD).vm.$emit('changeStep', 3)
  await flushPromises()
  const overlay = wrapper.getComponent(PlotCanvasOverlay)
  overlay.vm.$emit('select-plots', [31])
  overlay.vm.$emit('select-plot', 31)
  await flushPromises()
  expect(wrapper.getComponent(PlotStatisticsPanel).props('plots')[0].plot_number).toBe(31)
  overlay.vm.$emit('update-plot-points', { plotNumber: 31, points: [{ x: 0, y: 0 }, { x: .5, y: 0 }, { x: 0, y: 1 }] })
  await flushPromises()
  expect(wrapper.getComponent(PlotStatisticsPanel).props('plots')[0].coords).toBe('[[0,0],[0.5,0],[0,1]]')
  overlay.vm.$emit('select-plots', [31, 32])
  overlay.vm.$emit('select-plot', null)
  await flushPromises()
  expect(wrapper.getComponent(PlotStatisticsPanel).props('plots')).toHaveLength(2)
  wrapper.getComponent(PlotStatisticsPanel).vm.$emit('select-formula', 'VARI')
  await flushPromises()
  expect(wrapper.get('img').attributes('src')).toContain('formula=VARI')
  expect(wrapper.getComponent(StepNavigationHUD).props('currentStep')).toBe(3)
  wrapper.unmount()
})
