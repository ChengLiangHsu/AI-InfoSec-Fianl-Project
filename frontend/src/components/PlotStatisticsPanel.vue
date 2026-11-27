<script setup lang="ts">
import { computed, ref } from 'vue'
import type { PlotItem } from '@/lib/usePlots'
import { useRegionStatistics, type MeanRgb } from '@/lib/useRegionStatistics'

interface FormulaMeta {
  id: string
  label?: string
  badge?: string
  expr?: string
  help?: string
  limitation?: string
}

const props = defineProps<{
  taskId: string
  plots: PlotItem[]
  currentFormula: string
  formulas?: FormulaMeta[]
}>()
const emit = defineEmits<{ (e: 'select-formula', formula: string): void }>()
const expanded = ref(true)
const focusedNumber = ref<number | null>(null)
const plot = computed(() => props.plots.find(p => p.plot_number === focusedNumber.value) ?? props.plots[0])
const taskId = computed(() => props.taskId)
const coords = computed(() => plot.value?.coords)
const { statistics, loading, error, refresh } = useRegionStatistics(taskId, coords)

const formulaMap = computed(() => new Map((props.formulas ?? []).map(item => [item.id, item])))

function formulaBadge(id: string): string {
  const badge = formulaMap.value.get(id)?.badge
  if (badge && badge !== 'RGB 可見光') return badge
  if (id === 'MPRI') return 'RGB 替代'
  return ''
}

function formulaTooltip(id: string): string {
  const meta = formulaMap.value.get(id)
  if (!meta) return `${id}（純 RGB 指標）`
  return [
    meta.label || meta.id,
    meta.expr ? `純 RGB 公式：${meta.expr}` : '',
    meta.limitation ? `限制：${meta.limitation}` : '',
  ].filter(Boolean).join('\n')
}

function rgbText(rgb: MeanRgb): string {
  return rgb ? rgb.map(value => value.toFixed(2)).join(' / ') : '—'
}

function rgbColor(rgb: MeanRgb): string {
  return rgb ? `rgb(${rgb.join(',')})` : 'transparent'
}
</script>

<template>
  <section aria-label="框選區域數值" class="absolute left-4 top-4 z-20 w-[min(25rem,calc(100%-7rem))] rounded-xl border border-white/15 bg-zinc-950/90 text-zinc-100 shadow-xl backdrop-blur-md" @pointerdown.stop @wheel.stop>
    <button type="button" class="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-xs font-semibold cursor-pointer" :aria-expanded="expanded" aria-controls="plot-statistics-content" @click="expanded = !expanded">
      <span>區域 RGB 與演算法數值 <span v-if="plot" class="text-sky-300">#{{ plot.plot_number }}{{ plot.is_control ? ' (CK)' : '' }}</span></span>
      <span class="text-zinc-400">{{ expanded ? '收合 −' : '展開 +' }}</span>
    </button>
    <div v-show="expanded" id="plot-statistics-content" class="max-h-[min(65vh,32rem)] overflow-auto border-t border-white/10 p-3 text-xs">
      <p v-if="!plot" class="text-zinc-400">點選已框選的小區，即可比較原圖與各純 RGB 演算法的區域平均數值。</p>
      <template v-else>
        <label v-if="plots.length > 1" class="mb-3 flex items-center gap-2">
          查看小區
          <select :value="plot.plot_number" aria-label="查看小區" class="rounded border border-white/20 bg-zinc-900 px-2 py-1" @change="focusedNumber = Number(($event.target as HTMLSelectElement).value)">
            <option v-for="item in plots" :key="item.plot_number" :value="item.plot_number">#{{ item.plot_number }}{{ item.is_control ? ' (CK)' : '' }}</option>
          </select>
          <span class="text-zinc-400">已選 {{ plots.length }} 區</span>
        </label>
        <p v-if="loading" role="status" class="py-2 text-zinc-300">正在計算框選區域…</p>
        <div v-else-if="error" role="alert" class="space-y-2 text-red-300">
          <p>{{ error }}</p>
          <button type="button" class="underline cursor-pointer" @click="refresh">重新計算</button>
        </div>
        <template v-else-if="statistics">
          <p v-if="!statistics.pixel_count" class="py-2 text-amber-200">區域內沒有有效影像像素，請調整框選範圍。</p>
          <template v-else>
            <p class="mb-2 text-zinc-400">有效像素 {{ statistics.pixel_count.toLocaleString() }} · RGB 範圍 0–255</p>
            <table class="w-full text-left text-[11px] tabular-nums">
              <caption class="sr-only">各純 RGB 演算法的平均指數及原圖／熱圖著色平均 RGB；RGB 欄依序為 R、G、B，演算法列採紅黃綠假色階故 B 固定為 0.00</caption>
              <thead class="text-zinc-400">
                <tr>
                  <th scope="col" class="pb-2">影像／純 RGB 演算法</th>
                  <th scope="col" class="pb-2 text-right">平均指數</th>
                  <th scope="col" class="pb-2 text-right" title="原圖列為原始輸入影像平均 RGB；演算法列為紅→黃→綠熱圖著色後平均 RGB（不含藍色，B 固定為 0.00）">原圖／著色 R / G / B</th>
                </tr>
              </thead>
              <tbody>
                <tr :class="{ 'bg-sky-400/10': currentFormula === 'rgb' }">
                  <th scope="row" class="py-2 font-medium"><button class="cursor-pointer text-sky-300" type="button" @click="emit('select-formula', 'rgb')">原圖 RGB</button></th>
                  <td class="text-right text-zinc-500">—</td>
                  <td class="text-right whitespace-nowrap" title="原始輸入影像之平均 R / G / B"><span class="mr-1 inline-block size-2 rounded-sm" :style="{ backgroundColor: rgbColor(statistics.rgb_mean) }" />{{ rgbText(statistics.rgb_mean) }}</td>
                </tr>
                <tr v-for="row in statistics.algorithms" :key="row.id" class="border-t border-white/10" :class="{ 'bg-sky-400/10': currentFormula === row.id }">
                  <th scope="row" class="py-2 font-medium" :title="formulaTooltip(row.id)">
                    <button class="cursor-pointer text-sky-300" type="button" @click="emit('select-formula', row.id)">{{ row.id }}</button>
                    <span v-if="formulaBadge(row.id)" class="ml-1 rounded bg-amber-500/20 px-1 py-0.5 text-[9px] font-normal text-amber-200">{{ formulaBadge(row.id) }}</span>
                  </th>
                  <td class="text-right" :title="`有效指數像素：${row.valid_pixel_count.toLocaleString()}`">{{ row.index_mean === null ? '無有效值' : row.index_mean.toFixed(4) }}</td>
                  <td class="text-right whitespace-nowrap" title="套用紅→黃→綠假色階（B 固定為 0）後之輸出平均 R / G / B"><span class="mr-1 inline-block size-2 rounded-sm" :style="{ backgroundColor: rgbColor(row.rgb_mean) }" />{{ rgbText(row.rgb_mean) }}</td>
                </tr>
              </tbody>
            </table>
            <p class="mt-3 leading-relaxed text-zinc-400">
              原圖列為框內原始輸入影像平均 R/G/B；演算法列為套用紅→黃→綠假色階著色後之輸出平均 R/G/B（該色階不含藍色，故演算法列 B 固定為 0.00 屬預期現象）。所有指標皆以純 RGB 三通道計算（MPRI 為 RGB 替代公式，非 531/570nm 窄波段 PRI）；平均指數先逐像素計算再取平均，排除無法計算的值與透明背景。
            </p>
          </template>
        </template>
      </template>
    </div>
  </section>
</template>
