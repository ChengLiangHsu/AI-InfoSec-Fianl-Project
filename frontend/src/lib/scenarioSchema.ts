export type DynamicFieldType = 'text' | 'number' | 'select' | 'date' | 'boolean'

export type DynamicFieldValue = string | number | boolean | null | undefined

export interface DynamicFieldDef {
  key: string
  label: string
  type: DynamicFieldType
  unit?: string
  options?: string[]
  placeholder?: string
  required?: boolean
}

export interface ScenarioCategoryItem {
  id?: string
  name: string
  color: string
  is_control?: boolean
  values?: Record<string, DynamicFieldValue>
  treatment?: string
  dose?: string
}

export interface ScenarioData {
  version?: 2
  type: string
  title: string
  description?: string
  metadata_fields?: DynamicFieldDef[]
  metadata_values?: Record<string, DynamicFieldValue>
  group_fields?: DynamicFieldDef[]
  categories: ScenarioCategoryItem[]
  recommended_formulas?: string[]
  target?: string
  target_label?: string
}

export interface CategoryDetailItem {
  key: string
  label: string
  value: string
}

export const CONTROL_COLOR = '#94a3b8'

export const TREATMENT_PALETTE = [
  '#10b981', // Emerald
  '#8b5cf6', // Violet
  '#f59e0b', // Amber
  '#0ea5e9', // Sky
  '#ec4899', // Pink
  '#f97316', // Orange
  '#06b6d4', // Cyan
  '#84cc16', // Lime
  '#e11d48', // Rose
]

const VALID_FIELD_TYPES: ReadonlySet<string> = new Set([
  'text',
  'number',
  'select',
  'date',
  'boolean',
])

const DOSE_KEY_HINTS = [
  'dose',
  'dosage',
  'rate',
  'dilution',
  'concentration',
  '劑量',
  '倍數',
  '濃度',
  '施用量',
]

export function isDoseLikeField(field: DynamicFieldDef): boolean {
  const keyLower = (field.key || '').toLowerCase()
  const labelLower = (field.label || '').toLowerCase()
  return DOSE_KEY_HINTS.some((hint) => keyLower.includes(hint) || labelLower.includes(hint))
}

export function formatDynamicFieldValue(val: DynamicFieldValue, field: DynamicFieldDef): string {
  if (val === null || val === undefined || val === '') return ''
  if (field.type === 'boolean') {
    return val ? '是' : '否'
  }
  const text = String(val).trim()
  if (!text) return ''
  const unit = (field.unit || '').trim()
  if (unit && field.type === 'number' && !text.endsWith(unit)) {
    return `${text}${unit}`
  }
  return text
}

export function normalizeFieldDefs(rawFields: unknown): DynamicFieldDef[] {
  if (!Array.isArray(rawFields)) return []
  const result: DynamicFieldDef[] = []
  const seen = new Set<string>()
  rawFields.forEach((raw, idx) => {
    if (!raw || typeof raw !== 'object') return
    const obj = raw as Record<string, unknown>
    let key = String(obj.key || `field_${idx + 1}`).trim()
    if (!key || seen.has(key)) {
      key = `field_${idx + 1}`
    }
    seen.add(key)

    const rawType = String(obj.type || 'text').trim().toLowerCase()
    const type = (VALID_FIELD_TYPES.has(rawType) ? rawType : 'text') as DynamicFieldType
    const label = String(obj.label || key).trim()

    const field: DynamicFieldDef = {
      key,
      label,
      type,
    }
    const unit = String(obj.unit || '').trim()
    if (unit) field.unit = unit
    if (type === 'select') {
      field.options = Array.isArray(obj.options)
        ? obj.options.map((o) => String(o).trim()).filter(Boolean)
        : []
    }
    const placeholder = String(obj.placeholder || '').trim()
    if (placeholder) field.placeholder = placeholder
    if (typeof obj.required === 'boolean') field.required = obj.required
    result.push(field)
  })
  return result
}

