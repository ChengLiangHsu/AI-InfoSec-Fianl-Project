import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '@/App.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import ScenarioWorkspace from '@/components/ScenarioWorkspace.vue'
import StepNavigationHUD from '@/components/StepNavigationHUD.vue'
import { createManualDefaultScenario } from '@/lib/scenarioSchema'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('步驟 2 表單建置完成前鎖定步驟 3 導覽', () => {
  it('StepNavigationHUD 在表單未建置完成時停用下一步按鈕，建置完成後解鎖', async () => {
    const wrapper = mount(StepNavigationHUD, {
      props: {
        currentStep: 2,
        projectProgress: 100,
        hasScenario: false,
        hasPlots: false,
      },
    })

    const buttons = wrapper.findAll('button')
    const nextButton = buttons[buttons.length - 1]
    expect(nextButton.text()).toContain('下一步：小區標註')
    expect(nextButton.attributes('disabled')).toBeDefined()

    await nextButton.trigger('click')
    expect(wrapper.emitted('changeStep')).toBeUndefined()

    await wrapper.setProps({ hasScenario: true })
    const unlockedButtons = wrapper.findAll('button')
    const unlockedNextButton = unlockedButtons[unlockedButtons.length - 1]
    expect(unlockedNextButton.attributes('disabled')).toBeUndefined()

    await unlockedNextButton.trigger('click')
    expect(wrapper.emitted('changeStep')).toEqual([[3]])
    wrapper.unmount()
  })

  it('App 在步驟 2 表單未建置完成時阻擋跳轉至步驟 3，建置後即可正常進入', async () => {
    const project = { id: 'field-guard', name: '防呆測試田區', progress: 100, images: 10 }
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        const data = url.endsWith('odm-task-formulas')
          ? [{ id: 'VARI' }]
          : url.endsWith('odm-task-list')
            ? [project]
            : url.includes('/plots/')
              ? []
              : {}
        return Promise.resolve(new Response(JSON.stringify({ result: true, data })))
      })
    )
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})

    const wrapper = mount(App, {
      global: {
        stubs: {
          AppSidebar: true,
          DroneHomeUpload: true,
          ScenarioWorkspace: true,
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

    const navigation = wrapper.getComponent(StepNavigationHUD)
    expect(navigation.props('hasScenario')).toBe(false)

    // 先進入步驟 2
    navigation.vm.$emit('changeStep', 2)
    await flushPromises()
    expect(navigation.props('currentStep')).toBe(2)

    // 步驟 2 表單尚未建置完成，嘗試跳轉至步驟 3 應被阻擋並顯示提示
    navigation.vm.$emit('changeStep', 3)
    await flushPromises()
    expect(navigation.props('currentStep')).toBe(2)
    expect(alertSpy).toHaveBeenCalledWith('需先於步驟 2 完成試驗情境表單建置方可進入該步驟')

    // 模擬步驟 2 表單建置完成
    wrapper.getComponent(ScenarioWorkspace).vm.$emit('update:scenario', createManualDefaultScenario())
    await flushPromises()
    expect(navigation.props('hasScenario')).toBe(true)

    // 表單建置完成後即可順利進入步驟 3
    navigation.vm.$emit('changeStep', 3)
    await flushPromises()
    expect(navigation.props('currentStep')).toBe(3)
    wrapper.unmount()
  })
})
