<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { AlertTriangle, BarChart2, Maximize2, SlidersHorizontal } from '@lucide/vue'
import type { PlotItem } from '@/lib/usePlots'
import type {
  AlgorithmStatRow,
  OutlierAlert,
  PlotsStatisticsBatch,
  StatisticalTestResult,
} from '@/lib/usePlotsStatistics'

export interface ChartFormulaOption {
  id: string
  label?: string
}

const props = withDefaults(
  defineProps<{
    statistics: PlotsStatisticsBatch
    plots: PlotItem[]
    allowedFormulas: ChartFormulaOption[]
    currentFormula: string
    selectedPlotNumbers: number[]
    getPlotColor: (plot: PlotItem) => string
    expanded?: boolean
  }>(),
  {
    expanded: false,
  }
)

const emit = defineEmits<{
  (e: 'select-plots', plotNumbers: number[]): void
  (e: 'open-expand'): void
}>()

// 圖表顯示模式：長條圖（含 ±SD 誤差線與散點）或箱型圖
const chartMode = ref<'bar' | 'box'>('bar')

// 圖表所選光譜指標：跟隨右側地圖切換，若為 rgb 則預設第一項適用光譜
const chartFormula = ref<string>('')

function resolveDefaultFormula(): string {
  const allowedIds = props.allowedFormulas.map((f) => f.id)
  if (props.currentFormula && allowedIds.includes(props.currentFormula)) {
    return props.currentFormula
  }
  return allowedIds[0] || 'VARI'
}

watch(
  [() => props.currentFormula, () => props.allowedFormulas],
  () => {
    const allowedIds = props.allowedFormulas.map((f) => f.id)
    if (props.currentFormula && allowedIds.includes(props.currentFormula)) {
      chartFormula.value = props.currentFormula
    } else if (!allowedIds.includes(chartFormula.value)) {
      chartFormula.value = resolveDefaultFormula()
    }
  },
  { immediate: true }
)

const plotItemMap = computed(() => {
  const map = new Map<number, PlotItem>()
  for (const p of props.plots) {
    map.set(p.plot_number, p)
  }
  return map
})

const plotStatsMap = computed(() => {
  const map = new Map<number, number | null>()
  const fid = chartFormula.value
  for (const entry of props.statistics.plots) {
    const row = entry.algorithms.find((a) => a.id === fid)
    map.set(entry.plot_number, row?.index_mean ?? null)
  }
  return map
})

const currentTest = computed<StatisticalTestResult | null>(() => {
  return props.statistics.statistical_tests?.[chartFormula.value] ?? null
})

const currentOutliers = computed<OutlierAlert[]>(() => {
  return props.statistics.outliers?.[chartFormula.value] ?? []
})

const outlierPlotSet = computed(() => new Set(currentOutliers.value.map((o) => o.plot_number)))

interface ChartPoint {
  plotNumber: number
  value: number
  isOutlier: boolean
  isSelected: boolean
  jitterOffset: number
}

interface ChartGroupBar {
  key: string
  label: string
  shortLabel: string
  isControl: boolean
  color: string
  plotNumbers: number[]
  replicateCount: number
  mean: number | null
  std: number | null
  cvPct: number | null
  min: number | null
  q1: number | null
  median: number | null
  q3: number | null
  max: number | null
  tukeyLetter: string | null
  points: ChartPoint[]
}

function getAlgoRow(algorithms: AlgorithmStatRow[], fid: string): AlgorithmStatRow | undefined {
  return algorithms.find((a) => a.id === fid)
}

function truncateLabel(label: string, maxLen: number): string {
  return label.length > maxLen ? `${label.slice(0, maxLen - 1)}…` : label
}

