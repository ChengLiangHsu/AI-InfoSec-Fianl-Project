<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  Layers,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  RotateCw,
  Compass,
  MousePointer,
  Scan,
} from '@lucide/vue'
import PlotCanvasOverlay from '@/components/PlotCanvasOverlay.vue'
import SpectralStatsPanel, { type FormulaMeta } from '@/components/SpectralStatsPanel.vue'
import SpectralChatPanel from '@/components/SpectralChatPanel.vue'
import { useCanvasViewport, ROTATE_STEP_DEG } from '@/lib/useCanvasViewport'
import { usePlotsStatistics } from '@/lib/usePlotsStatistics'
import { normalizeRecommendedFormulas, type ScenarioData } from '@/lib/scenarioSchema'
import type { PlotItem } from '@/lib/usePlots'

const props = defineProps<{
  projectId: string
  projectName?: string
  projectProgress?: number
  scenario?: ScenarioData | null
  plots: PlotItem[]
  formulas: FormulaMeta[]
  selectedFormula: string
  selectedPlotNumbers: number[]
  getPlotColor: (plot: PlotItem) => string
}>()

const emit = defineEmits<{
  (e: 'update:selectedFormula', formula: string): void
  (e: 'select-plots', plotNumbers: number[]): void
}>()

// 嚴格依步驟 2 情境規劃代理人決定的光譜清單過濾（舊專案未設定時退回全部 5 種 RGB 光譜）
const allowedFormulas = computed<FormulaMeta[]>(() => {
  const recommended = normalizeRecommendedFormulas(props.scenario?.recommended_formulas)
  if (recommended.length === 0) {
    return props.formulas
  }
  const byId = new Map(props.formulas.map((f) => [f.id, f]))
  const filtered: FormulaMeta[] = []
  for (const id of recommended) {
    const meta = byId.get(id)
    if (meta) {
      filtered.push(meta)
    } else {
      filtered.push({ id })
    }
  }
  return filtered
})

watch(
  [allowedFormulas, () => props.selectedFormula],
  ([allowed, current]) => {
    if (current !== 'rgb' && !allowed.some((f) => f.id === current)) {
      emit('update:selectedFormula', 'rgb')
    }
  },
  { immediate: true }
)

// 整批小區光譜統計（單次開啟正射圖，切換選取零延遲）
const taskIdRef = computed(() => props.projectId)
const plotsSignature = computed(() =>
  props.plots
    .map((p) => `${p.plot_number}:${p.is_control ? 1 : 0}:${p.treatment}:${p.dose}:${p.coords}`)
    .join('|')
)
const {
  data: plotsStatistics,
  loading: statsLoading,
  error: statsError,
  refresh: refreshStats,
} = usePlotsStatistics(taskIdRef, plotsSignature)

// 三欄可拖曳寬度比例（左 26% / 中 30% / 右 44%）
const DEFAULT_LEFT_PCT = 26
const DEFAULT_MIDDLE_PCT = 30
const MIN_LEFT_PCT = 18
const MIN_MIDDLE_PCT = 20
const MIN_RIGHT_PCT = 26

const layoutRef = ref<HTMLDivElement | null>(null)
const leftPct = ref(DEFAULT_LEFT_PCT)
const middlePct = ref(DEFAULT_MIDDLE_PCT)
const rightPct = computed(() => Math.max(MIN_RIGHT_PCT, 100 - leftPct.value - middlePct.value))
const activeDivider = ref<'left' | 'right' | null>(null)
const isDesktop = ref(typeof window !== 'undefined' ? window.innerWidth >= 1024 : true)

function updateDesktopState() {
  if (typeof window !== 'undefined') {
    isDesktop.value = window.innerWidth >= 1024
  }
}

function startResize(which: 'left' | 'right', e: PointerEvent) {
  if (!isDesktop.value) return
  e.preventDefault()
  activeDivider.value = which
  window.addEventListener('pointermove', onResizeMove)
  window.addEventListener('pointerup', stopResize)
}

function onResizeMove(e: PointerEvent) {
  if (!activeDivider.value || !layoutRef.value) return
  const rect = layoutRef.value.getBoundingClientRect()
  if (rect.width <= 0) return
  const pct = ((e.clientX - rect.left) / rect.width) * 100

  if (activeDivider.value === 'left') {
    const maxLeft = 100 - middlePct.value - MIN_RIGHT_PCT
    leftPct.value = Math.max(MIN_LEFT_PCT, Math.min(maxLeft, pct))
  } else {
    const minBoundary = leftPct.value + MIN_MIDDLE_PCT
    const maxBoundary = 100 - MIN_RIGHT_PCT
    const clampedBoundary = Math.max(minBoundary, Math.min(maxBoundary, pct))
    middlePct.value = clampedBoundary - leftPct.value
  }
}

