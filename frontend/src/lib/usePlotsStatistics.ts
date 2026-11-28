import { onScopeDispose, ref, watch, type Ref } from 'vue'
import type { MeanRgb } from './useRegionStatistics'

export interface AlgorithmStatRow {
  id: string
  index_mean: number | null
  index_std?: number | null
  index_cv_pct?: number | null
  index_min?: number | null
  index_q1?: number | null
  index_median?: number | null
  index_q3?: number | null
  index_max?: number | null
  replicate_count?: number
  tukey_group?: string | null
  outlier_plot_numbers?: number[]
  valid_pixel_count: number
  rgb_mean: MeanRgb
}

export interface PairwiseComparison {
  group_a: string
  group_b: string
  label_a: string
  label_b: string
  mean_diff: number
  p_value: number
  significant: boolean
}

export interface StatisticalTestResult {
  formula_id: string
  status: 'ok' | 'insufficient_groups' | 'insufficient_replicates' | 'zero_variance'
  message: string
  alpha: number
  anova_f: number | null
  anova_p: number | null
  significant: boolean
  group_letters: Record<string, string>
  pairwise: PairwiseComparison[]
}

export interface OutlierAlert {
  plot_number: number
  group_key: string
  group_label: string
  is_control: boolean
  formula_id: string
  value: number
  group_mean: number
  group_median: number
  group_cv_pct: number | null
  method: 'iqr_1.5' | 'cv_15_n3'
  direction: 'high' | 'low'
  reason: string
}

export interface PlotStatisticsEntry {
  plot_number: number
  is_control: boolean
  treatment: string
  dose: string
  pixel_count: number
  rgb_mean: MeanRgb
  algorithms: AlgorithmStatRow[]
}

export interface AggregatedStatisticsEntry {
  plot_count: number
  pixel_count: number
  rgb_mean: MeanRgb
  algorithms: AlgorithmStatRow[]
}

export interface TreatmentGroupStatistics extends AggregatedStatisticsEntry {
  key: string
  label: string
  is_control: boolean
  plot_numbers: number[]
}

export interface PlotsStatisticsBatch {
  plots: PlotStatisticsEntry[]
  control_baseline: AggregatedStatisticsEntry | null
  treatment_groups: TreatmentGroupStatistics[]
  field_summary: AggregatedStatisticsEntry
  statistical_tests?: Record<string, StatisticalTestResult>
  outliers?: Record<string, OutlierAlert[]>
}

export function usePlotsStatistics(
  taskId: Ref<string>,
  plotsSignature: Ref<string>
) {
  const data = ref<PlotsStatisticsBatch | null>(null)
  const loading = ref(false)
  const error = ref('')
  let controller: AbortController | undefined
  let version = 0

  function cancel() {
    version++
    controller?.abort()
  }

  async function refresh() {
    cancel()
    data.value = null
    error.value = ''
    const id = taskId.value
    if (!id) {
      loading.value = false
      return
    }
    loading.value = true
    const requestVersion = version
    controller = new AbortController()
    try {
      const response = await fetch(`/api/task/plots-statistics/${encodeURIComponent(id)}`, {
        signal: controller.signal,
      })
      const result = await response.json().catch(() => null)
      if (!response.ok || !result?.result || !result?.data) {
        throw new Error(result?.message || '無法取得全區光譜統計資料')
      }
      if (requestVersion === version) {
        data.value = result.data as PlotsStatisticsBatch
      }
    } catch (cause) {
      if (requestVersion === version && !(cause instanceof DOMException && cause.name === 'AbortError')) {
        error.value = cause instanceof Error ? cause.message : '無法取得全區光譜統計資料'
      }
    } finally {
      if (requestVersion === version) {
        loading.value = false
      }
    }
  }

  watch([taskId, plotsSignature], () => {
    void refresh()
  }, { immediate: true })

  onScopeDispose(cancel)

  return {
    data,
    loading,
    error,
    refresh,
  }
}