const chartGroups = computed<ChartGroupBar[]>(() => {
  const fid = chartFormula.value
  const maxLabelLen = props.expanded ? 14 : 8
  return props.statistics.treatment_groups.map((group) => {
    const algo = getAlgoRow(group.algorithms, fid)
    const firstPlot = group.plot_numbers
      .map((num) => plotItemMap.value.get(num))
      .find((p): p is PlotItem => Boolean(p))
    const color = group.is_control
      ? '#94a3b8'
      : firstPlot
        ? props.getPlotColor(firstPlot)
        : '#10b981'

    const rawPoints = group.plot_numbers
      .map((num) => ({
        plotNumber: num,
        value: plotStatsMap.value.get(num) ?? null,
      }))
      .filter((item): item is { plotNumber: number; value: number } => item.value !== null)

    // 均勻微幅水平錯開散點，避免同數值重複小區重疊難以點擊
    const count = rawPoints.length
    const points: ChartPoint[] = rawPoints.map((pt, idx) => {
      const normalized = count <= 1 ? 0 : idx / (count - 1) - 0.5
      return {
        plotNumber: pt.plotNumber,
        value: pt.value,
        isOutlier: outlierPlotSet.value.has(pt.plotNumber),
        isSelected: props.selectedPlotNumbers.includes(pt.plotNumber),
        jitterOffset: normalized * 0.42,
      }
    })

    const tukeyLetter =
      algo?.tukey_group ?? currentTest.value?.group_letters?.[group.key] ?? null

    return {
      key: group.key,
      label: group.label,
      shortLabel: truncateLabel(group.label, maxLabelLen),
      isControl: group.is_control,
      color,
      plotNumbers: group.plot_numbers,
      replicateCount: algo?.replicate_count ?? rawPoints.length,
      mean: algo?.index_mean ?? null,
      std: algo?.index_std ?? null,
      cvPct: algo?.index_cv_pct ?? null,
      min: algo?.index_min ?? (rawPoints.length > 0 ? Math.min(...rawPoints.map((p) => p.value)) : null),
      q1: algo?.index_q1 ?? null,
      median: algo?.index_median ?? null,
      q3: algo?.index_q3 ?? null,
      max: algo?.index_max ?? (rawPoints.length > 0 ? Math.max(...rawPoints.map((p) => p.value)) : null),
      tukeyLetter,
      points,
    }
  })
})

const hasPlottableData = computed(() => chartGroups.value.some((g) => g.mean !== null))

// SVG 幾何與座標軸比例尺計算
const svgWidth = computed(() => {
  const minPerGroup = props.expanded ? 110 : 68
  const baseWidth = props.expanded ? 680 : 320
  return Math.max(baseWidth, chartGroups.value.length * minPerGroup + 64)
})
const svgHeight = computed(() => (props.expanded ? 300 : 210))
const padLeft = 46
const padRight = 14
const padTop = 26
const padBottom = computed(() => (props.expanded ? 48 : 42))
const plotWidth = computed(() => Math.max(100, svgWidth.value - padLeft - padRight))
const plotHeight = computed(() => Math.max(80, svgHeight.value - padTop - padBottom.value))

const yDomain = computed<[number, number]>(() => {
  const candidates: number[] = [0]
  for (const g of chartGroups.value) {
    if (g.mean !== null) {
      candidates.push(g.mean)
      if (g.std !== null) {
        candidates.push(g.mean + g.std, g.mean - g.std)
      }
    }
    if (g.min !== null) candidates.push(g.min)
    if (g.max !== null) candidates.push(g.max)
    for (const pt of g.points) {
      candidates.push(pt.value)
    }
  }
  let lo = Math.min(...candidates)
  let hi = Math.max(...candidates)
  if (Math.abs(hi - lo) < 1e-6) {
    lo -= 0.1
    hi += 0.1
  }
  const span = hi - lo
  // 上方多留空間擺放 Tukey HSD 顯著性字母
  return [lo - span * 0.08, hi + span * 0.22]
})

function yScale(val: number): number {
  const [lo, hi] = yDomain.value
  const ratio = (val - lo) / (hi - lo)
  return padTop + plotHeight.value * (1 - ratio)
}

const yTicks = computed<number[]>(() => {
  const [lo, hi] = yDomain.value
  const steps = 4
  const ticks: number[] = []
  for (let i = 0; i <= steps; i++) {
    ticks.push(lo + ((hi - lo) * i) / steps)
  }
  return ticks
})

const zeroLineY = computed<number | null>(() => {
  const [lo, hi] = yDomain.value
  if (lo <= 0 && hi >= 0) {
    return yScale(0)
  }
  return null
})

function groupCenterX(index: number): number {
  const count = Math.max(1, chartGroups.value.length)
  const slot = plotWidth.value / count
  return padLeft + slot * (index + 0.5)
}

const barWidth = computed(() => {
  const count = Math.max(1, chartGroups.value.length)
  const slot = plotWidth.value / count
  return Math.max(18, Math.min(props.expanded ? 54 : 34, slot * 0.52))
})