export function hasConfiguredScenario(scenario: ScenarioData | Record<string, unknown> | null | undefined): boolean {
  if (!scenario || typeof scenario !== 'object') return false
  const sc = scenario as Partial<ScenarioData>
  const hasCategories = Array.isArray(sc.categories) && sc.categories.length > 0
  const hasFields =
    (Array.isArray(sc.group_fields) && sc.group_fields.length > 0) ||
    (Array.isArray(sc.metadata_fields) && sc.metadata_fields.length > 0)
  return hasCategories || hasFields
}

export function deriveCategorySummary(
  cat: ScenarioCategoryItem,
  groupFields: DynamicFieldDef[] = []
): {
  label: string
  treatment: string
  dose: string
  details: CategoryDetailItem[]
} {
  if (cat.is_control) {
    return {
      label: (cat.name || '').trim() || '對照組 (CK)',
      treatment: '',
      dose: '',
      details: [],
    }
  }

  const values = cat.values && typeof cat.values === 'object' ? cat.values : {}
  const details: CategoryDetailItem[] = []

  for (const field of groupFields) {
    const formatted = formatDynamicFieldValue(values[field.key], field)
    if (formatted) {
      details.push({
        key: field.key,
        label: field.label,
        value: formatted,
      })
    }
  }

  if (groupFields.length > 0) {
    const doseField = groupFields.find(isDoseLikeField)
    const primaryField = groupFields.find((f) => f !== doseField)

    const primaryText = primaryField
      ? formatDynamicFieldValue(values[primaryField.key], primaryField)
      : ''
    const doseText = doseField
      ? formatDynamicFieldValue(values[doseField.key], doseField)
      : ''

    const parts = [primaryText, doseText].filter(Boolean)
    const fallbackName = (cat.name || '').trim()
    const label = parts.length > 0 ? parts.join(' ') : (fallbackName || '處理組')
    const treatment = primaryText || (cat.treatment || '').trim() || label
    const dose = doseField ? doseText : ''

    return { label, treatment, dose, details }
  }

  // Legacy v1 fallback
  const trt = (cat.treatment || '').trim()
  const ds = (cat.dose || '').trim()
  const label = [trt, ds].filter(Boolean).join(' ') || (cat.name || '').trim() || '處理組'
  if (trt) details.push({ key: 'treatment', label: '處理', value: trt })
  if (ds) details.push({ key: 'dose', label: '劑量', value: ds })
  return {
    label,
    treatment: trt || label,
    dose: ds,
    details,
  }
}

export function createManualDefaultScenario(): ScenarioData {
  return {
    version: 2,
    type: 'custom',
    title: '自訂田間試驗',
    description: '',
    metadata_fields: [
      { key: 'crop', label: '試驗作物', type: 'text', placeholder: '例：水稻、玉米' },
      { key: 'trial_date', label: '試驗日期', type: 'date' },
    ],
    metadata_values: {
      crop: '',
      trial_date: '',
    },
    group_fields: [
      { key: 'treatment', label: '處理 / 組別名稱', type: 'text', placeholder: '例：快得寧 或 品種 A', required: true },
      { key: 'dose', label: '施用劑量 / 參數（選填）', type: 'text', placeholder: '例：500x（若不適用可刪除欄位）', required: false },
    ],
    categories: [
      {
        id: 'ck',
        name: '對照組 (CK)',
        color: CONTROL_COLOR,
        is_control: true,
        values: {},
        treatment: '',
        dose: '',
      },
      {
        id: 'grp-1',
        name: '處理組 1',
        color: TREATMENT_PALETTE[0],
        is_control: false,
        values: { treatment: '', dose: '' },
        treatment: '',
        dose: '',
      },
    ],
  }
}

const CANONICAL_RGB_FORMULAS: ReadonlyMap<string, string> = new Map([
  ['ndyi', 'NDYI'],
  ['vari', 'VARI'],
  ['mpri', 'MPRI'],
  ['exg', 'EXG'],
  ['gli', 'GLI'],
])

