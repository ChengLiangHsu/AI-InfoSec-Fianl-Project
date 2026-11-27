import { describe, it, expect } from 'vitest'
import {
  CONTROL_COLOR,
  createManualDefaultScenario,
  deriveCategorySummary,
  hasConfiguredScenario,
  normalizeScenario,
  type ScenarioData,
} from '@/lib/scenarioSchema'
import { usePlots } from '@/lib/usePlots'

describe('scenarioSchema', () => {
  it('detects whether a project has a configured scenario', () => {
    expect(hasConfiguredScenario(null)).toBe(false)
    expect(hasConfiguredScenario(undefined)).toBe(false)
    expect(hasConfiguredScenario({} as ScenarioData)).toBe(false)
    expect(hasConfiguredScenario(createManualDefaultScenario())).toBe(true)
  })

  it('normalizes legacy v1 pesticide scenario into v2 with locked CK at index 0', () => {
    const legacy = {
      type: 'pesticide',
      title: '舊版農藥試驗',
      target: '快得寧',
      categories: [
        { name: '快得寧 500x', treatment: '快得寧', dose: '500x', color: '#10b981', is_control: false },
        { name: '未施藥對照 (CK)', treatment: '', dose: '', color: '#ff0000', is_control: true },
      ],
    }

    const normalized = normalizeScenario(legacy)
    expect(normalized.version).toBe(2)
    expect(normalized.group_fields?.length).toBe(2)
    expect(normalized.categories[0].is_control).toBe(true)
    expect(normalized.categories[0].color).toBe(CONTROL_COLOR)
    expect(normalized.categories[1].is_control).toBe(false)
    expect(normalized.categories[1].treatment).toBe('快得寧')
    expect(normalized.categories[1].dose).toBe('500x')
    expect(normalized.categories[1].values).toEqual({ treatment: '快得寧', dose: '500x' })
  })

  it('derives summary without dose for non-pesticide multi-type scenarios', () => {
    const groupFields = [
      { key: 'variety', label: '品種名稱', type: 'text' as const, required: true },
      { key: 'method', label: '栽培方式', type: 'select' as const, options: ['慣行', '有機'] },
      { key: 'mulch', label: '覆膜', type: 'boolean' as const },
    ]

    const summary = deriveCategorySummary(
      {
        id: 'grp-1',
        name: '',
        color: '#10b981',
        is_control: false,
        values: { variety: '台農71號', method: '有機', mulch: true },
      },
      groupFields
    )

    expect(summary.label).toBe('台農71號')
    expect(summary.treatment).toBe('台農71號')
    expect(summary.dose).toBe('')
    expect(summary.details).toEqual([
      { key: 'variety', label: '品種名稱', value: '台農71號' },
      { key: 'method', label: '栽培方式', value: '有機' },
      { key: 'mulch', label: '覆膜', value: '是' },
    ])
  })

  it('integrates v2 dynamic scenario with usePlots existingTreatments and plot colors', () => {
    const scenario: ScenarioData = {
      version: 2,
      type: 'pesticide',
      title: '殺菌劑試驗',
      group_fields: [
        { key: 'treatment', label: '藥劑名稱', type: 'text', required: true },
        { key: 'dose', label: '稀釋倍數', type: 'number', unit: '倍', required: true },
        { key: 'method', label: '噴施方式', type: 'select', options: ['葉面噴灑', '無人機'] },
      ],
      categories: [
        { id: 'ck', name: '未施藥對照 (CK)', color: CONTROL_COLOR, is_control: true, values: {} },
        {
          id: 'grp-1',
          name: '快得寧 500倍',
          color: '#8b5cf6',
          is_control: false,
          values: { treatment: '快得寧', dose: 500, method: '無人機' },
        },
      ],
    }

    const { setScenario, existingTreatments, getPlotColor } = usePlots()
    setScenario(scenario)

    expect(existingTreatments.value).toHaveLength(2)
    expect(existingTreatments.value[0].isControl).toBe(true)
    expect(existingTreatments.value[1].label).toBe('快得寧 500倍')
    expect(existingTreatments.value[1].treatment).toBe('快得寧')
    expect(existingTreatments.value[1].dose).toBe('500倍')
    expect(existingTreatments.value[1].details).toEqual([
      { key: 'treatment', label: '藥劑名稱', value: '快得寧' },
      { key: 'dose', label: '稀釋倍數', value: '500倍' },
      { key: 'method', label: '噴施方式', value: '無人機' },
    ])

    const color = getPlotColor({
      plot_number: 1,
      coords: '[[0,0],[1,0],[1,1]]',
      is_control: false,
      treatment: '快得寧',
      dose: '500倍',
    })
    expect(color).toBe('#8b5cf6')
  })

  it('does not append duplicate or extra options from plots when scenario categories are defined', () => {
    const scenario: ScenarioData = {
      version: 2,
      type: 'variety',
      title: '水稻品種比較試驗',
      group_fields: [
        { key: 'variety', label: '品種名稱', type: 'text', required: true },
        { key: 'method', label: '栽培方式', type: 'select', options: ['慣行', '有機'] },
      ],
      categories: [
        { id: 'ck', name: '對照組 (CK)', color: CONTROL_COLOR, is_control: true, values: {} },
        {
          id: 'grp-1',
          name: '台農71號',
          color: '#10b981',
          is_control: false,
          values: { variety: '台農71號', method: '慣行' },
        },
        {
          id: 'grp-2',
          name: '高雄147號',
          color: '#f59e0b',
          is_control: false,
          values: { variety: '高雄147號', method: '慣行' },
        },
      ],
    }

    const { setScenario, plots, existingTreatments } = usePlots()
    setScenario(scenario)
    plots.value = [
      {
        plot_number: 1,
        coords: '[[0,0],[1,0],[1,1]]',
        is_control: false,
        treatment: '台農71號',
        dose: '',
      },
      {
        plot_number: 2,
        coords: '[[0,0],[1,0],[1,1]]',
        is_control: false,
        treatment: '高雄147號',
        dose: '',
      },
      {
        plot_number: 3,
        coords: '[[0,0],[1,0],[1,1]]',
        is_control: false,
        treatment: '舊資料處理組',
        dose: '500x',
      },
    ]

    expect(existingTreatments.value).toHaveLength(3)
    expect(existingTreatments.value.map((t) => t.label)).toEqual([
      '對照組 (CK)',
      '台農71號',
      '高雄147號',
    ])
  })
})
