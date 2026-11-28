import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import SpectralWorkspace from '../src/components/SpectralWorkspace.vue'
import { normalizeScenario } from '../src/lib/scenarioSchema'
import type { PlotItem } from '../src/lib/usePlots'

vi.mock('../src/components/PlotCanvasOverlay.vue', () => ({
  default: defineComponent({
    name: 'PlotCanvasOverlay',
    props: ['plots', 'activeMode', 'clickSelectOnPan', 'selectedPlotNumbers'],
    emits: ['select-plot', 'select-plots'],
    setup(props, { expose }) {
      expose({
        syncCanvasSize: vi.fn(),
        redraw: vi.fn(),
        undoLastPoint: vi.fn(),
        cancelDrawing: vi.fn(),
        isDrawing: () => false,
      })
      return () =>
        h('div', {
          'data-testid': 'mock-plot-canvas-overlay',
          'data-click-select': String(props.clickSelectOnPan),
        })
    },
  }),
}))

const samplePlots: PlotItem[] = [
  {
    plot_number: 1,
    coords: '[[0.1,0.1],[0.4,0.1],[0.4,0.4],[0.1,0.4]]',
    is_control: true,
    treatment: '',
    dose: '',
  },
  {
    plot_number: 2,
    coords: '[[0.5,0.1],[0.8,0.1],[0.8,0.4],[0.5,0.4]]',
    is_control: false,
    treatment: '快得寧',
    dose: '500x',
  },
]

const allFormulas = [
  { id: 'NDYI', label: 'NDYI', expr: '(G - B) / (G + B)' },
  { id: 'VARI', label: 'VARI', expr: '(G - R) / (G + R - B)' },
  { id: 'MPRI', label: 'MPRI', expr: '(G - R) / (G + R)' },
  { id: 'EXG', label: 'EXG', expr: '(2 * G) - (R + B)' },
  { id: 'GLI', label: 'GLI', expr: '((G * 2) - R - B) / ((G * 2) + R + B)' },
]

const mockBatchStats = {
  result: true,
  data: {
    plots: [
      {
        plot_number: 1,
        is_control: true,
        treatment: '',
        dose: '',
        pixel_count: 1000,
        rgb_mean: [120, 110, 80],
        algorithms: [
          { id: 'VARI', index_mean: 0.05, valid_pixel_count: 1000, rgb_mean: [200, 180, 0] },
          { id: 'GLI', index_mean: 0.08, valid_pixel_count: 1000, rgb_mean: [190, 200, 0] },
          { id: 'EXG', index_mean: 0.04, valid_pixel_count: 1000, rgb_mean: [180, 180, 0] },
        ],
      },
      {
        plot_number: 2,
        is_control: false,
        treatment: '快得寧',
        dose: '500x',
        pixel_count: 1200,
        rgb_mean: [60, 180, 70],
        algorithms: [
          { id: 'VARI', index_mean: 0.25, valid_pixel_count: 1200, rgb_mean: [40, 230, 0] },
          { id: 'GLI', index_mean: 0.30, valid_pixel_count: 1200, rgb_mean: [30, 240, 0] },
          { id: 'EXG', index_mean: 0.22, valid_pixel_count: 1200, rgb_mean: [50, 220, 0] },
        ],
      },
    ],
    control_baseline: {
      plot_count: 1,
      pixel_count: 1000,
      rgb_mean: [120, 110, 80],
      algorithms: [
        { id: 'VARI', index_mean: 0.05, valid_pixel_count: 1000, rgb_mean: [200, 180, 0] },
        { id: 'GLI', index_mean: 0.08, valid_pixel_count: 1000, rgb_mean: [190, 200, 0] },
        { id: 'EXG', index_mean: 0.04, valid_pixel_count: 1000, rgb_mean: [180, 180, 0] },
      ],
    },
    treatment_groups: [
      {
        key: 'CK',
        label: '對照組 (CK)',
        is_control: true,
        plot_numbers: [1],
        plot_count: 1,
        pixel_count: 1000,
        rgb_mean: [120, 110, 80],
        algorithms: [
          { id: 'VARI', index_mean: 0.05, valid_pixel_count: 1000, rgb_mean: [200, 180, 0] },
          { id: 'GLI', index_mean: 0.08, valid_pixel_count: 1000, rgb_mean: [190, 200, 0] },
        ],
      },
      {
        key: '快得寧::500x',
        label: '快得寧 500x',
        is_control: false,
        plot_numbers: [2],
        plot_count: 1,
        pixel_count: 1200,
        rgb_mean: [60, 180, 70],
        algorithms: [
          { id: 'VARI', index_mean: 0.25, valid_pixel_count: 1200, rgb_mean: [40, 230, 0] },
          { id: 'GLI', index_mean: 0.30, valid_pixel_count: 1200, rgb_mean: [30, 240, 0] },
        ],
      },
    ],
    field_summary: {
      plot_count: 2,
      pixel_count: 2200,
      rgb_mean: [90, 145, 75],
      algorithms: [
        { id: 'VARI', index_mean: 0.15, valid_pixel_count: 2200, rgb_mean: [120, 205, 0] },
        { id: 'GLI', index_mean: 0.19, valid_pixel_count: 2200, rgb_mean: [110, 220, 0] },
      ],
    },
  },
}