function stopResize() {
  activeDivider.value = null
  window.removeEventListener('pointermove', onResizeMove)
  window.removeEventListener('pointerup', stopResize)
  nextTick(() => {
    syncMapAfterResize()
  })
}

function resetSplitRatios() {
  leftPct.value = DEFAULT_LEFT_PCT
  middlePct.value = DEFAULT_MIDDLE_PCT
  nextTick(() => {
    syncMapAfterResize()
  })
}

// 右欄正射／光譜圖視區控制
const viewportRef = ref<HTMLDivElement | null>(null)
const imageRef = ref<HTMLImageElement | null>(null)
const plotCanvasOverlayRef = ref<InstanceType<typeof PlotCanvasOverlay> | null>(null)
const viewport = useCanvasViewport()

const isImageLoading = ref(true)
const isRotateToolActive = ref(false)
const mapInteractionMode = ref<'pan' | 'select'>('pan')

const currentImageUrl = computed(() => {
  if (!props.projectId) return ''
  if (props.selectedFormula === 'rgb') {
    return `/api/task/odm-task-orthophoto/${props.projectId}`
  }
  return `/api/task/odm-task-spectral/${props.projectId}?formula=${encodeURIComponent(props.selectedFormula)}`
})

watch(
  () => [props.projectId, props.selectedFormula],
  () => {
    isImageLoading.value = true
  }
)

const selectedSinglePlotNumber = computed<number | null>(() =>
  props.selectedPlotNumbers.length === 1 ? props.selectedPlotNumbers[0] : null
)

function onFitToScreen() {
  const container = viewportRef.value
  const img = imageRef.value
  if (!container || !img || img.naturalWidth <= 0) return
  viewport.fitToViewport(
    container.clientWidth,
    container.clientHeight,
    img.naturalWidth || 1,
    img.naturalHeight || 1,
    20
  )
  nextTick(() => {
    plotCanvasOverlayRef.value?.syncCanvasSize()
  })
}

function syncMapAfterResize() {
  if (imageRef.value && imageRef.value.complete && imageRef.value.naturalWidth > 0) {
    onFitToScreen()
  } else {
    plotCanvasOverlayRef.value?.syncCanvasSize()
  }
}

function onImageLoaded() {
  isImageLoading.value = false
  nextTick(() => {
    onFitToScreen()
  })
}

function onZoomIn() {
  viewport.zoomIn(viewportRef.value?.clientWidth, viewportRef.value?.clientHeight)
  nextTick(() => plotCanvasOverlayRef.value?.redraw())
}

function onZoomOut() {
  viewport.zoomOut(viewportRef.value?.clientWidth, viewportRef.value?.clientHeight)
  nextTick(() => plotCanvasOverlayRef.value?.redraw())
}

function onRotateLeft() {
  viewport.rotateBy(-ROTATE_STEP_DEG, viewportRef.value?.clientWidth, viewportRef.value?.clientHeight)
  nextTick(() => plotCanvasOverlayRef.value?.redraw())
}

function onRotateRight() {
  viewport.rotateBy(ROTATE_STEP_DEG, viewportRef.value?.clientWidth, viewportRef.value?.clientHeight)
  nextTick(() => plotCanvasOverlayRef.value?.redraw())
}

function onResetRotation() {
  viewport.resetRotation(viewportRef.value?.clientWidth, viewportRef.value?.clientHeight)
  nextTick(() => plotCanvasOverlayRef.value?.redraw())
}

function toggleRotateTool() {
  isRotateToolActive.value = !isRotateToolActive.value
}

function handleOverlaySelectPlots(nums: number[]) {
  emit('select-plots', nums)
}

function handleOverlaySelectPlot(num: number | null) {
  if (num === null) {
    if (props.selectedPlotNumbers.length <= 1) {
      emit('select-plots', [])
    }
  } else {
    emit('select-plots', [num])
  }
}

let mapResizeObserver: ResizeObserver | null = null

