import { flushPromises, mount } from '@vue/test-utils'
import { expect, it, vi } from 'vitest'
import App from '@/App.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import ImageDownloadPanel from '@/components/ImageDownloadPanel.vue'
import StepNavigationHUD from '@/components/StepNavigationHUD.vue'
import PlotToolbar from '@/components/PlotToolbar.vue'
import PlotCanvasOverlay from '@/components/PlotCanvasOverlay.vue'

it('preserves the actual App step, image, and unsaved plots during a download', async () => {
  const project = { id: 'field-1', name: '測試田區', progress: 100, images: 10 }
  let resolveDownload!: (response: Response) => void
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.includes('/odm-task-export/')) return new Promise<Response>(resolve => { resolveDownload = resolve })
    const data = url.endsWith('odm-task-formulas') ? [{ id: 'VARI' }]
      : url.endsWith('odm-task-list') ? [project]
      : url.includes('/plots/') ? [] : {}
    return Promise.resolve(new Response(JSON.stringify({ data })))
  }))
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  URL.createObjectURL = vi.fn().mockReturnValue('blob:test')
  const wrapper = mount(App, {
    attachTo: document.body,
    global: { stubs: {
      AppSidebar: true, DroneHomeUpload: true, ProjectScenarioCard: true,
      PlotToolbar: true, PlotCanvasOverlay: { template: '<div />', methods: { redraw() {}, syncCanvasSize() {} } },
      PlotTreatmentDialog: true, CopyPlotsDialog: true,
    } },
  })
  await flushPromises()
  expect(wrapper.findComponent(ImageDownloadPanel).exists()).toBe(false)
  wrapper.getComponent(AppSidebar).vm.$emit('update:selectedProject', project)
  await flushPromises()
  const navigation = wrapper.getComponent(StepNavigationHUD)
  navigation.vm.$emit('changeStep', 3)
  await flushPromises()
  wrapper.getComponent(PlotCanvasOverlay).vm.$emit('plotDrawn', [
    { x: .1, y: .1 }, { x: .3, y: .1 }, { x: .3, y: .3 },
  ])
  await flushPromises()
  const plotsBefore = JSON.stringify(wrapper.getComponent(PlotToolbar).props('plots'))
  expect(wrapper.getComponent(PlotToolbar).props('isDirty')).toBe(true)
  const imageBefore = wrapper.get('img').attributes('src')
  await wrapper.get('button[aria-label="下載影像"]').trigger('click')
  await flushPromises()
  const select = document.querySelector<HTMLSelectElement>('#export-layer')!
  select.value = 'VARI'
  select.dispatchEvent(new Event('change', { bubbles: true }))
  await flushPromises()
  document.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  await flushPromises()
  expect(navigation.props('currentStep')).toBe(3)
  expect(wrapper.get('img').attributes('src')).toBe(imageBefore)
  expect(confirm).not.toHaveBeenCalled()
  expect(wrapper.getComponent(PlotToolbar).props('isDirty')).toBe(true)
  expect(JSON.stringify(wrapper.getComponent(PlotToolbar).props('plots'))).toBe(plotsBefore)
  document.querySelector<HTMLButtonElement>('button[aria-label="關閉下載面板"]')!.click()
  await flushPromises()
  // The existing unsaved-work guard remains active even while a download is running.
  navigation.vm.$emit('changeStep', 2)
  await flushPromises()
  expect(confirm).toHaveBeenCalledOnce()
  expect(navigation.props('currentStep')).toBe(3)
  confirm.mockReturnValue(true)
  navigation.vm.$emit('changeStep', 2)
  await flushPromises()
  expect(navigation.props('currentStep')).toBe(2)
  navigation.vm.$emit('changeStep', 3)
  await flushPromises()
  resolveDownload(new Response('image bytes'))
  await flushPromises()
  expect(wrapper.getComponent(PlotToolbar).props('isDirty')).toBe(true)
  expect(JSON.stringify(wrapper.getComponent(PlotToolbar).props('plots'))).toBe(plotsBefore)
})
