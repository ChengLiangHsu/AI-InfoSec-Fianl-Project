<script setup lang="ts">
import { computed } from 'vue'
import { computed, ref } from 'vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Spinner } from '@/components/ui/spinner'
import { BarChart3, RefreshCw, X } from '@lucide/vue'
import { AlertTriangle, BarChart3, RefreshCw, X } from '@lucide/vue'
import SpectralGroupChart from '@/components/SpectralGroupChart.vue'
import type { PlotItem } from '@/lib/usePlots'
import type { MeanRgb } from '@/lib/useRegionStatistics'
import type {
  AlgorithmStatRow,
  PlotStatisticsEntry,
  PlotsStatisticsBatch,
} from '@/lib/usePlotsStatistics'

export interface FormulaMeta {
  id: string
  label?: string
  badge?: string
  expr?: string
  help?: string
  limitation?: string
  range?: [number, number]
}

const props = defineProps<{
  plots: PlotItem[]
  selectedPlotNumbers: number[]
  currentFormula: string
  allowedFormulas: FormulaMeta[]
  getPlotColor: (plot: PlotItem) => string
  statistics: PlotsStatisticsBatch | null
  loading: boolean
  error: string
}>()

const emit = defineEmits<{
  (e: 'select-plots', plotNumbers: number[]): void
  (e: 'refresh'): void
}>()

const allowedIds = computed(() => props.allowedFormulas.map((f) => f.id))
const formulaMetaMap = computed(() => new Map(props.allowedFormulas.map((f) => [f.id, f])))

const plotStatsMap = computed(() => {
  const map = new Map<number, PlotStatisticsEntry>()
  for (const entry of props.statistics?.plots ?? []) {
    map.set(entry.plot_number, entry)
  }
  return map
})

const ckBaselineMap = computed(() => {
  const map = new Map<string, number | null>()
  for (const row of props.statistics?.control_baseline?.algorithms ?? []) {
    map.set(row.id, row.index_mean)
  }
  return map
})

const selectedPlotEntries = computed<PlotStatisticsEntry[]>(() => {
  return props.selectedPlotNumbers
    .map((num) => plotStatsMap.value.get(num))
    .filter((entry): entry is PlotStatisticsEntry => Boolean(entry))
})

const viewMode = computed<'whole' | 'single' | 'multi'>(() => {
  if (props.selectedPlotNumbers.length === 0) return 'whole'
  if (props.selectedPlotNumbers.length === 1) return 'single'
  return 'multi'
})

const scopeBadgeLabel = computed(() => {
  if (props.selectedPlotNumbers.length === 0) {
    return `全田區（${props.plots.length} 區）`
  }
  if (props.selectedPlotNumbers.length === 1) {
    const p = props.plots.find((item) => item.plot_number === props.selectedPlotNumbers[0])
    return p ? formatPlotShortLabel(p) : `#${props.selectedPlotNumbers[0]}`
  }
  return `已選 ${props.selectedPlotNumbers.length} 區比較`
})

function formatPlotShortLabel(plot: Pick<PlotItem, 'plot_number' | 'is_control' | 'treatment' | 'dose'>): string {
  if (plot.is_control) return `#${plot.plot_number} CK`
  const parts = [plot.treatment, plot.dose].filter(Boolean)
  return parts.length > 0 ? `#${plot.plot_number} ${parts.join(' ')}` : `#${plot.plot_number}`
}

function getAlgoRow(algorithms: AlgorithmStatRow[], formulaId: string): AlgorithmStatRow | undefined {
  return algorithms.find((a) => a.id === formulaId)
}

function formatIndex(val: number | null | undefined): string {
  if (val === null || val === undefined || Number.isNaN(val)) return '無有效值'
  return val.toFixed(4)
}

function formatDeltaVsCk(
  val: number | null | undefined,
  formulaId: string,
  isControl: boolean
): { text: string; tone: 'neutral' | 'positive' | 'negative' } {
  if (isControl) return { text: '基準 (CK)', tone: 'neutral' }
  const ck = ckBaselineMap.value.get(formulaId)
  if (val === null || val === undefined || ck === null || ck === undefined) {
    return { text: '—', tone: 'neutral' }
  }
  const diff = val - ck
  const sign = diff > 0 ? '+' : ''
  const pct = Math.abs(ck) > 1e-6 ? ` (${sign}${((diff / Math.abs(ck)) * 100).toFixed(1)}%)` : ''
  const tone = Math.abs(diff) < 1e-4 ? 'neutral' : diff > 0 ? 'positive' : 'negative'
  return { text: `${sign}${diff.toFixed(4)}${pct}`, tone }
}

