import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import PlotStatisticsPanel from '@/components/PlotStatisticsPanel.vue'

const plot = { plot_number: 31, coords: '[[0,0],[1,0],[1,1],[0,1]]', is_control: true, treatment: '', dose: '' }
const data = {
  pixel_count: 20, rgb_mean: [20, 100, 40],
  algorithms: [{ id: 'VARI', index_mean: 1, valid_pixel_count: 20, rgb_mean: [1, 255, 0] }],
}
const response = (payload = data) => new Response(JSON.stringify({ result: true, data: payload }))

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

it('shows original and algorithm RGB, and lets the user switch the displayed layer', async () => {
  vi.useFakeTimers()
  const fetcher = vi.fn().mockResolvedValue(response())
  vi.stubGlobal('fetch', fetcher)
  const wrapper = mount(PlotStatisticsPanel, { props: { taskId: 'field', plots: [plot], currentFormula: 'rgb' } })
  expect(wrapper.text()).toContain('正在計算')
  await vi.advanceTimersByTimeAsync(300)
  await flushPromises()
  expect(wrapper.text()).toContain('#31 (CK)')
  expect(wrapper.text()).toContain('20.00 / 100.00 / 40.00')
  expect(wrapper.text()).toContain('1.00 / 255.00 / 0.00')
  expect(wrapper.text()).toContain('1.0000')
  expect(JSON.parse(fetcher.mock.calls[0][1].body).points).toEqual(JSON.parse(plot.coords))
  await wrapper.findAll('button').find(button => button.text() === 'VARI')!.trigger('click')
  expect(wrapper.emitted('select-formula')).toEqual([['VARI']])
  wrapper.unmount()
})

it('debounces geometry changes and ignores stale results after switching projects', async () => {
  vi.useFakeTimers()
  let finishOld!: (value: Response) => void
  const fetcher = vi.fn().mockImplementationOnce(() => new Promise(resolve => { finishOld = resolve }))
    .mockResolvedValueOnce(response({ ...data, rgb_mean: [90, 80, 70] }))
  vi.stubGlobal('fetch', fetcher)
  const wrapper = mount(PlotStatisticsPanel, { props: { taskId: 'old', plots: [plot], currentFormula: 'rgb' } })
  await vi.advanceTimersByTimeAsync(300)
  await wrapper.setProps({ taskId: 'new', plots: [{ ...plot, coords: '[[0,0],[0.5,0],[0,1]]' }] })
  await wrapper.setProps({ plots: [{ ...plot, coords: '[[0,0],[0.8,0],[0,1]]' }] })
  expect(fetcher.mock.calls[0][1].signal.aborted).toBe(true)
  await vi.advanceTimersByTimeAsync(300)
  await flushPromises()
  finishOld(response())
  await flushPromises()
  expect(wrapper.text()).toContain('90.00 / 80.00 / 70.00')
  expect(fetcher).toHaveBeenCalledTimes(2)
  await wrapper.setProps({ plots: [] })
  expect(wrapper.text()).toContain('點選已框選的小區')
  expect(wrapper.text()).not.toContain('90.00')
  wrapper.unmount()
})

it('supports retry and multiple selected plots without showing fabricated empty values', async () => {
  vi.useFakeTimers()
  const fetcher = vi.fn().mockRejectedValueOnce(new Error('連線失敗'))
    .mockResolvedValueOnce(response())
    .mockResolvedValueOnce(response({ pixel_count: 0, rgb_mean: null as any, algorithms: [] }))
  vi.stubGlobal('fetch', fetcher)
  const wrapper = mount(PlotStatisticsPanel, { props: { taskId: 'field', plots: [plot, { ...plot, plot_number: 32, coords: '[[0,0],[0.5,0],[0,1]]' }], currentFormula: 'rgb' } })
  await vi.advanceTimersByTimeAsync(300)
  await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('連線失敗')
  await wrapper.findAll('button').find(button => button.text() === '重新計算')!.trigger('click')
  await vi.advanceTimersByTimeAsync(300)
  await flushPromises()
  await wrapper.get('select').setValue('32')
  expect(wrapper.text()).not.toContain('20.00 / 100.00')
  await vi.advanceTimersByTimeAsync(300)
  await flushPromises()
  expect(wrapper.text()).toContain('區域內沒有有效影像像素')
  wrapper.unmount()
})
