import { ref, computed } from 'vue'

export interface NormalizedPoint {
  x: number
  y: number
}

export interface PlotItem {
  plot_number: number
  coords: string // JSON 格式字串: "[[x1, y1], [x2, y2], ...]"
  is_control: boolean
  treatment: string
  dose: string
  metrics?: Record<string, number>
}

export interface ActiveBrush {
  isControl: boolean
  treatment: string
  dose: string
}

export interface ExistingTreatment {
  isControl: boolean
  treatment: string
  dose: string
  label: string
}

export interface GridGeneratorState {
  isActive: boolean
  corners: NormalizedPoint[] // [TL, TR, BR, BL]
  rows: number
  cols: number
  marginRatio: number
  isDetecting: boolean
}

const PRESET_COLORS = [
  '#10b981', // emerald
  '#3b82f6', // blue
  '#f59e0b', // amber
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
  '#14b8a6', // teal
]

const CONTROL_COLOR = '#64748b' // slate
const UNASSIGNED_COLOR = '#94a3b8' // gray

export function parseCoords(coordsStr: string): NormalizedPoint[] {
  try {
    const raw = JSON.parse(coordsStr)
    if (!Array.isArray(raw)) return []
    return raw.map((pt: any) => ({
      x: Number(pt[0]),
      y: Number(pt[1]),
    }))
  } catch {
    return []
  }
}

export function serializePoints(points: NormalizedPoint[]): string {
  const rounded = points.map((p) => [
    Number(p.x.toFixed(5)),
    Number(p.y.toFixed(5)),
  ])
  return JSON.stringify(rounded)
}