function rgbText(rgb: MeanRgb): string {
  return rgb ? rgb.map((v) => v.toFixed(1)).join(' / ') : '—'
}

function rgbColor(rgb: MeanRgb): string {
  return rgb ? `rgb(${rgb.join(',')})` : 'transparent'
}

function formulaTooltip(id: string): string {
  const meta = formulaMetaMap.value.get(id)
  if (!meta) return `${id}（純 RGB 指標）`
  return [
    meta.label || meta.id,
    meta.expr ? `純 RGB 公式：${meta.expr}` : '',
    meta.limitation ? `限制：${meta.limitation}` : '',
  ]
    .filter(Boolean)
    .join('\n')
}

function handlePlotChipClick(plotNumber: number, e: MouseEvent) {
  const isModifier = e.ctrlKey || e.metaKey || e.shiftKey
  if (isModifier) {
    const next = props.selectedPlotNumbers.includes(plotNumber)
      ? props.selectedPlotNumbers.filter((n) => n !== plotNumber)
      : [...props.selectedPlotNumbers, plotNumber]
    emit('select-plots', next)
  } else {
    emit('select-plots', [plotNumber])
  }
}

function removeSelectedPlot(plotNumber: number) {
  emit(
    'select-plots',
    props.selectedPlotNumbers.filter((n) => n !== plotNumber)
  )
}

// 控制統計圖表放大檢視彈窗狀態
const isChartDialogOpen = ref(false)

function formatStdCv(row: AlgorithmStatRow | undefined): string {
  if (!row || row.index_std === null || row.index_std === undefined) return ''
  const stdStr = `±${row.index_std.toFixed(4)}`
  const cvStr =
    row.index_cv_pct !== null && row.index_cv_pct !== undefined
      ? ` · CV ${row.index_cv_pct.toFixed(1)}%`
      : ''
  return `${stdStr}${cvStr}`
}
</script>

