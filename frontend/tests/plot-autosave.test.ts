import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '@/App.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import PlotCanvasOverlay from '@/components/PlotCanvasOverlay.vue'
import StepNavigationHUD from '@/components/StepNavigationHUD.vue'
import { createManualDefaultScenario } from '@/lib/scenarioSchema'
import { usePlots } from '@/lib/usePlots'

const TRIANGLE = [
  { x: 0.1, y: 0.1 },
  { x: 0.3, y: 0.1 },
  { x: 0.3, y: 0.3 },
]

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('plot annotation auto-save', () => {
  it('debounces rapid plot edits into a single PUT request', async () => {
    vi.useFakeTimers()
    const putPayloads: any[] = []
    vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === 'PUT' && url === '/api/task/plots/task-1') {
        const parsed = JSON.parse(String(init.body))
        putPayloads.push(parsed)
        return Promise.resolve(new Response(JSON.stringify({ result: true, data: parsed.plots })))
      }
      return Promise.resolve(new Response(JSON.stringify({ result: true, data: [] })))
    }))

    const store = usePlots({ autoSaveDelayMs: 500 })
    await store.loadPlots('task-1')
    expect(store.saveState.value).toBe('saved')

    store.addPlotWithTreatment(TRIANGLE, '', '', true)
    store.updatePlotTreatment(1, '藥劑A', '1000x', false)
    store.movePlot(1, { dx: 0.05, dy: 0.05 })
    expect(store.isDirty.value).toBe(true)
    expect(store.saveState.value).toBe('pending')
    expect(putPayloads).toHaveLength(0)

    await vi.advanceTimersByTimeAsync(499)
    expect(putPayloads).toHaveLength(0)

    await vi.advanceTimersByTimeAsync(1)
    await flushPromises()
    expect(putPayloads).toHaveLength(1)
    expect(putPayloads[0].plots).toHaveLength(1)
    expect(putPayloads[0].plots[0].treatment).toBe('藥劑A')
    expect(putPayloads[0].plots[0].dose).toBe('1000x')
    expect(store.isDirty.value).toBe(false)
    expect(store.saveState.value).toBe('saved')
  })

  it('preserves edits made during an in-flight save and follows up with a second save', async () => {
    vi.useFakeTimers()
    const putPayloads: any[] = []
    let resolveFirstPut!: (res: Response) => void

    vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === 'PUT' && url === '/api/task/plots/task-2') {
        const parsed = JSON.parse(String(init.body))
        putPayloads.push(parsed)
        if (putPayloads.length === 1) {
          return new Promise<Response>((resolve) => {
            resolveFirstPut = resolve
          })
        }
        return Promise.resolve(new Response(JSON.stringify({ result: true, data: parsed.plots })))
      }
      return Promise.resolve(new Response(JSON.stringify({ result: true, data: [] })))
    }))

    const store = usePlots({ autoSaveDelayMs: 300 })
    await store.loadPlots('task-2')

    store.addPlotWithTreatment(TRIANGLE, '', '', true)
    await vi.advanceTimersByTimeAsync(300)
    expect(store.isSaving.value).toBe(true)
    expect(putPayloads).toHaveLength(1)

    // User draws a second plot while the first PUT is still in-flight
    store.addPlotWithTreatment(TRIANGLE, '藥劑B', '500x', false)
    expect(store.plots.value).toHaveLength(2)

    // First PUT resolves with only plot #1
    resolveFirstPut(new Response(JSON.stringify({ result: true, data: putPayloads[0].plots })))
    await flushPromises()

    // Plot #2 must still exist and must have been saved in the follow-up PUT
    expect(store.plots.value).toHaveLength(2)
    expect(putPayloads).toHaveLength(2)
    expect(putPayloads[1].plots).toHaveLength(2)
    expect(store.isDirty.value).toBe(false)
    expect(store.saveState.value).toBe('saved')
  })

  it('flushes pending plot changes automatically when leaving Step 3 without confirm dialog', async () => {
    const project = {
      id: 'field-auto',
      name: '自動儲存測試田區',
      progress: 100,
      images: 8,
      scenario: createManualDefaultScenario(),
    }
    const putCalls: string[] = []
    vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === 'PUT' && url === `/api/task/plots/${project.id}`) {
        putCalls.push(String(init.body))
        const parsed = JSON.parse(String(init.body))
        return Promise.resolve(new Response(JSON.stringify({ result: true, data: parsed.plots })))
      }
      const data = url.endsWith('odm-task-formulas') ? [{ id: 'VARI' }]
        : url.endsWith('odm-task-list') ? [project]
        : url.includes('/plots/') ? [] : {}
      return Promise.resolve(new Response(JSON.stringify({ result: true, data })))
    }))
    const confirmSpy = vi.spyOn(window, 'confirm')

    const wrapper = mount(App, {
      global: {
        stubs: {
          AppSidebar: true,
          DroneHomeUpload: true,
          ProjectScenarioCard: true,
          PlotToolbar: true,
          PlotCanvasOverlay: { template: '<div />', methods: { redraw() {}, syncCanvasSize() {} } },
          PlotTreatmentDialog: true,
          CopyPlotsDialog: true,
        },
      },
    })
    await flushPromises()
    wrapper.getComponent(AppSidebar).vm.$emit('update:selectedProject', project)
    await flushPromises()

    const nav = wrapper.getComponent(StepNavigationHUD)
    nav.vm.$emit('changeStep', 3)
    await flushPromises()
    expect(wrapper.get('[data-testid="plots-autosave-status"]').text()).toContain('已自動儲存')

    wrapper.getComponent(PlotCanvasOverlay).vm.$emit('plotDrawn', TRIANGLE)
    await flushPromises()
    expect(wrapper.get('[data-testid="plots-autosave-status"]').text()).toContain('待自動儲存')

    // Immediately switch to Step 4 before the debounce timer fires
    nav.vm.$emit('changeStep', 4)
    await flushPromises()

    expect(putCalls).toHaveLength(1)
    expect(confirmSpy).not.toHaveBeenCalled()
    expect(nav.props('currentStep')).toBe(4)
    wrapper.unmount()
  })

  it('shows retry state on failure and flushes old project plots before switching projects', async () => {
    vi.useFakeTimers()
    const projectA = {
      id: 'proj-a',
      name: '田區 A',
      progress: 100,
      images: 5,
      scenario: createManualDefaultScenario(),
    }
    const projectB = {
      id: 'proj-b',
      name: '田區 B',
      progress: 100,
      images: 6,
      scenario: createManualDefaultScenario(),
    }
    let shouldFailPut = true
    const savedByProject: Record<string, any[]> = {}

    vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === 'PUT' && url.startsWith('/api/task/plots/')) {
        if (shouldFailPut) {
          return Promise.resolve(new Response(JSON.stringify({ result: false, message: '暫時無法連線' }), { status: 500 }))
        }
        const taskId = url.split('/').pop()!
        const parsed = JSON.parse(String(init.body))
        savedByProject[taskId] = parsed.plots
        return Promise.resolve(new Response(JSON.stringify({ result: true, data: parsed.plots })))
      }
      const data = url.endsWith('odm-task-formulas') ? [{ id: 'VARI' }]
        : url.endsWith('odm-task-list') ? [projectA, projectB]
        : url.includes('/plots/') ? [] : {}
      return Promise.resolve(new Response(JSON.stringify({ result: true, data })))
    }))

    const wrapper = mount(App, {
      global: {
        stubs: {
          AppSidebar: true,
          DroneHomeUpload: true,
          ProjectScenarioCard: true,
          PlotToolbar: true,
          PlotCanvasOverlay: { template: '<div />', methods: { redraw() {}, syncCanvasSize() {} } },
          PlotTreatmentDialog: true,
          CopyPlotsDialog: true,
        },
      },
    })
    await flushPromises()
    wrapper.getComponent(AppSidebar).vm.$emit('update:selectedProject', projectA)
    await flushPromises()
    wrapper.getComponent(StepNavigationHUD).vm.$emit('changeStep', 3)
    await flushPromises()

    wrapper.getComponent(PlotCanvasOverlay).vm.$emit('plotDrawn', TRIANGLE)
    await vi.advanceTimersByTimeAsync(600)
    await flushPromises()

    // Failure shows retry button in HUD
    const statusEl = wrapper.get('[data-testid="plots-autosave-status"]')
    expect(statusEl.text()).toContain('儲存失敗')

    // Now network recovers; switching directly to project B flushes project A first
    shouldFailPut = false
    wrapper.getComponent(AppSidebar).vm.$emit('update:selectedProject', projectB)
    await flushPromises()

    expect(savedByProject['proj-a']).toHaveLength(1)
    wrapper.unmount()
  })
})
