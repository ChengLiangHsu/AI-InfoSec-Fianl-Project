import { ref, computed, watch } from 'vue'

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
  color?: string
}

export interface ScenarioCategoryItem {
  treatment?: string
  name: string
  dose?: string
  color: string
  is_control?: boolean
}

export interface ScenarioDefinition {
  type?: string
  title?: string
  target?: string
  target_label?: string
  categories?: ScenarioCategoryItem[]
}

export interface GridGeneratorState {
  isActive: boolean
  corners: NormalizedPoint[] // [TL, TR, BR, BL]
  rows: number
  cols: number
  scaleX: number // 小區寬度比例 (0.05 ~ 1.0, 預設 0.40)
  scaleY: number // 小區高度比例 (0.05 ~ 1.0, 預設 0.40)
  marginRatio: number // 向後相容保留 (等於 (1 - scaleX) / 2)
  paddingRatio: number // 田區外邊距留白 (0.0 ~ 0.25, 預設 0.0)
  offsetX: number // 網格水平中心微調 (-0.25 ~ 0.25, 預設 0.0)
  offsetY: number // 網格垂直中心微調 (-0.25 ~ 0.25, 預設 0.0)
  excludedIndices: number[] // 排除的單元格索引 (r * cols + c)
  isDetecting: boolean
}