describe('Step 4 SpectralWorkspace three-column layout & linkage', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    fetchMock.mockReset()
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).includes('/api/task/plots-statistics/')) {
        return {
          ok: true,
          json: async () => mockBatchStats,
        }
      }
      if (String(url).includes('/api/task/chat')) {
        return {
          ok: true,
          text: async () => '',
        }
      }
      return { ok: true, json: async () => ({}) }
    })
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('normalizes recommended_formulas in scenarioSchema', () => {
    const normalized = normalizeScenario({
      version: 2,
      type: 'pesticide',
      title: '藥效試驗',
      recommended_formulas: ['vari', 'GLI', 'INVALID', 'VARI'],
      categories: [{ name: 'CK', color: '#94a3b8', is_control: true }],
    })
    expect(normalized.recommended_formulas).toEqual(['VARI', 'GLI'])
  })

  it('renders 3 columns with resizable dividers and strictly filters formulas from Step 2 scenario', async () => {
    const wrapper = mount(SpectralWorkspace, {
      props: {
        projectId: 'proj-4',
        projectName: '測試田區',
        projectProgress: 100,
        scenario: {
          version: 2,
          type: 'pesticide',
          title: '水稻殺蟲試驗',
          recommended_formulas: ['VARI', 'GLI'],
          categories: [{ name: 'CK', color: '#94a3b8', is_control: true }],
        },
        plots: samplePlots,
        formulas: allFormulas,
        selectedFormula: 'rgb',
        selectedPlotNumbers: [],
        getPlotColor: () => '#10b981',
      },
    })

    await flushPromises()

    expect(wrapper.find('[data-testid="spectral-stats-panel"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="spectral-chat-panel"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="spectral-map-panel"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="spectral-divider-left"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="spectral-divider-right"]').exists()).toBe(true)

    // Strictly only RGB + VARI + GLI are rendered in the formula switcher
    expect(wrapper.find('[data-testid="formula-option-rgb"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="formula-option-VARI"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="formula-option-GLI"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="formula-option-EXG"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="formula-option-NDYI"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="formula-option-MPRI"]').exists()).toBe(false)
  })

  it('updates chat target context when selecting plots without auto-triggering POST /api/task/chat', async () => {
    const wrapper = mount(SpectralWorkspace, {
      props: {
        projectId: 'proj-4b',
        projectName: '測試田區',
        projectProgress: 100,
        scenario: {
          version: 2,
          type: 'pesticide',
          title: '水稻殺蟲試驗',
          recommended_formulas: ['VARI', 'GLI'],
          categories: [{ name: 'CK', color: '#94a3b8', is_control: true }],
        },
        plots: samplePlots,
        formulas: allFormulas,
        selectedFormula: 'VARI',
        selectedPlotNumbers: [],
        getPlotColor: () => '#10b981',
      },
    })

    await flushPromises()
    expect(wrapper.find('[data-testid="spectral-chat-target-badge"]').text()).toContain('全田區')

    // Click plot #2 chip in left panel -> emits select-plots([2])
    await wrapper.find('[data-testid="stats-plot-chip-2"]').trigger('click')
    expect(wrapper.emitted('select-plots')?.[0]).toEqual([[2]])

    // Simulate parent updating selectedPlotNumbers prop
    await wrapper.setProps({ selectedPlotNumbers: [2] })
    await flushPromises()

    expect(wrapper.find('[data-testid="spectral-chat-target-badge"]').text()).toContain('#2 快得寧 500x')
    // Must NEVER auto-POST to /api/task/chat when plot selection changes
    const postChatCalls = fetchMock.mock.calls.filter(
      ([url, init]) => String(url).includes('/api/task/chat') && init?.method === 'POST'
    )
    expect(postChatCalls.length).toBe(0)
  })

  it('renders ANOVA banner, Tukey letters, box/bar chart toggle, and syncs map selection on outlier click', async () => {
    const richStats = {
      result: true,
      data: {
        ...mockBatchStats.data,
        treatment_groups: [
          {
            ...mockBatchStats.data.treatment_groups[0],
            algorithms: [
              {
                id: 'VARI',
                index_mean: 0.05,
                index_std: 0.01,
                index_cv_pct: 20.0,
                index_min: 0.04,
                index_q1: 0.045,
                index_median: 0.05,
                index_q3: 0.055,
                index_max: 0.06,
                replicate_count: 3,
                tukey_group: 'b',
                outlier_plot_numbers: [1],
                valid_pixel_count: 1000,
                rgb_mean: [200, 180, 0],
              },
            ],
          },
          {
            ...mockBatchStats.data.treatment_groups[1],
            algorithms: [
              {
                id: 'VARI',
                index_mean: 0.25,
                index_std: 0.02,
                index_cv_pct: 8.0,
                index_min: 0.23,
                index_q1: 0.24,
                index_median: 0.25,
                index_q3: 0.26,
                index_max: 0.27,
                replicate_count: 3,
                tukey_group: 'a',
                outlier_plot_numbers: [],
                valid_pixel_count: 1200,
                rgb_mean: [40, 230, 0],
              },
            ],
          },
        ],
        statistical_tests: {
          VARI: {
            formula_id: 'VARI',
            status: 'ok',
            message: '單因子 ANOVA 達顯著差異 (F=42.5, p < 0.001)，已依 Tukey HSD 標記分群字母',
            alpha: 0.05,
            anova_f: 42.5,
            anova_p: 0.0002,
            significant: true,
            group_letters: { '快得寧::500x': 'a', CK: 'b' },
            pairwise: [
              {
                group_a: '快得寧::500x',
                group_b: 'CK',
                label_a: '快得寧 500x',
                label_b: '對照組 (CK)',
                mean_diff: 0.2,
                p_value: 0.0002,
                significant: true,
              },
            ],
          },
        },
        outliers: {
          VARI: [
            {
              plot_number: 1,
              group_key: 'CK',
              group_label: '對照組 (CK)',
              is_control: true,
              formula_id: 'VARI',
              value: 0.05,
              group_mean: 0.05,
              group_median: 0.05,
              group_cv_pct: 20.0,
              method: 'cv_15_n3',
              direction: 'low',
              reason: '3 重複組內變異係數 CV=20.0% (>15%)，建議複查影像',
            },
          ],
        },
      },
    }

    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).includes('/api/task/plots-statistics/')) {
        return { ok: true, json: async () => richStats }
      }
      return { ok: true, text: async () => '' }
    })

    const wrapper = mount(SpectralWorkspace, {
      props: {
        projectId: 'proj-4c',
        projectName: '測試田區',
        projectProgress: 100,
        scenario: {
          version: 2,
          type: 'pesticide',
          title: '水稻殺蟲試驗',
          recommended_formulas: ['VARI'],
          categories: [{ name: 'CK', color: '#94a3b8', is_control: true }],
        },
        plots: samplePlots,
        formulas: allFormulas,
        selectedFormula: 'VARI',
        selectedPlotNumbers: [],
        getPlotColor: () => '#10b981',
      },
    })

    await flushPromises()

    expect(wrapper.find('[data-testid="spectral-group-chart"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="spectral-anova-banner"]').text()).toContain('ANOVA 顯著')
    expect(wrapper.find('[data-testid="tukey-letter-快得寧::500x"]').text()).toBe('a')
    expect(wrapper.find('[data-testid="tukey-letter-CK"]').text()).toBe('b')

    // 切換箱型圖模式
    await wrapper.find('[data-testid="chart-mode-box"]').trigger('click')
    expect(wrapper.find('[data-testid="spectral-group-chart"] svg').exists()).toBe(true)

    // 點擊離群小區警示 -> 應立即發送 select-plots([1]) 定位右側地圖
    expect(wrapper.find('[data-testid="spectral-outlier-alerts"]').exists()).toBe(true)
    await wrapper.find('[data-testid="outlier-alert-plot-1"]').trigger('click')
    expect(wrapper.emitted('select-plots')?.[0]).toEqual([[1]])

    // 點擊圖上散點 #2 -> 應發送 select-plots([2])
    await wrapper.find('[data-testid="chart-point-plot-2"]').trigger('click')
    expect(wrapper.emitted('select-plots')?.[1]).toEqual([[2]])
  })
})