export function usePlots() {
  const plots = ref<PlotItem[]>([])
  const activeMode = ref<'view' | 'draw'>('view')
  const selectedPlotNumber = ref<number | null>(null)
  const isDirty = ref(false)
  const isSaving = ref(false)
  const errorMessage = ref<string | null>(null)

  // 一鍵自動網格生成狀態
  const gridState = ref<GridGeneratorState>({
    isActive: false,
    corners: [
      { x: 0.30, y: 0.25 },
      { x: 0.55, y: 0.25 },
      { x: 0.55, y: 0.38 },
      { x: 0.30, y: 0.38 },
    ],
    rows: 3,
    cols: 4,
    marginRatio: 0.08,
    isDetecting: false,
  })

  // 動態分配各處理組之顏色標籤
  const treatmentColorMap = computed(() => {
    const map = new Map<string, string>()
    let colorIdx = 0

    for (const p of plots.value) {
      if (p.is_control) {
        map.set('CK', CONTROL_COLOR)
      } else if (p.treatment) {
        const key = `${p.treatment}_${p.dose}`
        if (!map.has(key)) {
          map.set(key, PRESET_COLORS[colorIdx % PRESET_COLORS.length])
          colorIdx++
        }
      }
    }
    return map
  })

  // 取得既有專案中出現過的獨立處理組清單，作為快捷選取按鈕
  const existingTreatments = computed<ExistingTreatment[]>(() => {
    const set = new Set<string>()
    for (const p of plots.value) {
      if (p.is_control) {
        set.add('CK')
      } else if (p.treatment) {
        set.add(`${p.treatment}::${p.dose}`)
      }
    }
    return Array.from(set).map((item) => {
      if (item === 'CK') {
        return { isControl: true, treatment: '', dose: '', label: '未施藥對照 (CK)' }
      }
      const [treatment, dose] = item.split('::')
      return {
        isControl: false,
        treatment,
        dose,
        label: `${treatment}${dose ? ' (' + dose + ')' : ''}`,
      }
    })
  })

  function getPlotColor(plot: PlotItem): string {
    if (plot.is_control) return CONTROL_COLOR
    if (!plot.treatment) return UNASSIGNED_COLOR
    const key = `${plot.treatment}_${plot.dose}`
    return treatmentColorMap.value.get(key) || PRESET_COLORS[0]
  }

  async function loadPlots(taskId: string): Promise<void> {
    if (!taskId) {
      plots.value = []
      isDirty.value = false
      selectedPlotNumber.value = null
      return
    }
    errorMessage.value = null
    try {
      const res = await fetch(`/api/task/plots/${taskId}`)
      const json = await res.json()
      if (res.ok && json.result && Array.isArray(json.data)) {
        plots.value = json.data
        isDirty.value = false
        selectedPlotNumber.value = null
      } else {
        errorMessage.value = json.message || '無法取得小區資料'
      }
    } catch (err: any) {
      errorMessage.value = `載入小區失敗: ${err.message}`
    }
  }

  async function savePlots(taskId: string): Promise<boolean> {
    if (!taskId) return false
    isSaving.value = true
    errorMessage.value = null
    try {
      const payload = {
        plots: plots.value.map((p) => ({
          plot_number: p.plot_number,
          coords: p.coords,
          is_control: p.is_control,
          treatment: p.treatment,
          dose: p.dose,
          metrics: p.metrics || {},
        })),
      }
      const res = await fetch(`/api/task/plots/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const json = await res.json()
      if (res.ok && json.result) {
        if (Array.isArray(json.data)) {
          plots.value = json.data
        }
        isDirty.value = false
        return true
      } else {
        errorMessage.value = json.message || '儲存小區失敗'
        return false
      }
    } catch (err: any) {
      errorMessage.value = `儲存失敗: ${err.message}`
      return false
    } finally {
      isSaving.value = false
    }
  }

  function addPlotWithTreatment(
    points: NormalizedPoint[],
    treatment: string,
    dose: string,
    isControl: boolean
  ): PlotItem | null {
    if (points.length < 3) return null
    const maxNum = plots.value.reduce((acc, cur) => Math.max(acc, cur.plot_number), 0)
    const newPlot: PlotItem = {
      plot_number: maxNum + 1,
      coords: serializePoints(points),
      is_control: isControl,
      treatment: isControl ? '' : treatment.trim(),
      dose: isControl ? '' : dose.trim(),
      metrics: {},
    }
    plots.value.push(newPlot)
    selectedPlotNumber.value = newPlot.plot_number
    isDirty.value = true
    return newPlot
  }

  function updatePlotTreatment(
    plotNumber: number,
    treatment: string,
    dose: string,
    isControl: boolean
  ): void {
    const target = plots.value.find((p) => p.plot_number === plotNumber)
    if (!target) return
    target.is_control = isControl
    target.treatment = isControl ? '' : treatment.trim()
    target.dose = isControl ? '' : dose.trim()
    isDirty.value = true
  }

  function updatePlotPoints(plotNumber: number, points: NormalizedPoint[]): void {
    if (points.length < 3) return
    const target = plots.value.find((p) => p.plot_number === plotNumber)
    if (target) {
      target.coords = serializePoints(points)
      isDirty.value = true
    }
  }

  function deletePlot(plotNumber: number): void {
    const idx = plots.value.findIndex((p) => p.plot_number === plotNumber)
    if (idx !== -1) {
      plots.value.splice(idx, 1)
      if (selectedPlotNumber.value === plotNumber) {
        selectedPlotNumber.value = null
      }
      isDirty.value = true
    }
  }

  function clearAllPlots(): void {
    plots.value = []
    selectedPlotNumber.value = null
    isDirty.value = true
  }

  function startGridMode(defaultCorners?: NormalizedPoint[]): void {
    gridState.value.isActive = true
    if (defaultCorners && defaultCorners.length === 4) {
      gridState.value.corners = defaultCorners
    }
  }

  function closeGridMode(): void {
    gridState.value.isActive = false
  }

  function updateGridCorner(index: number, pt: NormalizedPoint): void {
    if (index >= 0 && index < 4 && gridState.value.corners[index]) {
      gridState.value.corners[index] = {
        x: Math.max(0, Math.min(1, Number(pt.x.toFixed(5)))),
        y: Math.max(0, Math.min(1, Number(pt.y.toFixed(5)))),
      }
    }
  }

  async function detectMarkers(taskId: string, roi?: [number, number, number, number]): Promise<boolean> {
    if (!taskId) return false
    gridState.value.isDetecting = true
    errorMessage.value = null
    try {
      const res = await fetch(`/api/task/detect-markers/${taskId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ roi }),
      })
      const json = await res.json()
      if (res.ok && json.result && Array.isArray(json.data?.corners) && json.data.corners.length === 4) {
        gridState.value.corners = json.data.corners.map((pt: [number, number]) => ({
          x: pt[0],
          y: pt[1],
        }))
        return true
      } else {
        errorMessage.value = json.message || '無法自動偵測四角白色定位牌'
        return false
      }
    } catch (err: any) {
      errorMessage.value = `偵測定位牌失敗: ${err.message}`
      return false
    } finally {
      gridState.value.isDetecting = false
    }
  }

  function computeGridPlots(): NormalizedPoint[][] {
    const { corners, rows, cols, marginRatio } = gridState.value
    if (corners.length < 4 || rows <= 0 || cols <= 0) return []

    const p00 = corners[0] // TL (u=0, v=0)
    const p10 = corners[1] // TR (u=1, v=0)
    const p11 = corners[2] // BR (u=1, v=1)
    const p01 = corners[3] // BL (u=0, v=1)

    function interp(u: number, v: number): NormalizedPoint {
      const x = (1 - u) * (1 - v) * p00.x + u * (1 - v) * p10.x + u * v * p11.x + (1 - u) * v * p01.x
      const y = (1 - u) * (1 - v) * p00.y + u * (1 - v) * p10.y + u * v * p11.y + (1 - u) * v * p01.y
      return {
        x: Math.max(0, Math.min(1, Number(x.toFixed(5)))),
        y: Math.max(0, Math.min(1, Number(y.toFixed(5)))),
      }
    }

    const marginU = (1.0 / cols) * marginRatio
    const marginV = (1.0 / rows) * marginRatio

    const result: NormalizedPoint[][] = []
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const uMin = c / cols + marginU
        const uMax = (c + 1) / cols - marginU
        const vMin = r / rows + marginV
        const vMax = (r + 1) / rows - marginV

        // 小區多邊形四頂點：TL, TR, BR, BL
        result.push([
          interp(uMin, vMin),
          interp(uMax, vMin),
          interp(uMax, vMax),
          interp(uMin, vMax),
        ])
      }
    }
    return result
  }

  function confirmBatchGenerate(mode: 'replace' | 'append' = 'replace'): void {
    const polys = computeGridPlots()
    if (polys.length === 0) return

    if (mode === 'replace') {
      plots.value = []
    }

    let startNum = mode === 'replace'
      ? 1
      : plots.value.reduce((acc, cur) => Math.max(acc, cur.plot_number), 0) + 1

    for (const poly of polys) {
      plots.value.push({
        plot_number: startNum++,
        coords: serializePoints(poly),
        is_control: false,
        treatment: '',
        dose: '',
        metrics: {},
      })
    }

    isDirty.value = true
    selectedPlotNumber.value = null
    closeGridMode()
  }

  return {
    plots,
    activeMode,
    selectedPlotNumber,
    isDirty,
    isSaving,
    errorMessage,
    gridState,
    treatmentColorMap,
    existingTreatments,
    getPlotColor,
    loadPlots,
    savePlots,
    addPlotWithTreatment,
    updatePlotTreatment,
    updatePlotPoints,
    deletePlot,
    clearAllPlots,
    startGridMode,
    closeGridMode,
    updateGridCorner,
    detectMarkers,
    computeGridPlots,
    confirmBatchGenerate,
  }
}