export interface CellSpan {
  uMin: number
  uMax: number
  vMin: number
  vMax: number
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

const CONTROL_COLOR = '#94a3b8' // slate (與情境設定統一為靜態灰白)
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

export function calculatePlotCentroid(points: NormalizedPoint[]): NormalizedPoint {
  if (points.length === 0) return { x: 0, y: 0 }
  if (points.length === 1) return { x: points[0].x, y: points[0].y }
  if (points.length === 2) {
    return {
      x: (points[0].x + points[1].x) / 2,
      y: (points[0].y + points[1].y) / 2,
    }
  }

  let signedArea = 0
  let cx = 0
  let cy = 0
  const n = points.length

  for (let i = 0; i < n; i++) {
    const p0 = points[i]
    const p1 = points[(i + 1) % n]
    const cross = p0.x * p1.y - p1.x * p0.y
    signedArea += cross
    cx += (p0.x + p1.x) * cross
    cy += (p0.y + p1.y) * cross
  }

  signedArea *= 0.5
  if (Math.abs(signedArea) < 1e-7) {
    const sumX = points.reduce((acc, p) => acc + p.x, 0)
    const sumY = points.reduce((acc, p) => acc + p.y, 0)
    return { x: sumX / n, y: sumY / n }
  }

  return {
    x: Math.max(0, Math.min(1, Number((cx / (6 * signedArea)).toFixed(5)))),
    y: Math.max(0, Math.min(1, Number((cy / (6 * signedArea)).toFixed(5)))),
  }
}

export function shiftPoints(
  points: NormalizedPoint[],
  dx: number,
  dy: number
): NormalizedPoint[] {
  return points.map((p) => ({
    x: Math.max(0, Math.min(1, Number((p.x + dx).toFixed(5)))),
    y: Math.max(0, Math.min(1, Number((p.y + dy).toFixed(5)))),
  }))
}

export function clampGridCorners(
  corners: NormalizedPoint[],
  dx: number,
  dy: number
): NormalizedPoint[] {
  if (!corners || corners.length < 4) return corners

  let minX = 1
  let maxX = 0
  let minY = 1
  let maxY = 0
  for (const c of corners) {
    if (c.x < minX) minX = c.x
    if (c.x > maxX) maxX = c.x
    if (c.y < minY) minY = c.y
    if (c.y > maxY) maxY = c.y
  }

  const clampedDx = Math.max(-minX, Math.min(1 - maxX, dx))
  const clampedDy = Math.max(-minY, Math.min(1 - maxY, dy))

  return corners.map((c) => ({
    x: Math.max(0, Math.min(1, Number((c.x + clampedDx).toFixed(5)))),
    y: Math.max(0, Math.min(1, Number((c.y + clampedDy).toFixed(5)))),
  }))
}

export function interpolateBilinear(
  u: number,
  v: number,
  corners: NormalizedPoint[]
): NormalizedPoint {
  const p00 = corners[0] // TL (u=0, v=0)
  const p10 = corners[1] // TR (u=1, v=0)
  const p11 = corners[2] // BR (u=1, v=1)
  const p01 = corners[3] // BL (u=0, v=1)

  const x = (1 - u) * (1 - v) * p00.x + u * (1 - v) * p10.x + u * v * p11.x + (1 - u) * v * p01.x
  const y = (1 - u) * (1 - v) * p00.y + u * (1 - v) * p10.y + u * v * p11.y + (1 - u) * v * p01.y

  return {
    x: Math.max(0, Math.min(1, Number(x.toFixed(5)))),
    y: Math.max(0, Math.min(1, Number(y.toFixed(5)))),
  }
}

export function calculateCellNormalizedSpan(
  c: number,
  r: number,
  state: GridGeneratorState
): CellSpan {
  const { rows, cols } = state
  const padding = Math.max(0, Math.min(0.25, state.paddingRatio || 0))
  const spanU = 1 - 2 * padding
  const spanV = 1 - 2 * padding

  const cellW = spanU / cols
  const cellH = spanV / rows

  const offX = (state.offsetX || 0) * cellW
  const offY = (state.offsetY || 0) * cellH

  const centerU = padding + (c + 0.5) * cellW + offX
  const centerV = padding + (r + 0.5) * cellH + offY

  // 優先採用 scaleX/scaleY；若未提供則由 marginRatio 計算 (scale = 1 - 2 * marginRatio)
  const effScaleX = state.scaleX !== undefined
    ? state.scaleX
    : Math.max(0.05, 1 - 2 * (state.marginRatio || 0.08))
  const effScaleY = state.scaleY !== undefined
    ? state.scaleY
    : Math.max(0.05, 1 - 2 * (state.marginRatio || 0.08))

  const scaleX = Math.max(0.05, Math.min(1, effScaleX))
  const scaleY = Math.max(0.05, Math.min(1, effScaleY))

  const halfW = 0.5 * scaleX * cellW
  const halfH = 0.5 * scaleY * cellH

  return {
    uMin: Math.max(0, Math.min(1, centerU - halfW)),
    uMax: Math.max(0, Math.min(1, centerU + halfW)),
    vMin: Math.max(0, Math.min(1, centerV - halfH)),
    vMax: Math.max(0, Math.min(1, centerV + halfH)),
  }
}

export function generateSubplotPolygon(
  span: CellSpan,
  corners: NormalizedPoint[]
): NormalizedPoint[] {
  return [
    interpolateBilinear(span.uMin, span.vMin, corners),
    interpolateBilinear(span.uMax, span.vMin, corners),
    interpolateBilinear(span.uMax, span.vMax, corners),
    interpolateBilinear(span.uMin, span.vMax, corners),
  ]
}

export function usePlots() {
  const plots = ref<PlotItem[]>([])
  const activeMode = ref<'view' | 'draw'>('view')
  const selectedPlotNumbers = ref<number[]>([])
  const selectedPlotNumber = computed<number | null>({
    get: () => (selectedPlotNumbers.value.length === 1 ? selectedPlotNumbers.value[0] : null),
    set: (val: number | null) => {
      if (val === null) {
        selectedPlotNumbers.value = []
      } else {
        selectedPlotNumbers.value = [val]
      }
    },
  })
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
    rows: 10,
    cols: 3,
    scaleX: 0.38,
    scaleY: 0.38,
    marginRatio: 0.31,
    paddingRatio: 0.0,
    offsetX: 0.0,
    offsetY: 0.0,
    excludedIndices: [],
    isDetecting: false,
  })

  const currentScenario = ref<ScenarioDefinition | null>(null)

  // 當切換為手動繪製模式或啟用一鍵網格時，自動清除選取狀態以防干擾
  watch(activeMode, (newMode) => {
    if (newMode === 'draw') {
      selectedPlotNumbers.value = []
    }
  })

  watch(
    () => gridState.value.isActive,
    (active) => {
      if (active) {
        selectedPlotNumbers.value = []
      }
    }
  )

  function setScenario(sc: ScenarioDefinition | null) {
    currentScenario.value = sc
  }

  // 動態分配各處理組之顏色標籤
  const treatmentColorMap = computed(() => {
    const map = new Map<string, string>()
    let colorIdx = 0

    // 1. 優先注入專案情境特徵所指定的色彩
    if (currentScenario.value?.categories && currentScenario.value.categories.length > 0) {
      const targetName = currentScenario.value.target || ''
      for (const cat of currentScenario.value.categories) {
        if (cat.is_control) {
          map.set('CK', cat.color || CONTROL_COLOR)
        } else {
          const trt = cat.treatment || targetName || ''
          const doseName = cat.dose || cat.name || ''
          if (trt) {
            map.set(`${trt}_${doseName}`, cat.color)
            map.set(`${trt}_${cat.name}`, cat.color)
          }
          if (doseName) map.set(doseName, cat.color)
          if (cat.name) map.set(cat.name, cat.color)
        }
      }
    }

    // 2. 小區畫布既有處理組補足
    for (const p of plots.value) {
      if (p.is_control) {
        if (!map.has('CK')) map.set('CK', CONTROL_COLOR)
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
    const list: ExistingTreatment[] = []
    const seen = new Set<string>()

    // 1. 優先加入專案情境設定之預設標籤
    if (currentScenario.value?.categories && currentScenario.value.categories.length > 0) {
      const targetName = currentScenario.value.target || ''
      for (const cat of currentScenario.value.categories) {
        if (cat.is_control) {
          if (!seen.has('CK')) {
            seen.add('CK')
            list.push({ isControl: true, treatment: '', dose: '', label: cat.name || '未施藥對照 (CK)', color: cat.color || CONTROL_COLOR })
          }
        } else {
          const trt = cat.treatment || targetName || ''
          const doseName = cat.dose || ''
          const label = [trt, doseName].filter(Boolean).join(' ') || cat.name || '處理組'
          const key = `${trt}::${doseName}`
          if (!seen.has(key)) {
            seen.add(key)
            list.push({
              isControl: false,
              treatment: trt,
              dose: doseName,
              label,
              color: cat.color,
            })
          }
        }
      }
    }

    // 確保對照組永遠存在於清單首位
    if (!seen.has('CK')) {
      seen.add('CK')
      list.unshift({ isControl: true, treatment: '', dose: '', label: '未施藥對照 (CK)', color: CONTROL_COLOR })
    }

    // 2. 補充畫布上已有但在情境中未列出的額外處理組
    for (const p of plots.value) {
      if (p.is_control) {
        if (!seen.has('CK')) {
          seen.add('CK')
          list.unshift({ isControl: true, treatment: '', dose: '', label: '未施藥對照 (CK)', color: CONTROL_COLOR })
        }
      } else if (p.treatment) {
        const key = `${p.treatment}::${p.dose}`
        if (!seen.has(key)) {
          seen.add(key)
          list.push({
            isControl: false,
            treatment: p.treatment,
            dose: p.dose,
            label: `${p.treatment}${p.dose ? ' (' + p.dose + ')' : ''}`,
            color: getPlotColor(p),
          })
        }
      }
    }
    return list
  })

  function getPlotColor(plot: PlotItem): string {
    if (plot.is_control) return treatmentColorMap.value.get('CK') || CONTROL_COLOR
    if (!plot.treatment) return UNASSIGNED_COLOR
    const key = `${plot.treatment}_${plot.dose}`
    return (
      treatmentColorMap.value.get(key) ||
      treatmentColorMap.value.get(plot.dose) ||
      treatmentColorMap.value.get(plot.treatment) ||
      PRESET_COLORS[0]
    )
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

  function selectPlots(numbers: number[]): void {
    selectedPlotNumbers.value = Array.from(new Set(numbers))
  }

  function togglePlotSelection(plotNumber: number): void {
    const idx = selectedPlotNumbers.value.indexOf(plotNumber)
    if (idx === -1) {
      selectedPlotNumbers.value.push(plotNumber)
    } else {
      selectedPlotNumbers.value.splice(idx, 1)
    }
  }

  function clearPlotSelection(): void {
    selectedPlotNumbers.value = []
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

  function updatePlotTreatments(
    plotNumbers: number[],
    treatment: string,
    dose: string,
    isControl: boolean
  ): void {
    if (!plotNumbers || plotNumbers.length === 0) return
    const numSet = new Set(plotNumbers)
    for (const p of plots.value) {
      if (numSet.has(p.plot_number)) {
        p.is_control = isControl
        p.treatment = isControl ? '' : treatment.trim()
        p.dose = isControl ? '' : dose.trim()
      }
    }
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
      selectedPlotNumbers.value = selectedPlotNumbers.value.filter((n) => n !== plotNumber)
      isDirty.value = true
    }
  }

  function deletePlots(plotNumbers: number[]): void {
    if (!plotNumbers || plotNumbers.length === 0) return
    const numSet = new Set(plotNumbers)
    plots.value = plots.value.filter((p) => !numSet.has(p.plot_number))
    selectedPlotNumbers.value = selectedPlotNumbers.value.filter((n) => !numSet.has(n))
    isDirty.value = true
  }

  function clearAllPlots(): void {
    plots.value = []
    selectedPlotNumbers.value = []
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

  function updateGridCorners(corners: NormalizedPoint[]): void {
    if (Array.isArray(corners) && corners.length === 4) {
      gridState.value.corners = corners.map((c) => ({
        x: Math.max(0, Math.min(1, Number(c.x.toFixed(5)))),
        y: Math.max(0, Math.min(1, Number(c.y.toFixed(5)))),
      }))
    }
  }

  function moveGrid(delta: { dx: number; dy: number }): void {
    if (!gridState.value.corners || gridState.value.corners.length < 4) return
    gridState.value.corners = clampGridCorners(gridState.value.corners, delta.dx, delta.dy)
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
    const { corners, rows, cols } = gridState.value
    if (corners.length < 4 || rows <= 0 || cols <= 0) return []
    const excludedSet = new Set(gridState.value.excludedIndices || [])

    const result: NormalizedPoint[][] = []
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const cellIdx = r * cols + c
        if (excludedSet.has(cellIdx)) continue
        const span = calculateCellNormalizedSpan(c, r, gridState.value)
        const poly = generateSubplotPolygon(span, corners)
        result.push(poly)
      }
    }
    return result
  }

  function toggleExcludeGridCell(cellIndex: number): void {
    const list = [...(gridState.value.excludedIndices || [])]
    const idx = list.indexOf(cellIndex)
    if (idx !== -1) {
      list.splice(idx, 1)
    } else {
      list.push(cellIndex)
    }
    gridState.value.excludedIndices = list
  }

  function clearExcludedGridCells(): void {
    gridState.value.excludedIndices = []
  }

  function duplicatePlot(plotNumber: number, offset = { dx: 0.02, dy: 0.02 }): PlotItem | null {
    const target = plots.value.find((p) => p.plot_number === plotNumber)
    if (!target) return null
    const pts = parseCoords(target.coords)
    if (pts.length < 3) return null

    const shifted = shiftPoints(pts, offset.dx, offset.dy)
    const maxNum = plots.value.reduce((acc, cur) => Math.max(acc, cur.plot_number), 0)
    const cloned: PlotItem = {
      plot_number: maxNum + 1,
      coords: serializePoints(shifted),
      is_control: target.is_control,
      treatment: target.treatment,
      dose: target.dose,
      metrics: {},
    }
    plots.value.push(cloned)
    selectedPlotNumber.value = cloned.plot_number
    isDirty.value = true
    return cloned
  }

  function duplicateAllPlots(offset = { dx: 0.03, dy: 0.03 }): void {
    if (plots.value.length === 0) return
    let maxNum = plots.value.reduce((acc, cur) => Math.max(acc, cur.plot_number), 0)
    const newPlots: PlotItem[] = []

    for (const p of plots.value) {
      const pts = parseCoords(p.coords)
      if (pts.length < 3) continue
      const shifted = shiftPoints(pts, offset.dx, offset.dy)
      newPlots.push({
        plot_number: ++maxNum,
        coords: serializePoints(shifted),
        is_control: p.is_control,
        treatment: p.treatment,
        dose: p.dose,
        metrics: {},
      })
    }
    plots.value.push(...newPlots)
    isDirty.value = true
  }

  function movePlot(plotNumber: number, delta: { dx: number; dy: number }): void {
    const target = plots.value.find((p) => p.plot_number === plotNumber)
    if (!target) return
    const pts = parseCoords(target.coords)
    if (pts.length < 3) return
    target.coords = serializePoints(shiftPoints(pts, delta.dx, delta.dy))
    isDirty.value = true
  }

  function movePlots(plotNumbers: number[], delta: { dx: number; dy: number }): void {
    if (!plotNumbers || plotNumbers.length === 0) return
    const numSet = new Set(plotNumbers)
    for (const p of plots.value) {
      if (numSet.has(p.plot_number)) {
        const pts = parseCoords(p.coords)
        if (pts.length >= 3) {
          p.coords = serializePoints(shiftPoints(pts, delta.dx, delta.dy))
        }
      }
    }
    isDirty.value = true
  }

  function duplicatePlots(plotNumbers: number[], offset = { dx: 0.02, dy: 0.02 }): PlotItem[] {
    if (!plotNumbers || plotNumbers.length === 0) return []
    const numSet = new Set(plotNumbers)
    let maxNum = plots.value.reduce((acc, cur) => Math.max(acc, cur.plot_number), 0)
    const newPlots: PlotItem[] = []

    for (const p of plots.value) {
      if (numSet.has(p.plot_number)) {
        const pts = parseCoords(p.coords)
        if (pts.length < 3) continue
        const shifted = shiftPoints(pts, offset.dx, offset.dy)
        const cloned: PlotItem = {
          plot_number: ++maxNum,
          coords: serializePoints(shifted),
          is_control: p.is_control,
          treatment: p.treatment,
          dose: p.dose,
          metrics: {},
        }
        newPlots.push(cloned)
      }
    }
    plots.value.push(...newPlots)
    selectedPlotNumbers.value = newPlots.map((p) => p.plot_number)
    isDirty.value = true
    return newPlots
  }

  function copyPlotsToClipboard(): boolean {
    if (plots.value.length === 0) return false
    try {
      const json = JSON.stringify(plots.value, null, 2)
      navigator.clipboard.writeText(json)
      return true
    } catch {
      return false
    }
  }

  async function pastePlotsFromClipboard(offset = { dx: 0.02, dy: 0.02 }): Promise<number> {
    try {
      const text = await navigator.clipboard.readText()
      const raw = JSON.parse(text)
      if (!Array.isArray(raw) || raw.length === 0) return 0
      let maxNum = plots.value.reduce((acc, cur) => Math.max(acc, cur.plot_number), 0)
      let added = 0
      for (const item of raw) {
        if (!item.coords) continue
        const pts = parseCoords(item.coords)
        if (pts.length < 3) continue
        const shifted = shiftPoints(pts, offset.dx, offset.dy)
        plots.value.push({
          plot_number: ++maxNum,
          coords: serializePoints(shifted),
          is_control: Boolean(item.is_control),
          treatment: item.treatment || '',
          dose: item.dose || '',
          metrics: {},
        })
        added++
      }
      if (added > 0) isDirty.value = true
      return added
    } catch {
      return 0
    }
  }

  function importPlotsFromExternal(externalPlots: PlotItem[], mode: 'replace' | 'append' = 'append'): number {
    if (!Array.isArray(externalPlots) || externalPlots.length === 0) return 0
    if (mode === 'replace') {
      plots.value = []
    }
    let maxNum = mode === 'replace' ? 0 : plots.value.reduce((acc, cur) => Math.max(acc, cur.plot_number), 0)
    let count = 0
    for (const p of externalPlots) {
      const pts = parseCoords(p.coords)
      if (pts.length < 3) continue
      plots.value.push({
        plot_number: ++maxNum,
        coords: serializePoints(pts),
        is_control: Boolean(p.is_control),
        treatment: p.treatment || '',
        dose: p.dose || '',
        metrics: {},
      })
      count++
    }
    if (count > 0) isDirty.value = true
    return count
  }

  function updateGridScale(scaleX: number, scaleY?: number): void {
    gridState.value.scaleX = Math.max(0.05, Math.min(1, scaleX))
    gridState.value.scaleY = Math.max(0.05, Math.min(1, scaleY !== undefined ? scaleY : scaleX))
    gridState.value.marginRatio = Number(((1 - gridState.value.scaleX) / 2).toFixed(3))
  }

  function updateGridPadding(padding: number): void {
    gridState.value.paddingRatio = Math.max(0, Math.min(0.25, padding))
  }

  function updateGridOffset(offsetX: number, offsetY: number): void {
    gridState.value.offsetX = Math.max(-0.25, Math.min(0.25, offsetX))
    gridState.value.offsetY = Math.max(-0.25, Math.min(0.25, offsetY))
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
        is_control: true,
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
    selectedPlotNumbers,
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
    updatePlotTreatments,
    updatePlotPoints,
    deletePlot,
    deletePlots,
    clearAllPlots,
    selectPlots,
    togglePlotSelection,
    clearPlotSelection,
    startGridMode,
    closeGridMode,
    updateGridCorner,
    updateGridCorners,
    moveGrid,
    detectMarkers,
    computeGridPlots,
    confirmBatchGenerate,
    updateGridScale,
    updateGridPadding,
    updateGridOffset,
    toggleExcludeGridCell,
    clearExcludedGridCells,
    duplicatePlot,
    duplicatePlots,
    duplicateAllPlots,
    movePlot,
    movePlots,
    copyPlotsToClipboard,
    pastePlotsFromClipboard,
    importPlotsFromExternal,
    setScenario,
    currentScenario,
  }
}