export function normalizeRecommendedFormulas(raw: unknown): string[] {
  if (!Array.isArray(raw)) return []
  const result: string[] = []
  const seen = new Set<string>()
  for (const item of raw) {
    if (typeof item !== 'string') continue
    const canonical = CANONICAL_RGB_FORMULAS.get(item.trim().toLowerCase())
    if (canonical && !seen.has(canonical)) {
      seen.add(canonical)
      result.push(canonical)
    }
  }
  return result
}

export function normalizeScenario(raw: ScenarioData | Record<string, unknown> | null | undefined): ScenarioData {
  if (!raw || typeof raw !== 'object' || Object.keys(raw).length === 0) {
    return createManualDefaultScenario()
  }

  const data = raw as Partial<ScenarioData>
  const isV2 =
    data.version === 2 ||
    Array.isArray(data.group_fields) ||
    Array.isArray(data.metadata_fields)

  const metadataFields = isV2 ? normalizeFieldDefs(data.metadata_fields) : []
  const metadataValues: Record<string, DynamicFieldValue> =
    isV2 && data.metadata_values && typeof data.metadata_values === 'object'
      ? { ...data.metadata_values }
      : {}

  const groupFields: DynamicFieldDef[] = isV2
    ? normalizeFieldDefs(data.group_fields)
    : [
        {
          key: 'treatment',
          label: data.target_label || '藥劑 / 組別名稱',
          type: 'text',
          placeholder: '例：快得寧',
          required: true,
        },
        {
          key: 'dose',
          label: '施用劑量 / 倍數',
          type: 'text',
          placeholder: '例：500x',
          required: false,
        },
      ]

  const rawCategories = Array.isArray(data.categories) ? data.categories : []
  const defaultTarget = (data.target || '').trim()

  let controlItem = rawCategories.find((c) => c && c.is_control)
  const treatmentItems = rawCategories.filter((c) => c && c !== controlItem)

  if (!controlItem && treatmentItems.length > 0) {
    controlItem = treatmentItems.shift()
  }

  const normalizedCategories: ScenarioCategoryItem[] = [
    {
      id: controlItem?.id || 'ck',
      name: (controlItem?.name || '').trim() || '對照組 (CK)',
      color: CONTROL_COLOR,
      is_control: true,
      values: {},
      treatment: '',
      dose: '',
    },
  ]

  treatmentItems.forEach((cat, idx) => {
    const color = (cat.color || '').trim() || TREATMENT_PALETTE[idx % TREATMENT_PALETTE.length]
    let values: Record<string, DynamicFieldValue> =
      cat.values && typeof cat.values === 'object' ? { ...cat.values } : {}

    if (!isV2) {
      let trt = (cat.treatment || '').trim()
      let ds = (cat.dose || '').trim()
      const nm = (cat.name || '').trim()
      if (!trt && defaultTarget) trt = defaultTarget
      if (!ds && nm && nm !== trt) ds = nm
      values = {
        treatment: trt || nm,
        dose: ds,
      }
    }

    const baseCat: ScenarioCategoryItem = {
      id: cat.id || `grp-${idx + 1}`,
      name: (cat.name || '').trim(),
      color,
      is_control: false,
      values,
      treatment: cat.treatment || '',
      dose: cat.dose || '',
    }
    const summary = deriveCategorySummary(baseCat, groupFields)
    baseCat.name = summary.label || baseCat.name || `處理組 ${idx + 1}`
    baseCat.treatment = summary.treatment
    baseCat.dose = summary.dose
    normalizedCategories.push(baseCat)
  })

  const recommendedFormulas = normalizeRecommendedFormulas(data.recommended_formulas)

  return {
    version: 2,
    type: (data.type || 'custom').trim() || 'custom',
    title: (data.title || '試驗情境設定').trim() || '試驗情境設定',
    description: (data.description || '').trim(),
    metadata_fields: metadataFields,
    metadata_values: metadataValues,
    group_fields: groupFields,
    categories: normalizedCategories,
    ...(recommendedFormulas.length > 0 ? { recommended_formulas: recommendedFormulas } : {}),
  }
}
