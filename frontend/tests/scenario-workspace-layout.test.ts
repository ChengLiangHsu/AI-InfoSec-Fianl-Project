import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '@/App.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import ProjectScenarioCard from '@/components/ProjectScenarioCard.vue'
import ScenarioWorkspace from '@/components/ScenarioWorkspace.vue'
import StepNavigationHUD from '@/components/StepNavigationHUD.vue'
import type { ScenarioData } from '@/lib/scenarioSchema'

const configuredScenario: ScenarioData = {
  version: 2,
  type: 'variety',
  title: '水稻品種比較試驗',
  description: '比較不同水稻品種之生長表現',
  metadata_fields: [
    { key: 'crop', label: '試驗作物', type: 'text' },
  ],
  metadata_values: { crop: '水稻' },
  group_fields: [
    { key: 'variety', label: '品種名稱', type: 'text' },
  ],
  categories: [
    { id: 'ck', name: '對照組 (CK)', color: '#94a3b8', is_control: true, values: {}, treatment: '', dose: '' },
    { id: 'g1', name: '台農71號', color: '#10b981', is_control: false, values: { variety: '台農71號' }, treatment: '台農71號', dose: '' },
  ],
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('Step 2 AI scenario workspace layout and HUD visibility', () => {
  it('hides the top-left project status HUD on step 2 while keeping it on steps 1, 3, and 4', async () => {
    const project = {
      id: 'proj-1',
      name: '田間航拍_1110_1557',
      progress: 100,
      images: 49,
      scenario: configuredScenario,
    }
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      const data = url.endsWith('odm-task-formulas')
        ? [{ id: 'VARI' }]
        : url.endsWith('odm-task-list')
          ? [project]
          : url.includes('/plots/')
            ? [{ plot_number: 1, treatment: '台農71號', dose: '', is_control: false, points: [{ x: 0.1, y: 0.1 }, { x: 0.3, y: 0.1 }, { x: 0.3, y: 0.3 }] }]
            : []
      return Promise.resolve(new Response(JSON.stringify({ result: true, data })))
    }))

    const wrapper = mount(App, {
      global: {
        stubs: {
          AppSidebar: true,
          DroneHomeUpload: true,
          ScenarioWorkspace: true,
          PlotToolbar: true,
          PlotStatisticsPanel: true,
          PlotCanvasOverlay: { template: '<div />', methods: { redraw() {}, syncCanvasSize() {} } },
          PlotTreatmentDialog: true,
          CopyPlotsDialog: true,
        },
      },
    })
    await flushPromises()

    wrapper.getComponent(AppSidebar).vm.$emit('update:selectedProject', project)
    await flushPromises()

    // Step 1: HUD visible
    const navigation = wrapper.getComponent(StepNavigationHUD)
    expect(navigation.props('currentStep')).toBe(1)
    expect(wrapper.find('[data-testid="project-status-hud"]').exists()).toBe(true)

    // Step 2: HUD hidden for dedicated AI chat page
    navigation.vm.$emit('changeStep', 2)
    await flushPromises()
    expect(navigation.props('currentStep')).toBe(2)
    expect(wrapper.find('[data-testid="project-status-hud"]').exists()).toBe(false)
    expect(wrapper.findComponent(ScenarioWorkspace).exists()).toBe(true)

    // Step 3: HUD restored
    navigation.vm.$emit('changeStep', 3)
    await flushPromises()
    expect(navigation.props('currentStep')).toBe(3)
    expect(wrapper.find('[data-testid="project-status-hud"]').exists()).toBe(true)

    // Step 4: HUD restored
    navigation.vm.$emit('changeStep', 4)
    await flushPromises()
    expect(navigation.props('currentStep')).toBe(4)
    expect(wrapper.find('[data-testid="project-status-hud"]').exists()).toBe(true)
  })

  it('uses full-width 50/50 split layout in split mode and centered single-column before scenario exists', async () => {
    vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/api/task/scenario/') && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body || '{}'))
        return Promise.resolve(new Response(JSON.stringify({ result: true, data: body.scenario })))
      }
      return Promise.resolve(new Response(JSON.stringify({ data: [] })))
    }))

    const wrapper = mount(ScenarioWorkspace, {
      props: {
        projectId: 'proj-empty',
        projectName: '測試專案',
        initialScenario: null,
      },
      global: {
        stubs: {
          ProjectScenarioCard: true,
          Conversation: { template: '<div><slot /></div>' },
          ConversationContent: { template: '<div><slot /></div>' },
          ConversationScrollButton: true,
          Message: { template: '<div><slot /></div>' },
          MessageBranch: { template: '<div><slot /></div>' },
          MessageBranchContent: { template: '<div><slot /></div>' },
          MessageContent: { template: '<div><slot /></div>' },
          MessageResponse: true,
          PromptInputProvider: { template: '<div><slot /></div>' },
          PromptInput: { template: '<div><slot /></div>' },
          PromptInputBody: { template: '<div><slot /></div>' },
          PromptInputFooter: { template: '<div><slot /></div>' },
          PromptInputSubmit: true,
          PromptInputTextarea: true,
        },
      },
    })
    await flushPromises()

    // Non-split mode: centered single-column chat, no form panel
    const layout = wrapper.get('[data-testid="scenario-workspace-layout"]')
    expect(layout.classes()).toContain('max-w-3xl')
    expect(wrapper.find('[data-testid="scenario-form-panel"]').exists()).toBe(false)

    // Trigger manual start to enter split mode
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(layout.classes()).toContain('max-w-none')
    expect(layout.classes()).not.toContain('max-w-7xl')

    const chatPanel = wrapper.get('[data-testid="scenario-chat-panel"]')
    const formPanel = wrapper.get('[data-testid="scenario-form-panel"]')

    expect(chatPanel.classes()).toContain('flex-1')
    expect(chatPanel.classes()).toContain('basis-0')
    expect(chatPanel.classes()).toContain('min-w-0')
    expect(chatPanel.classes()).toContain('min-h-0')
    expect(chatPanel.classes()).toContain('lg:h-full')
    expect(chatPanel.classes()).not.toContain('h-[42vh]')
    expect(chatPanel.classes()).not.toContain('lg:w-[40%]')
    expect(chatPanel.classes()).not.toContain('lg:max-w-[460px]')

    expect(formPanel.classes()).toContain('flex-1')
    expect(formPanel.classes()).toContain('basis-0')
    expect(formPanel.classes()).toContain('min-w-0')
    expect(formPanel.classes()).toContain('min-h-0')
    expect(formPanel.classes()).toContain('lg:h-full')
  })

  it('opens immediately in full-width 50/50 split mode when initialScenario is already configured', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response(JSON.stringify({ data: [] })))))

    const wrapper = mount(ScenarioWorkspace, {
      props: {
        projectId: 'proj-configured',
        projectName: '水稻專案',
        initialScenario: configuredScenario,
      },
      global: {
        stubs: {
          ProjectScenarioCard: true,
          Conversation: { template: '<div><slot /></div>' },
          ConversationContent: { template: '<div><slot /></div>' },
          ConversationScrollButton: true,
          Message: { template: '<div><slot /></div>' },
          MessageBranch: { template: '<div><slot /></div>' },
          MessageBranchContent: { template: '<div><slot /></div>' },
          MessageContent: { template: '<div><slot /></div>' },
          MessageResponse: true,
          PromptInputProvider: { template: '<div><slot /></div>' },
          PromptInput: { template: '<div><slot /></div>' },
          PromptInputBody: { template: '<div><slot /></div>' },
          PromptInputFooter: { template: '<div><slot /></div>' },
          PromptInputSubmit: true,
          PromptInputTextarea: true,
        },
      },
    })
    await flushPromises()

    const layout = wrapper.get('[data-testid="scenario-workspace-layout"]')
    expect(layout.classes()).toContain('max-w-none')
    expect(wrapper.find('[data-testid="scenario-chat-panel"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="scenario-form-panel"]').exists()).toBe(true)
  })

  it('prevents the color column header in ProjectScenarioCard from wrapping in narrow 50/50 split panes', async () => {
    const wrapper = mount(ProjectScenarioCard, {
      props: {
        projectId: 'proj-configured',
        projectName: '水稻專案',
        initialScenario: configuredScenario,
      },
    })
    await flushPromises()

    const headers = wrapper.findAll('thead th')
    const colorHeader = headers.find((th) => th.text().trim() === '色彩')
    expect(colorHeader).toBeDefined()
    expect(colorHeader!.classes()).toContain('whitespace-nowrap')
  })
})