<template>
  <section data-testid="spectral-stats-panel" aria-label="光譜演算法數值資訊"
    class="flex h-full min-h-0 flex-col rounded-2xl border border-border/70 bg-card text-card-foreground shadow-xs overflow-hidden">
    <!-- 標頭 -->
    <header
      class="flex items-center justify-between gap-2 px-3.5 py-2.5 border-b border-border/50 bg-muted/20 shrink-0">
      <div class="flex items-center gap-2 min-w-0">
        <div class="flex size-7 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
          <BarChart3 class="size-4" />
        </div>
        <div class="min-w-0">
          <h2 class="text-sm font-semibold text-foreground truncate">
            光譜演算法數值資訊
          </h2>
          <p class="text-[11px] text-muted-foreground truncate">
            {{ scopeBadgeLabel }}
          </p>
        </div>
      </div>

      <Button type="button" variant="ghost" size="sm"
        class="h-7 w-7 p-0 text-muted-foreground hover:text-foreground cursor-pointer shrink-0" :disabled="loading"
        title="重新計算光譜統計" aria-label="重新計算光譜統計" @click="emit('refresh')">
        <RefreshCw class="size-3.5" :class="{ 'animate-spin': loading }" />
      </Button>
    </header>

    <!-- 小區快速選取列（與右側正射圖雙向同步） -->
    <div class="px-3 py-2 border-b border-border/40 bg-muted/10 shrink-0 space-y-1.5">
      <div class="flex items-center justify-between text-[11px] text-muted-foreground">
        <span>分析對象（與右圖同步）</span>
        <span class="text-[10px] opacity-80">點擊單選 · Ctrl/Shift 多選</span>
      </div>
      <div class="flex flex-wrap gap-1 max-h-20 overflow-y-auto pr-0.5">
        <button type="button" data-testid="stats-plot-chip-all"
          class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium transition-colors cursor-pointer"
          :class="selectedPlotNumbers.length === 0
              ? 'border-primary bg-primary text-primary-foreground'
              : 'border-border/70 bg-background text-muted-foreground hover:bg-accent hover:text-foreground'
            " @click="emit('select-plots', [])">
          全田區
        </button>

        <button v-for="plot in plots" :key="plot.plot_number" type="button"
          :data-testid="`stats-plot-chip-${plot.plot_number}`"
          class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium transition-colors cursor-pointer"
          :class="selectedPlotNumbers.includes(plot.plot_number)
              ? 'border-primary bg-primary/15 text-foreground ring-1 ring-primary/40'
              : 'border-border/70 bg-background text-muted-foreground hover:bg-accent hover:text-foreground'
            " @click="handlePlotChipClick(plot.plot_number, $event)">
          <span class="size-2 rounded-full shrink-0" :style="{ backgroundColor: getPlotColor(plot) }" />
          <span class="truncate max-w-[110px]">{{ formatPlotShortLabel(plot) }}</span>
        </button>
      </div>
    </div>

    <!-- 數值主內容 -->
    <div class="flex-1 min-h-0 overflow-y-auto p-3.5 space-y-4 text-xs">
      <div v-if="loading" role="status" class="flex items-center justify-center gap-2 py-10 text-muted-foreground">
        <Spinner class="size-4 animate-spin text-primary" />
        <span>正在計算各小區光譜數值...</span>
      </div>

      <div v-else-if="error" role="alert"
        class="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-destructive space-y-2">
        <p>{{ error }}</p>
        <Button type="button" size="sm" variant="outline" class="h-7 text-xs cursor-pointer" @click="emit('refresh')">
          重新計算
        </Button>
      </div>

      <template v-else-if="statistics && statistics.field_summary">
        <!-- 內嵌處理組統計圖表（長條圖 ±SD / 箱型圖 / Tukey 字母 / 離群小區警示） -->
        <SpectralGroupChart v-if="statistics.treatment_groups.length > 0 && allowedFormulas.length > 0"
          :statistics="statistics" :plots="plots" :allowed-formulas="allowedFormulas" :current-formula="currentFormula"
          :selected-plot-numbers="selectedPlotNumbers" :get-plot-color="getPlotColor"
          @select-plots="emit('select-plots', $event)" @open-expand="isChartDialogOpen = true" />

        <!-- 模式 1：未選取小區 -> 全田區與各處理組平均概況 -->
        <template v-if="viewMode === 'whole'">
          <div class="rounded-lg border border-border/60 bg-muted/20 p-2.5 space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="font-semibold text-foreground">全田區概況</span>
              <span class="font-mono text-[11px] text-muted-foreground">
                {{ statistics.field_summary.plot_count }} 區 · {{ statistics.field_summary.pixel_count.toLocaleString()
                }} px
              </span>
            </div>
            <div class="flex items-center justify-between text-[11px] text-muted-foreground">
              <span>原圖平均 RGB</span>
              <span class="font-mono text-foreground inline-flex items-center gap-1.5">
                <span class="inline-block size-2.5 rounded-sm border border-border/60"
                  :style="{ backgroundColor: rgbColor(statistics.field_summary.rgb_mean) }" />
                {{ rgbText(statistics.field_summary.rgb_mean) }}
              </span>
            </div>
          </div>

          <div class="space-y-2">
            <h3 class="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              適用光譜指標（全田區均值 vs CK 基準）
            </h3>
            <div class="overflow-x-auto rounded-lg border border-border/60">
              <table class="w-full text-left text-[11px] tabular-nums">
                <thead class="bg-muted/30 text-muted-foreground">
                  <tr>
                    <th scope="col" class="px-2.5 py-1.5 font-medium">光譜指標</th>
                    <th scope="col" class="px-2.5 py-1.5 text-right font-medium">全田均值</th>
                    <th scope="col" class="px-2.5 py-1.5 text-right font-medium">CK 基準</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="fid in allowedIds" :key="fid" class="border-t border-border/40"
                    :class="{ 'bg-primary/10': currentFormula === fid }">
                    <th scope="row" class="px-2.5 py-2 font-semibold text-foreground" :title="formulaTooltip(fid)">
                      {{ fid }}
                    </th>
                    <td class="px-2.5 py-2 text-right font-mono">
                      {{ formatIndex(getAlgoRow(statistics.field_summary.algorithms, fid)?.index_mean) }}
                    </td>
                    <td class="px-2.5 py-2 text-right font-mono text-muted-foreground">
                      {{ formatIndex(ckBaselineMap.get(fid)) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-if="statistics.treatment_groups.length > 0" class="space-y-2">
            <h3 class="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              各處理組平均比較
            </h3>
            <div class="space-y-2">
              <div v-for="group in statistics.treatment_groups" :key="group.key"
                class="rounded-lg border border-border/60 bg-background p-2.5 space-y-1.5">
                <div class="flex items-center justify-between gap-2">
                  <span class="font-semibold text-foreground truncate">{{ group.label }}</span>
                  <Badge variant="outline" class="text-[10px] shrink-0">
                    {{ group.plot_count }} 區
                  </Badge>
                </div>
                <div class="grid grid-cols-1 gap-1 pt-0.5">
                  <div v-for="fid in allowedIds" :key="fid"
                    class="flex items-center justify-between text-[11px] rounded px-1.5 py-0.5"
                    :class="{ 'bg-primary/10': currentFormula === fid }">
                    <span class="font-mono font-medium text-muted-foreground">{{ fid }}</span>
                    <div class="flex items-center gap-2 font-mono">
                      <span class="text-foreground font-semibold">
                        {{ formatIndex(getAlgoRow(group.algorithms, fid)?.index_mean) }}
                      </span>
                      <span class="font-mono font-medium text-muted-foreground inline-flex items-center gap-1">
                        <span>{{ fid }}</span>
                        <Badge v-if="getAlgoRow(group.algorithms, fid)?.tukey_group" variant="secondary"
                          class="text-[9px] px-1 py-0 font-mono" title="Tukey HSD 顯著性分群字母（相同字母表示組間無顯著差異）">
                          {{ getAlgoRow(group.algorithms, fid)?.tukey_group }}
                        </Badge>
                        <AlertTriangle v-if="(getAlgoRow(group.algorithms, fid)?.outlier_plot_numbers?.length ?? 0) > 0"
                          class="size-3 text-amber-500"
                          :title="`組內發現離群小區：#${getAlgoRow(group.algorithms, fid)?.outlier_plot_numbers?.join(', #')}`" />
                      </span>
                      <div class="flex flex-col items-end font-mono">
                        <div class="flex items-center gap-2">
                          <span class="text-foreground font-semibold">
                            {{ formatIndex(getAlgoRow(group.algorithms, fid)?.index_mean) }}
                          </span>
                          <span class="text-[10px]" :class="{
                            'text-emerald-600 dark:text-emerald-400': formatDeltaVsCk(getAlgoRow(group.algorithms, fid)?.index_mean, fid, group.is_control).tone === 'positive',
                            'text-rose-600 dark:text-rose-400': formatDeltaVsCk(getAlgoRow(group.algorithms, fid)?.index_mean, fid, group.is_control).tone === 'negative',
                            'text-muted-foreground': formatDeltaVsCk(getAlgoRow(group.algorithms, fid)?.index_mean, fid, group.is_control).tone === 'neutral',
                          }">
                            {{ formatDeltaVsCk(getAlgoRow(group.algorithms, fid)?.index_mean, fid,
                            group.is_control).text }}
                          </span>
                        </div>
                        <span class="text-[10px]" :class="{
                          'text-emerald-600 dark:text-emerald-400': formatDeltaVsCk(getAlgoRow(group.algorithms, fid)?.index_mean, fid, group.is_control).tone === 'positive',
                          'text-rose-600 dark:text-rose-400': formatDeltaVsCk(getAlgoRow(group.algorithms, fid)?.index_mean, fid, group.is_control).tone === 'negative',
                          'text-muted-foreground': formatDeltaVsCk(getAlgoRow(group.algorithms, fid)?.index_mean, fid, group.is_control).tone === 'neutral',
                        }" v-if="formatStdCv(getAlgoRow(group.algorithms, fid))"
                          class="text-[9px] text-muted-foreground/85">
                          {{ formatDeltaVsCk(getAlgoRow(group.algorithms, fid)?.index_mean, fid, group.is_control).text
                          }}
                          {{ formatStdCv(getAlgoRow(group.algorithms, fid)) }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        </template>

        <!-- 模式 2：單選 1 個小區 -> 詳情 + 相對 CK 差異 -->
        <template v-else-if="viewMode === 'single' && selectedPlotEntries[0]">
          <div class="rounded-lg border border-border/60 bg-muted/20 p-2.5 space-y-1.5">
            <div class="flex items-center justify-between gap-2">
              <div class="flex items-center gap-1.5 min-w-0">
                <Badge variant="secondary" class="font-mono text-[11px]">
                  #{{ selectedPlotEntries[0].plot_number }}
                </Badge>
                <span class="font-semibold text-foreground truncate">
                  {{
                    selectedPlotEntries[0].is_control
                      ? '對照組 (CK)'
                      : [selectedPlotEntries[0].treatment, selectedPlotEntries[0].dose].filter(Boolean).join(' ') ||
                      '未分類處理組'
                  }}
                </span>
              </div>
              <span class="font-mono text-[11px] text-muted-foreground shrink-0">
                {{ selectedPlotEntries[0].pixel_count.toLocaleString() }} px
              </span>
            </div>
            <div class="flex items-center justify-between text-[11px] text-muted-foreground">
              <span>原圖平均 R / G / B</span>
              <span class="font-mono text-foreground inline-flex items-center gap-1.5">
                <span class="inline-block size-2.5 rounded-sm border border-border/60"
                  :style="{ backgroundColor: rgbColor(selectedPlotEntries[0].rgb_mean) }" />
                {{ rgbText(selectedPlotEntries[0].rgb_mean) }}
              </span>
            </div>
          </div>

          <div class="overflow-x-auto rounded-lg border border-border/60">
            <table class="w-full text-left text-[11px] tabular-nums">
              <thead class="bg-muted/30 text-muted-foreground">
                <tr>
                  <th scope="col" class="px-2.5 py-2 font-medium">光譜指標</th>
                  <th scope="col" class="px-2.5 py-2 text-right font-medium">平均指數</th>
                  <th scope="col" class="px-2.5 py-2 text-right font-medium">相對 CK</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="fid in allowedIds" :key="fid" class="border-t border-border/40"
                  :class="{ 'bg-primary/10': currentFormula === fid }">
                  <th scope="row" class="px-2.5 py-2 font-semibold text-foreground" :title="formulaTooltip(fid)">
                    <div class="flex items-center gap-1.5">
                      <span class="inline-block size-2 rounded-sm border border-border/50 shrink-0"
                        :style="{ backgroundColor: rgbColor(getAlgoRow(selectedPlotEntries[0].algorithms, fid)?.rgb_mean ?? null) }" />
                      <span>{{ fid }}</span>
                    </div>
                  </th>
                  <td class="px-2.5 py-2 text-right font-mono font-medium">
                    {{ formatIndex(getAlgoRow(selectedPlotEntries[0].algorithms, fid)?.index_mean) }}
                  </td>
                  <td class="px-2.5 py-2 text-right font-mono text-[10px]" :class="{
                    'text-emerald-600 dark:text-emerald-400': formatDeltaVsCk(getAlgoRow(selectedPlotEntries[0].algorithms, fid)?.index_mean, fid, selectedPlotEntries[0].is_control).tone === 'positive',
                    'text-rose-600 dark:text-rose-400': formatDeltaVsCk(getAlgoRow(selectedPlotEntries[0].algorithms, fid)?.index_mean, fid, selectedPlotEntries[0].is_control).tone === 'negative',
                    'text-muted-foreground': formatDeltaVsCk(getAlgoRow(selectedPlotEntries[0].algorithms, fid)?.index_mean, fid, selectedPlotEntries[0].is_control).tone === 'neutral',
                  }">
                    {{ formatDeltaVsCk(getAlgoRow(selectedPlotEntries[0].algorithms, fid)?.index_mean, fid,
                      selectedPlotEntries[0].is_control).text }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- 模式 3：多選 2+ 小區 -> 並列數值對比表 -->
        <template v-else-if="viewMode === 'multi'">
          <div class="flex flex-wrap items-center gap-1">
            <Badge v-for="entry in selectedPlotEntries" :key="entry.plot_number" variant="secondary"
              class="gap-1 text-[11px] pr-1">
              <span>{{ formatPlotShortLabel(entry) }}</span>
              <button type="button" class="rounded-full p-0.5 hover:bg-background/70 cursor-pointer"
                :aria-label="`移除 #${entry.plot_number}`" @click="removeSelectedPlot(entry.plot_number)">
                <X class="size-2.5" />
              </button>
            </Badge>
          </div>

          <div class="overflow-x-auto rounded-lg border border-border/60">
            <table class="w-full text-left text-[11px] tabular-nums">
              <thead class="bg-muted/30 text-muted-foreground">
                <tr>
                  <th scope="col" class="px-2 py-2 font-medium sticky left-0 bg-muted/30">指標</th>
                  <th v-for="entry in selectedPlotEntries" :key="entry.plot_number" scope="col"
                    class="px-2 py-2 text-right font-medium whitespace-nowrap">
                    {{ formatPlotShortLabel(entry) }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr class="border-t border-border/40">
                  <th scope="row" class="px-2 py-2 font-medium text-muted-foreground sticky left-0 bg-card">
                    RGB
                  </th>
                  <td v-for="entry in selectedPlotEntries" :key="entry.plot_number"
                    class="px-2 py-2 text-right font-mono text-[10px] whitespace-nowrap">
                    <span class="mr-1 inline-block size-2 rounded-sm border border-border/50"
                      :style="{ backgroundColor: rgbColor(entry.rgb_mean) }" />
                    {{ rgbText(entry.rgb_mean) }}
                  </td>
                </tr>
                <tr v-for="fid in allowedIds" :key="fid" class="border-t border-border/40"
                  :class="{ 'bg-primary/10': currentFormula === fid }">
                  <th scope="row" class="px-2 py-2 font-semibold text-foreground sticky left-0 bg-card"
                    :title="formulaTooltip(fid)">
                    {{ fid }}
                  </th>
                  <td v-for="entry in selectedPlotEntries" :key="entry.plot_number"
                    class="px-2 py-2 text-right font-mono whitespace-nowrap">
                    <div class="font-semibold text-foreground">
                      {{ formatIndex(getAlgoRow(entry.algorithms, fid)?.index_mean) }}
                    </div>
                    <div class="text-[10px]" :class="{
                      'text-emerald-600 dark:text-emerald-400': formatDeltaVsCk(getAlgoRow(entry.algorithms, fid)?.index_mean, fid, entry.is_control).tone === 'positive',
                      'text-rose-600 dark:text-rose-400': formatDeltaVsCk(getAlgoRow(entry.algorithms, fid)?.index_mean, fid, entry.is_control).tone === 'negative',
                      'text-muted-foreground': formatDeltaVsCk(getAlgoRow(entry.algorithms, fid)?.index_mean, fid, entry.is_control).tone === 'neutral',
                    }">
                      {{ formatDeltaVsCk(getAlgoRow(entry.algorithms, fid)?.index_mean, fid, entry.is_control).text }}
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <p class="text-[11px] leading-relaxed text-muted-foreground/85 pt-1">
          所有指標皆以純 RGB 三通道計算並排除透明背景；「相對 CK」以對照組小區平均值為基準。
        </p>
      </template>
    </div>

    <!-- 放大檢視統計圖表與 Tukey HSD 成對比較彈窗 -->
    <Dialog v-model:open="isChartDialogOpen">
      <DialogContent class="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>各處理組光譜統計圖表與顯著性檢定</DialogTitle>
          <DialogDescription>
            點擊圖上任一小區散點或異常警示可直接連動高亮右側正射／光譜地圖對應小區；系統嚴守雙軌解讀原則，不自動刪除離群數據。
          </DialogDescription>
        </DialogHeader>
        <SpectralGroupChart v-if="statistics && statistics.treatment_groups.length > 0 && allowedFormulas.length > 0"
          :statistics="statistics" :plots="plots" :allowed-formulas="allowedFormulas" :current-formula="currentFormula"
          :selected-plot-numbers="selectedPlotNumbers" :get-plot-color="getPlotColor" :expanded="true"
          @select-plots="emit('select-plots', $event)" />
      </DialogContent>
    </Dialog>
  </section>
</template>