onMounted(() => {
  updateDesktopState()
  window.addEventListener('resize', updateDesktopState)
  if (viewportRef.value && typeof ResizeObserver !== 'undefined') {
    mapResizeObserver = new ResizeObserver(() => {
      syncMapAfterResize()
    })
    mapResizeObserver.observe(viewportRef.value)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', updateDesktopState)
  window.removeEventListener('pointermove', onResizeMove)
  window.removeEventListener('pointerup', stopResize)
  mapResizeObserver?.disconnect()
})
</script>

<template>
  <div
    data-testid="spectral-workspace"
    class="flex-1 h-full max-h-full min-h-0 flex flex-col px-3 sm:px-4 pt-3 pb-20 bg-muted/10 overflow-hidden"
    :class="{ 'select-none cursor-col-resize': activeDivider !== null }"
  >
    <div
      ref="layoutRef"
      data-testid="spectral-workspace-columns"
      class="flex-1 h-full min-h-0 w-full flex flex-col lg:flex-row gap-2 lg:gap-0 overflow-hidden"
    >
      <!-- 左欄：光譜演算法數值資訊 -->
      <div
        class="min-h-0 min-w-0 lg:h-full flex flex-col overflow-hidden"
        :style="isDesktop ? { width: `${leftPct}%` } : undefined"
      >
        <SpectralStatsPanel
          :plots="plots"
          :selected-plot-numbers="selectedPlotNumbers"
          :current-formula="selectedFormula"
          :allowed-formulas="allowedFormulas"
          :get-plot-color="getPlotColor"
          :statistics="plotsStatistics"
          :loading="statsLoading"
          :error="statsError"
          @select-plots="emit('select-plots', $event)"
          @refresh="refreshStats"
        />
      </div>

      <!-- 左｜中 拖曳分隔拉桿 -->
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="調整左側數值欄與中間對話欄寬度"
        data-testid="spectral-divider-left"
        title="拖曳調整欄寬（雙擊重設預設比例）"
        class="hidden lg:flex w-2.5 shrink-0 items-center justify-center cursor-col-resize group"
        @pointerdown="startResize('left', $event)"
        @dblclick="resetSplitRatios"
      >
        <div
          class="h-12 w-1 rounded-full transition-colors"
          :class="activeDivider === 'left' ? 'bg-primary' : 'bg-border group-hover:bg-primary/60'"
        />
      </div>

      <!-- 中欄：光譜分析代理人對話框 -->
      <div
        class="min-h-0 min-w-0 lg:h-full flex flex-col overflow-hidden"
        :style="isDesktop ? { width: `${middlePct}%` } : undefined"
      >
        <SpectralChatPanel
          :project-id="projectId"
          :project-name="projectName"
          :plots="plots"
          :selected-plot-numbers="selectedPlotNumbers"
          :current-formula="selectedFormula"
        />
      </div>

      <!-- 中｜右 拖曳分隔拉桿 -->
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="調整中間對話欄與右側正射圖寬度"
        data-testid="spectral-divider-right"
        title="拖曳調整欄寬（雙擊重設預設比例）"
        class="hidden lg:flex w-2.5 shrink-0 items-center justify-center cursor-col-resize group"
        @pointerdown="startResize('right', $event)"
        @dblclick="resetSplitRatios"
      >
        <div
          class="h-12 w-1 rounded-full transition-colors"
          :class="activeDivider === 'right' ? 'bg-primary' : 'bg-border group-hover:bg-primary/60'"
        />
      </div>

      <!-- 右欄：套用光譜下的正射圖 -->
      <section
        data-testid="spectral-map-panel"
        aria-label="光譜正射影像視圖"
        class="relative flex-1 min-h-[320px] lg:min-h-0 min-w-0 lg:h-full rounded-2xl border border-border/70 bg-black overflow-hidden select-none shadow-xs"
        :style="isDesktop ? { width: `${rightPct}%` } : undefined"
      >
        <!-- 右上角光譜演算法切換器（嚴格僅含 RGB 原圖＋步驟 2 決定之光譜） -->
        <div
          data-testid="spectral-formula-switcher"
          data-tour="formula-selector"
          class="absolute top-3 right-3 z-20 flex flex-col gap-1 rounded-xl border border-white/15 bg-zinc-950/85 p-2 text-white shadow-2xl backdrop-blur-md"
        >
          <div class="flex items-center gap-1.5 px-1.5 py-0.5 text-[10px] font-semibold text-zinc-400 uppercase tracking-wider">
            <Layers class="size-3" />
            <span>適用光譜</span>
          </div>
          <div class="flex flex-col gap-1 max-h-[260px] overflow-y-auto pr-0.5">
            <TooltipProvider :delay-duration="150">
              <Tooltip>
                <TooltipTrigger as-child>
                  <Button
                    size="sm"
                    variant="ghost"
                    data-testid="formula-option-rgb"
                    class="h-7 justify-start gap-2 px-2.5 text-xs font-medium border transition-colors cursor-pointer"
                    :class="selectedFormula === 'rgb'
                      ? 'bg-emerald-600 text-white border-emerald-400/50 hover:bg-emerald-500 hover:text-white dark:hover:bg-emerald-500 shadow-xs'
                      : 'bg-white/5 text-zinc-200 border-white/10 hover:bg-white/15 hover:text-white dark:hover:bg-white/15'"
                    @click="emit('update:selectedFormula', 'rgb')"
                  >
                    <span
                      class="size-2 rounded-full"
                      :class="selectedFormula === 'rgb' ? 'bg-white' : 'bg-emerald-400'"
                    />
                    <span>RGB 原始</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="left" class="max-w-xs space-y-1 p-2 text-xs">
                  <p class="font-bold text-foreground">原始正射影像 (RGB)</p>
                  <p class="text-muted-foreground leading-relaxed">未經光譜指數計算之原始拼接正射影像。</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <div class="my-0.5 h-px bg-white/15" />

            <TooltipProvider
              v-for="f in allowedFormulas"
              :key="f.id"
              :delay-duration="150"
            >
              <Tooltip>
                <TooltipTrigger as-child>
                  <Button
                    size="sm"
                    variant="ghost"
                    :data-testid="`formula-option-${f.id}`"
                    class="h-7 justify-between gap-2 px-2.5 text-xs font-medium border transition-colors cursor-pointer"
                    :class="selectedFormula === f.id
                      ? 'bg-purple-600 text-white border-purple-400/50 hover:bg-purple-500 hover:text-white dark:hover:bg-purple-500 shadow-xs'
                      : 'bg-white/5 text-zinc-200 border-white/10 hover:bg-white/15 hover:text-white dark:hover:bg-white/15'"
                    @click="emit('update:selectedFormula', f.id)"
                  >
                    <span class="flex items-center gap-1.5">
                      <span class="font-semibold">{{ f.id }}</span>
                      <span
                        v-if="f.badge && f.badge !== 'RGB 可見光'"
                        class="rounded bg-amber-500/20 px-1 py-0.5 text-[9px] font-medium text-amber-200"
                      >
                        {{ f.badge }}
                      </span>
                    </span>
                    <span
                      v-if="selectedFormula === f.id"
                      class="size-1.5 rounded-full bg-white animate-pulse"
                    />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="left" class="max-w-xs space-y-1.5 p-2.5 text-xs">
                  <div class="flex items-center justify-between gap-2">
                    <p class="font-bold text-foreground">{{ f.label || f.id }}</p>
                    <span v-if="f.badge" class="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">{{ f.badge }}</span>
                  </div>
                  <p v-if="f.help" class="text-muted-foreground leading-relaxed">{{ f.help }}</p>
                  <p v-if="f.expr" class="font-mono text-[10px] text-muted-foreground/90 bg-muted/60 px-1.5 py-1 rounded">
                    純 RGB 公式：{{ f.expr }}
                  </p>
                  <p v-if="f.limitation" class="text-[11px] text-amber-600 dark:text-amber-300 leading-relaxed">
                    限制：{{ f.limitation }}
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>

        <!-- 左下角縮放／旋轉／框選控制列 -->
        <div
          class="absolute bottom-3 left-3 z-20 flex items-center gap-0.5 rounded-xl border border-white/15 bg-zinc-950/85 p-1 text-zinc-200 shadow-2xl backdrop-blur-md"
        >
          <Button
            size="sm"
            variant="ghost"
            class="size-7 p-0 cursor-pointer text-zinc-400 hover:text-white hover:bg-white/10"
            title="縮小視角"
            @click="onZoomOut"
          >
            <ZoomOut class="size-3.5" />
          </Button>
          <span class="w-11 text-center font-mono text-[11px] font-semibold text-zinc-100 select-none">
            {{ viewport.zoomPercentage }}%
          </span>
          <Button
            size="sm"
            variant="ghost"
            class="size-7 p-0 cursor-pointer text-zinc-400 hover:text-white hover:bg-white/10"
            title="放大視角"
            @click="onZoomIn"
          >
            <ZoomIn class="size-3.5" />
          </Button>

          <div class="my-1 h-3.5 w-px bg-white/20" />

          <Button
            size="sm"
            variant="ghost"
            class="size-7 p-0 cursor-pointer text-zinc-400 hover:text-white hover:bg-white/10"
            title="逆時針旋轉 15°"
            @click="onRotateLeft"
          >
            <RotateCcw class="size-3.5" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            class="h-7 min-w-10 px-1 font-mono text-[11px] font-semibold cursor-pointer"
            :class="viewport.rotationDegrees.value !== 0 ? 'text-purple-300 hover:text-purple-200 hover:bg-purple-500/20' : 'text-zinc-300 hover:text-white hover:bg-white/10'"
            title="重設旋轉角度為 0°"
            @click="onResetRotation"
          >
            {{ viewport.rotationDegrees }}°
          </Button>
          <Button
            size="sm"
            variant="ghost"
            class="size-7 p-0 cursor-pointer text-zinc-400 hover:text-white hover:bg-white/10"
            title="順時針旋轉 15°"
            @click="onRotateRight"
          >
            <RotateCw class="size-3.5" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            class="size-7 p-0 cursor-pointer transition-colors"
            :class="isRotateToolActive ? 'bg-purple-600 text-white hover:bg-purple-500 ring-1 ring-purple-400/60' : 'text-zinc-400 hover:text-white hover:bg-white/10'"
            :aria-pressed="isRotateToolActive"
            title="切換滑鼠左鍵旋轉模式（隨時可用右鍵旋轉）"
            @click="toggleRotateTool"
          >
            <Compass class="size-3.5" />
          </Button>

          <div class="my-1 h-3.5 w-px bg-white/20" />

          <Button
            size="sm"
            variant="ghost"
            class="h-7 gap-1 px-2 text-xs font-medium cursor-pointer transition-colors"
            :class="mapInteractionMode === 'select' ? 'bg-sky-600 text-white hover:bg-sky-500 ring-1 ring-sky-400/60' : 'text-zinc-300 hover:text-white hover:bg-white/10'"
            :aria-pressed="mapInteractionMode === 'select'"
            data-testid="step4-box-select-toggle"
            title="切換拉框多選模式（預設可直接點選小區、拖曳空白處平移）"
            @click="mapInteractionMode = mapInteractionMode === 'select' ? 'pan' : 'select'"
          >
            <MousePointer class="size-3.5" />
            <span class="hidden xl:inline">框選</span>
          </Button>

          <Button
            size="sm"
            variant="ghost"
            class="h-7 gap-1 px-2 text-xs font-medium cursor-pointer text-zinc-300 hover:text-white hover:bg-white/10"
            title="重設最適大小"
            @click="onFitToScreen"
          >
            <Scan class="size-3.5" />
          </Button>
        </div>

        <!-- 影像載入中遮罩 -->
        <div
          v-if="isImageLoading && projectProgress === 100"
          class="absolute inset-0 z-15 flex flex-col items-center justify-center bg-black/60 backdrop-blur-xs pointer-events-none"
        >
          <Spinner class="size-7 animate-spin text-purple-400" />
          <span class="mt-2 text-xs font-medium text-zinc-300">光譜影像載入中...</span>
        </div>

        <!-- 影像與小區多邊形畫布 -->
        <div ref="viewportRef" class="relative w-full h-full overflow-hidden bg-black">
          <img
            v-if="projectProgress === 100"
            ref="imageRef"
            class="absolute top-0 left-0 max-w-none max-h-none pointer-events-none select-none transition-opacity duration-150"
            :class="{ 'opacity-40': isImageLoading }"
            :style="{
              width: `${viewport.baseWidth.value}px`,
              height: `${viewport.baseHeight.value}px`,
              transform: `translate3d(${viewport.panX.value}px, ${viewport.panY.value}px, 0) rotate(${viewport.rotation.value}deg) scale(${viewport.scale.value})`,
              transformOrigin: '0 0',
              imageRendering: 'auto',
            }"
            :src="currentImageUrl"
            :alt="projectName || '光譜正射影像'"
            @load="onImageLoaded"
            @error="isImageLoading = false"
          />
          <PlotCanvasOverlay
            v-if="projectProgress === 100"
            ref="plotCanvasOverlayRef"
            :plots="plots"
            :active-mode="mapInteractionMode"
            draw-tool="rect"
            :can-edit="false"
            :click-select-on-pan="true"
            :selected-plot-number="selectedSinglePlotNumber"
            :selected-plot-numbers="selectedPlotNumbers"
            :get-plot-color="getPlotColor"
            :viewport="viewport"
            :is-rotate-tool-active="isRotateToolActive"
            :grid-state="{ isActive: false, corners: [], rows: 3, cols: 3, marginRatio: 0.1, scaleX: 0.8, scaleY: 0.8, paddingRatio: 0, offsetX: 0, offsetY: 0, excludedIndices: [], isDetecting: false }"
            :preview-plots="[]"
            @select-plot="handleOverlaySelectPlot"
            @select-plots="handleOverlaySelectPlots"
          />
        </div>
      </section>
    </div>
  </div>
</template>
