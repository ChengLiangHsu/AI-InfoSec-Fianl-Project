import { onScopeDispose, ref, watch, type Ref } from 'vue'

export type MeanRgb = [number, number, number] | null
export interface RegionStatistics {
  pixel_count: number
  rgb_mean: MeanRgb
  algorithms: {
    id: string
    index_mean: number | null
    valid_pixel_count: number
    rgb_mean: MeanRgb
  }[]
}

export function useRegionStatistics(taskId: Ref<string>, coords: Ref<string | undefined>) {
  const statistics = ref<RegionStatistics | null>(null)
  const loading = ref(false)
  const error = ref('')
  let controller: AbortController | undefined
  let timer: ReturnType<typeof setTimeout> | undefined
  let version = 0

  function cancel() {
    version++
    clearTimeout(timer)
    controller?.abort()
  }

  async function request(id: string, polygon: string, requestVersion: number) {
    controller = new AbortController()
    try {
      const response = await fetch(`/api/task/region-statistics/${encodeURIComponent(id)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ points: JSON.parse(polygon) }),
        signal: controller.signal,
      })
      const result = await response.json()
      if (!response.ok || !result.result || !result.data) throw new Error(result.message || '無法取得區域數值')
      if (requestVersion === version) statistics.value = result.data
    } catch (cause) {
      if (requestVersion === version) error.value = cause instanceof Error ? cause.message : '無法取得區域數值'
    } finally {
      if (requestVersion === version) loading.value = false
    }
  }

  function refresh() {
    cancel()
    statistics.value = null
    error.value = ''
    loading.value = Boolean(taskId.value && coords.value)
    if (!loading.value) return
    const id = taskId.value
    const polygon = coords.value!
    const requestVersion = version
    timer = setTimeout(() => request(id, polygon, requestVersion), 300)
  }

  watch([taskId, coords], refresh, { immediate: true })
  onScopeDispose(cancel)
  return { statistics, loading, error, refresh }
}