function groupTopAnchorY(g: ChartGroupBar): number {
  const tops: number[] = []
  if (g.mean !== null) {
    tops.push(g.std !== null ? g.mean + g.std : g.mean)
  }
  if (g.max !== null) tops.push(g.max)
  for (const pt of g.points) tops.push(pt.value)
  if (tops.length === 0) return padTop + 10
  return Math.max(padTop + 10, yScale(Math.max(...tops)) - 8)
}

function handlePointClick(plotNumber: number, event: MouseEvent) {
  event.stopPropagation()
  if (event.ctrlKey || event.metaKey || event.shiftKey) {
    const next = props.selectedPlotNumbers.includes(plotNumber)
      ? props.selectedPlotNumbers.filter((n) => n !== plotNumber)
      : [...props.selectedPlotNumbers, plotNumber]
    emit('select-plots', next)
  } else {
    emit('select-plots', [plotNumber])
  }
}

function handleGroupSelect(plotNumbers: number[]) {
  if (plotNumbers.length > 0) {
    emit('select-plots', [...plotNumbers])
  }
}

function formatPValue(p: number | null | undefined): string {
  if (p === null || p === undefined) return '—'
  if (p < 0.001) return '< 0.001'
  return p.toFixed(4)
}

function formatNum(val: number | null | undefined, digits = 3): string {
  if (val === null || val === undefined || Number.isNaN(val)) return '—'
  return val.toFixed(digits)
}
</script>

