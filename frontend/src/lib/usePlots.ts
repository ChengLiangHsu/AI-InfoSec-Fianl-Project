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
  const activeMode = ref<'view' | 'draw' | 'assign'>('view')
  const selectedPlotNumber = ref<number | null>(null)
  const isDirty = ref(false)
  const isSaving = ref(false)
  const errorMessage = ref<string | null>(null)

  const activeBrush = ref<ActiveBrush>({
    isControl: false,
    treatment: '',
    dose: '',
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

  function addPlot(points: NormalizedPoint[]): PlotItem | null {
    if (points.length < 3) return null
    const maxNum = plots.value.reduce((acc, cur) => Math.max(acc, cur.plot_number), 0)
    const newPlot: PlotItem = {
      plot_number: maxNum + 1,
      coords: serializePoints(points),
      is_control: false,
      treatment: '',
      dose: '',
      metrics: {},
    }
    plots.value.push(newPlot)
    selectedPlotNumber.value = newPlot.plot_number
    isDirty.value = true
    return newPlot
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

  function assignTreatmentToPlot(plotNumber: number): void {
    const target = plots.value.find((p) => p.plot_number === plotNumber)
    if (!target) return
    if (activeBrush.value.isControl) {
      target.is_control = true
      target.treatment = ''
      target.dose = ''
    } else {
      target.is_control = false
      target.treatment = activeBrush.value.treatment.trim()
      target.dose = activeBrush.value.dose.trim()
    }
    isDirty.value = true
  }

  function clearAllPlots(): void {
    plots.value = []
    selectedPlotNumber.value = null
    isDirty.value = true
  }

  return {
    plots,
    activeMode,
    selectedPlotNumber,
    activeBrush,
    isDirty,
    isSaving,
    errorMessage,
    treatmentColorMap,
    getPlotColor,
    loadPlots,
    savePlots,
    addPlot,
    updatePlotPoints,
    deletePlot,
    assignTreatmentToPlot,
    clearAllPlots,
  }
}