<template>
  <div
    :data-testid="expanded ? 'spectral-group-chart-expanded' : 'spectral-group-chart'"
    class="rounded-xl border border-border/60 bg-background/80 p-2.5 space-y-2.5"
  >
    <!-- 頂部控制列：指標切換、長條圖/箱型圖切換、放大彈窗 -->
    <div class="flex flex-wrap items-center justify-between gap-1.5">
      <div class="flex flex-wrap items-center gap-1">
        <button
          v-for="f in allowedFormulas"
          :key="f.id"
          type="button"
          :data-testid="`chart-formula-${f.id}`"
          class="rounded-md px-2 py-0.5 text-[11px] font-mono font-semibold transition-colors cursor-pointer"
          :class="
            chartFormula === f.id
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground'
          "
          @click="chartFormula = f.id"
        >
          {{ f.id }}
        </button>
      </div>

      <div class="flex items-center gap-1">
        <div class="inline-flex rounded-md border border-border/60 bg-muted/30 p-0.5">
          <button
            type="button"
            data-testid="chart-mode-bar"
            class="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium transition-colors cursor-pointer"
            :class="
              chartMode === 'bar'
                ? 'bg-background text-foreground shadow-2xs'
                : 'text-muted-foreground hover:text-foreground'
            "
            title="長條圖（均值 ± SD 與個別小區散點）"
            @click="chartMode = 'bar'"
          >
            <BarChart2 class="size-3" />
            <span>長條</span>
          </button>
          <button
            type="button"
            data-testid="chart-mode-box"
            class="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium transition-colors cursor-pointer"
            :class="
              chartMode === 'box'
                ? 'bg-background text-foreground shadow-2xs'
                : 'text-muted-foreground hover:text-foreground'
            "
            title="箱型圖（Q1 / 中位數 / Q3 與極值）"
            @click="chartMode = 'box'"
          >
            <SlidersHorizontal class="size-3" />
            <span>箱型</span>
          </button>
        </div>

        <Button
          v-if="!expanded"
          type="button"
          variant="ghost"
          size="sm"
          data-testid="chart-expand-button"
          class="h-6 w-6 p-0 text-muted-foreground hover:text-foreground cursor-pointer"
          title="放大檢視完整統計圖表與 Tukey 成對比較表"
          aria-label="放大檢視統計圖表"
          @click="emit('open-expand')"
        >
          <Maximize2 class="size-3.5" />
        </Button>
      </div>
    </div>

    <!-- 單因子 ANOVA / Tukey HSD 檢定摘要橫幅 -->
    <div
      v-if="currentTest"
      data-testid="spectral-anova-banner"
      class="flex flex-wrap items-center justify-between gap-1.5 rounded-lg border px-2 py-1.5 text-[11px]"
      :class="
        currentTest.status === 'ok' && currentTest.significant
          ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
          : 'border-border/60 bg-muted/25 text-muted-foreground'
      "
    >
      <div class="flex items-center gap-1.5 min-w-0">
        <Badge
          v-if="currentTest.status === 'ok'"
          :variant="currentTest.significant ? 'default' : 'secondary'"
          class="text-[10px] px-1.5 py-0 shrink-0"
        >
          {{ currentTest.significant ? 'ANOVA 顯著' : '無顯著差異' }}
        </Badge>
        <Badge v-else variant="outline" class="text-[10px] px-1.5 py-0 shrink-0">
          檢定略過
        </Badge>
        <span class="truncate" :title="currentTest.message">
          <template v-if="currentTest.status === 'ok'">
            F={{ currentTest.anova_f ?? '—' }}, p {{ formatPValue(currentTest.anova_p) }} · 相同字母無顯著差異
          </template>
          <template v-else>
            {{ currentTest.message }}
          </template>
        </span>
      </div>
    </div>

    <!-- 主 SVG 圖表 -->
    <div v-if="hasPlottableData" class="w-full overflow-x-auto">
      <svg
        :viewBox="`0 0 ${svgWidth} ${svgHeight}`"
        class="w-full h-auto select-none"
        role="img"
        :aria-label="`${chartFormula} 各處理組統計圖表`"
      >
        <!-- 水平格線與 Y 軸刻度 -->
        <g v-for="(tick, idx) in yTicks" :key="idx">
          <line
            :x1="padLeft"
            :x2="svgWidth - padRight"
            :y1="yScale(tick)"
            :y2="yScale(tick)"
            stroke="currentColor"
            stroke-opacity="0.12"
            stroke-dasharray="2 3"
          />
          <text
            :x="padLeft - 6"
            :y="yScale(tick) + 3"
            text-anchor="end"
            class="fill-muted-foreground text-[9px] font-mono"
          >
            {{ tick.toFixed(2) }}
          </text>
        </g>

        <!-- 零基準線 -->
        <line
          v-if="zeroLineY !== null"
          :x1="padLeft"
          :x2="svgWidth - padRight"
          :y1="zeroLineY"
          :y2="zeroLineY"
          stroke="currentColor"
          stroke-opacity="0.35"
          stroke-width="1"
        />

        <!-- 各處理組圖形 -->
        <g v-for="(group, gIdx) in chartGroups" :key="group.key">
          <!-- 模式 A：長條圖 + ±SD 誤差線 -->
          <template v-if="chartMode === 'bar' && group.mean !== null">
            <rect
              :x="groupCenterX(gIdx) - barWidth / 2"
              :y="Math.min(yScale(group.mean), zeroLineY ?? yScale(yDomain[0]))"
              :width="barWidth"
              :height="Math.max(2, Math.abs(yScale(group.mean) - (zeroLineY ?? yScale(yDomain[0]))))"
              :fill="group.color"
              fill-opacity="0.28"
              :stroke="group.color"
              stroke-width="1.5"
              rx="4"
              class="cursor-pointer transition-opacity hover:fill-opacity-45"
              @click="handleGroupSelect(group.plotNumbers)"
            >
              <title>
                {{ group.label }}（n={{ group.replicateCount }}）&#10;均值：{{ formatNum(group.mean, 4) }}&#10;SD：{{ formatNum(group.std, 4) }}&#10;CV%：{{ group.cvPct !== null ? `${group.cvPct}%` : '—' }}
              </title>
            </rect>

            <!-- ±SD 誤差線 -->
            <g v-if="group.std !== null && group.std > 0">
              <line
                :x1="groupCenterX(gIdx)"
                :x2="groupCenterX(gIdx)"
                :y1="yScale(group.mean + group.std)"
                :y2="yScale(group.mean - group.std)"
                stroke="currentColor"
                stroke-opacity="0.7"
                stroke-width="1.3"
              />
              <line
                :x1="groupCenterX(gIdx) - 5"
                :x2="groupCenterX(gIdx) + 5"
                :y1="yScale(group.mean + group.std)"
                :y2="yScale(group.mean + group.std)"
                stroke="currentColor"
                stroke-opacity="0.7"
                stroke-width="1.3"
              />
              <line
                :x1="groupCenterX(gIdx) - 5"
                :x2="groupCenterX(gIdx) + 5"
                :y1="yScale(group.mean - group.std)"
                :y2="yScale(group.mean - group.std)"
                stroke="currentColor"
                stroke-opacity="0.7"
                stroke-width="1.3"
              />
            </g>
          </template>

          <!-- 模式 B：箱型圖（Min-Max 鬚線、Q1-Q3 箱體、中位數線、均值菱形） -->
          <template v-else-if="chartMode === 'box' && group.q1 !== null && group.q3 !== null && group.median !== null">
            <line
              v-if="group.min !== null && group.max !== null"
              :x1="groupCenterX(gIdx)"
              :x2="groupCenterX(gIdx)"
              :y1="yScale(group.max)"
              :y2="yScale(group.min)"
              stroke="currentColor"
              stroke-opacity="0.6"
              stroke-width="1.2"
            />
            <line
              v-if="group.max !== null"
              :x1="groupCenterX(gIdx) - barWidth * 0.25"
              :x2="groupCenterX(gIdx) + barWidth * 0.25"
              :y1="yScale(group.max)"
              :y2="yScale(group.max)"
              stroke="currentColor"
              stroke-opacity="0.6"
              stroke-width="1.2"
            />
            <line
              v-if="group.min !== null"
              :x1="groupCenterX(gIdx) - barWidth * 0.25"
              :x2="groupCenterX(gIdx) + barWidth * 0.25"
              :y1="yScale(group.min)"
              :y2="yScale(group.min)"
              stroke="currentColor"
              stroke-opacity="0.6"
              stroke-width="1.2"
            />
            <rect
              :x="groupCenterX(gIdx) - barWidth / 2"
              :y="yScale(group.q3)"
              :width="barWidth"
              :height="Math.max(2, yScale(group.q1) - yScale(group.q3))"
              :fill="group.color"
              fill-opacity="0.3"
              :stroke="group.color"
              stroke-width="1.5"
              rx="3"
              class="cursor-pointer"
              @click="handleGroupSelect(group.plotNumbers)"
            >
              <title>
                {{ group.label }}（n={{ group.replicateCount }}）&#10;Q1：{{ formatNum(group.q1, 4) }} / 中位數：{{ formatNum(group.median, 4) }} / Q3：{{ formatNum(group.q3, 4) }}
              </title>
            </rect>
            <line
              :x1="groupCenterX(gIdx) - barWidth / 2"
              :x2="groupCenterX(gIdx) + barWidth / 2"
              :y1="yScale(group.median)"
              :y2="yScale(group.median)"
              stroke="currentColor"
              stroke-width="2"
            />
            <polygon
              v-if="group.mean !== null"
              :points="`${groupCenterX(gIdx)},${yScale(group.mean) - 3.5} ${groupCenterX(gIdx) + 3.5},${yScale(group.mean)} ${groupCenterX(gIdx)},${yScale(group.mean) + 3.5} ${groupCenterX(gIdx) - 3.5},${yScale(group.mean)}`"
              fill="currentColor"
              fill-opacity="0.85"
            />
          </template>

          <!-- Tukey HSD 顯著性字母（a / b / ab） -->
          <text
            v-if="group.tukeyLetter"
            :data-testid="`tukey-letter-${group.key}`"
            :x="groupCenterX(gIdx)"
            :y="groupTopAnchorY(group)"
            text-anchor="middle"
            class="fill-foreground text-[11px] font-mono font-bold"
          >
            {{ group.tukeyLetter }}
          </text>

          <!-- 個別小區可點擊散點（離群點以琥珀／紅圈醒目標示） -->
          <g v-for="pt in group.points" :key="pt.plotNumber">
            <circle
              v-if="pt.isSelected || pt.isOutlier"
              :cx="groupCenterX(gIdx) + pt.jitterOffset * barWidth"
              :cy="yScale(pt.value)"
              :r="pt.isSelected ? 7 : 6.5"
              fill="none"
              :stroke="pt.isOutlier ? '#f59e0b' : '#38bdf8'"
              stroke-width="1.8"
              stroke-opacity="0.9"
            />
            <circle
              :data-testid="`chart-point-plot-${pt.plotNumber}`"
              :cx="groupCenterX(gIdx) + pt.jitterOffset * barWidth"
              :cy="yScale(pt.value)"
              :r="pt.isSelected ? 4.5 : pt.isOutlier ? 4.2 : 3.4"
              :fill="pt.isOutlier ? '#f59e0b' : group.color"
              stroke="#09090b"
              stroke-width="1"
              class="cursor-pointer transition-transform"
              @click="handlePointClick(pt.plotNumber, $event)"
            >
              <title>
                #{{ pt.plotNumber }} {{ group.label }}：{{ pt.value.toFixed(4) }}{{ pt.isOutlier ? '（異常離群，點擊定位排查）' : '（點擊定位小區）' }}
              </title>
            </circle>
          </g>

          <!-- X 軸組別名稱與重複數 -->
          <text
            :x="groupCenterX(gIdx)"
            :y="svgHeight - (expanded ? 22 : 18)"
            text-anchor="middle"
            class="fill-foreground text-[10px] font-medium cursor-pointer"
            @click="handleGroupSelect(group.plotNumbers)"
          >
            {{ group.shortLabel }}
          </text>
          <text
            :x="groupCenterX(gIdx)"
            :y="svgHeight - (expanded ? 8 : 6)"
            text-anchor="middle"
            class="fill-muted-foreground text-[9px] font-mono"
          >
            n={{ group.replicateCount }}
          </text>
        </g>
      </svg>
    </div>

    <p v-else class="py-6 text-center text-[11px] text-muted-foreground">
      目前尚無可繪製的處理組統計資料。
    </p>

    <!-- 異常離群小區警示清單（點擊直接選取並定位右側地圖小區） -->
    <div
      v-if="currentOutliers.length > 0"
      data-testid="spectral-outlier-alerts"
      class="rounded-lg border border-amber-500/40 bg-amber-500/10 p-2 space-y-1.5"
    >
      <div class="flex items-center gap-1.5 text-[11px] font-semibold text-amber-700 dark:text-amber-300">
        <AlertTriangle class="size-3.5 shrink-0" />
        <span>異常離群小區警示（{{ currentOutliers.length }} 區 · 僅供複查，未自動剔除）</span>
      </div>
      <div class="space-y-1">
        <button
          v-for="item in currentOutliers"
          :key="`${item.formula_id}-${item.plot_number}`"
          type="button"
          :data-testid="`outlier-alert-plot-${item.plot_number}`"
          class="w-full text-left rounded-md border border-amber-500/30 bg-background/80 hover:bg-amber-500/15 px-2 py-1.5 transition-colors cursor-pointer"
          @click="emit('select-plots', [item.plot_number])"
        >
          <div class="flex items-center justify-between gap-2 text-[11px]">
            <span class="font-semibold text-foreground">
              #{{ item.plot_number }} · {{ item.group_label }}
            </span>
            <span class="font-mono text-[10px] text-amber-700 dark:text-amber-300 shrink-0">
              {{ item.value.toFixed(4) }}（點擊定位）
            </span>
          </div>
          <p class="text-[10px] text-muted-foreground leading-snug mt-0.5">
            {{ item.reason }}
          </p>
        </button>
      </div>
    </div>

    <!-- 放大模式專屬：Tukey HSD 成對比較明細表 -->
    <div
      v-if="expanded && currentTest && currentTest.pairwise.length > 0"
      data-testid="spectral-tukey-pairwise-table"
      class="space-y-1.5 pt-1"
    >
      <h4 class="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
        Tukey HSD 組間成對比較（α = {{ currentTest.alpha }}）
      </h4>
      <div class="overflow-x-auto rounded-lg border border-border/60">
        <table class="w-full text-left text-[11px] tabular-nums">
          <thead class="bg-muted/30 text-muted-foreground">
            <tr>
              <th scope="col" class="px-2.5 py-1.5 font-medium">比較組別</th>
              <th scope="col" class="px-2.5 py-1.5 text-right font-medium">均值差</th>
              <th scope="col" class="px-2.5 py-1.5 text-right font-medium">p-value</th>
              <th scope="col" class="px-2.5 py-1.5 text-right font-medium">顯著性</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(pair, idx) in currentTest.pairwise"
              :key="idx"
              class="border-t border-border/40"
            >
              <td class="px-2.5 py-1.5 font-medium text-foreground">
                {{ pair.label_a }} vs {{ pair.label_b }}
              </td>
              <td class="px-2.5 py-1.5 text-right font-mono">
                {{ pair.mean_diff >= 0 ? '+' : '' }}{{ pair.mean_diff.toFixed(4) }}
              </td>
              <td class="px-2.5 py-1.5 text-right font-mono">
                {{ formatPValue(pair.p_value) }}
              </td>
              <td class="px-2.5 py-1.5 text-right">
                <Badge
                  :variant="pair.significant ? 'default' : 'secondary'"
                  class="text-[10px] px-1.5 py-0"
                >
                  {{ pair.significant ? '顯著 *' : '不顯著' }}
                </Badge>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
