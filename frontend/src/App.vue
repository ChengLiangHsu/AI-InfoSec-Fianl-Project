<script lang="ts">
export const description = "Collapsible nested sidebars."
export const iframeHeight = "800px"
</script>
<script setup lang="ts">
import {
  FileCodeIcon,
  XIcon,
  Plus,
  Upload,
  ImageIcon,
  Clock,
  Images,
  CheckCircle2,
  Layers,
  Trash2,
  Sparkles,
  ZoomIn,
  ZoomOut,
  Scan,
  RotateCcw,
  X,
  XCircle,
  Save,
  Pencil,
} from '@lucide/vue'
import { useCanvasViewport } from './lib/useCanvasViewport'
import AppSidebar from "@/components/AppSidebar.vue"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  Attachment,
  AttachmentContent,
  AttachmentDescription,
  AttachmentGroup,
  AttachmentMedia,
  AttachmentTitle,
} from '@/components/ui/attachment'
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import FloatingPersona from './components/FloatingPersona.vue'
import DroneHomeUpload from './components/DroneHomeUpload.vue'
import ProjectScenarioCard, { type ScenarioData } from './components/ProjectScenarioCard.vue'
import PlotToolbar from './components/PlotToolbar.vue'
import PlotCanvasOverlay from './components/PlotCanvasOverlay.vue'
import PlotTreatmentDialog, { type TreatmentData } from './components/PlotTreatmentDialog.vue'
import StepNavigationHUD from './components/StepNavigationHUD.vue'
import { usePlots, type NormalizedPoint, type PlotItem } from './lib/usePlots'
import { useChatAgent } from './lib/useChatAgent'
import { useOdmProgress } from './lib/useOdmProgress'
import exifr from 'exifr'

const { clearChat } = useChatAgent()
const { listenProgress } = useOdmProgress()

const {
  plots,
  activeMode,
  selectedPlotNumber,
  isDirty,
  isSaving,
  errorMessage,
  gridState,
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
  toggleExcludeGridCell,
  clearExcludedGridCells,
  duplicatePlot,
  pastePlotWithDelta,
  duplicateAllPlots,
  movePlot,
  copyPlotsToClipboard,
  pastePlotsFromClipboard,
  importPlotsFromExternal,
  setScenario,
} = usePlots()

const previewGridPlots = computed(() => {
  if (!gridState.value.isActive) return []
  return computeGridPlots()
})

async function handleDetectMarkers() {
  if (!selectedProject.value?.id) return
  await detectMarkers(selectedProject.value.id)
  nextTick(() => plotCanvasOverlayRef.value?.redraw())
}

function handleConfirmGrid() {
  if (plots.value.length > 0) {
    const replace = window.confirm(`目前畫布上已有 ${plots.value.length} 個小區。\n點擊「確定」替換既有小區，點擊「取消」保留並追加在後方。`)
    confirmBatchGenerate(replace ? 'replace' : 'append')
  } else {
    confirmBatchGenerate('replace')
  }
  nextTick(() => plotCanvasOverlayRef.value?.redraw())
}

function handleDuplicatePlot(plotNum: number) {
  duplicatePlot(plotNum)
  nextTick(() => plotCanvasOverlayRef.value?.redraw())
}

function handlePastePlot(payload: { sourcePlot: PlotItem; delta: { dx: number; dy: number } }) {
  pastePlotWithDelta(payload.sourcePlot, payload.delta)
  nextTick(() => plotCanvasOverlayRef.value?.redraw())
}

function handleClearAllPlots() {
  if (plots.value.length === 0) return
  if (confirm(`確定要清空畫布上的所有 ${plots.value.length} 個小區嗎？`)) {
    clearAllPlots()
    nextTick(() => plotCanvasOverlayRef.value?.redraw())
  }
}

const drawTool = ref<'rect' | 'polygon' | 'eraser'>('rect')

const plotCanvasOverlayRef = ref<InstanceType<typeof PlotCanvasOverlay> | null>(null)
const orthoContainerRef = ref<HTMLDivElement | null>(null)
const viewportRef = ref<HTMLDivElement | null>(null)
const imageRef = ref<HTMLImageElement | null>(null)

const viewport = useCanvasViewport()

const isDrawing = computed(() => plotCanvasOverlayRef.value?.isDrawing?.() || false)

const treatmentDialogState = ref<{
  open: boolean
  isNewPlot: boolean
  plotNumber: number | null
  points: NormalizedPoint[] | null
  initialTreatment: string
  initialDose: string
  initialIsControl: boolean
}>({
  open: false,
  isNewPlot: true,
  plotNumber: null,
  points: null,
  initialTreatment: '',
  initialDose: '',
  initialIsControl: false,
})

function onFitToScreen() {
  const container = viewportRef.value
  const img = imageRef.value
  if (!container || !img) return
  viewport.fitToViewport(
    container.clientWidth,
    container.clientHeight,
    img.naturalWidth || 1,
    img.naturalHeight || 1,
    24
  )
  nextTick(() => {
    plotCanvasOverlayRef.value?.syncCanvasSize()
  })
}

function handleWindowResize() {
  if (viewportRef.value && imageRef.value && imageRef.value.complete && imageRef.value.naturalWidth > 0) {
    onFitToScreen()
  }
}

function onZoomIn() {
  const w = viewportRef.value?.clientWidth
  const h = viewportRef.value?.clientHeight
  viewport.zoomIn(w, h)
  nextTick(() => plotCanvasOverlayRef.value?.redraw())
}

function onZoomOut() {
  const w = viewportRef.value?.clientWidth
  const h = viewportRef.value?.clientHeight
  viewport.zoomOut(w, h)
  nextTick(() => plotCanvasOverlayRef.value?.redraw())
}

function onImageLoaded() {
  isImageLoading.value = false
  nextTick(() => {
    onFitToScreen()
  })
}

function onPlotDrawn(points: NormalizedPoint[]) {
  addPlotWithTreatment(points, '', '', false)
  nextTick(() => plotCanvasOverlayRef.value?.redraw())
}

function onEditPlot(plot: PlotItem) {
  treatmentDialogState.value = {
    open: true,
    isNewPlot: false,
    plotNumber: plot.plot_number,
    points: null,
    initialTreatment: plot.treatment,
    initialDose: plot.dose,
    initialIsControl: plot.is_control,
  }
}

function onDialogConfirm(data: TreatmentData) {
  if (treatmentDialogState.value.isNewPlot && treatmentDialogState.value.points) {
    addPlotWithTreatment(
      treatmentDialogState.value.points,
      data.treatment,
      data.dose,
      data.isControl
    )
  } else if (!treatmentDialogState.value.isNewPlot && treatmentDialogState.value.plotNumber !== null) {
    updatePlotTreatment(
      treatmentDialogState.value.plotNumber,
      data.treatment,
      data.dose,
      data.isControl
    )
  }
  treatmentDialogState.value.open = false
  treatmentDialogState.value.points = null
}

function onDialogCancel() {
  treatmentDialogState.value.open = false
  treatmentDialogState.value.points = null
}

function onDialogDelete(plotNumber: number) {
  deletePlot(plotNumber)
  treatmentDialogState.value.open = false
  treatmentDialogState.value.points = null
}

function onUpdatePlotPoints(payload: { plotNumber: number; points: NormalizedPoint[] }) {
  updatePlotPoints(payload.plotNumber, payload.points)
}

function onSelectPlot(plotNumber: number | null) {
  selectedPlotNumber.value = plotNumber
}

async function handleSavePlots() {
  if (!selectedProject.value?.id) return
  const ok = await savePlots(selectedProject.value.id)
  if (!ok && errorMessage.value) {
    alert(errorMessage.value)
  }
}

const currentStep = ref<1 | 2 | 3 | 4>(1)

function isStepUnlocked(stepId: 1 | 2 | 3 | 4): boolean {
  if (stepId === 1 || stepId === 2) return true
  if (stepId === 3) return (selectedProject.value?.progress ?? 0) === 100
  if (stepId === 4) return (selectedProject.value?.progress ?? 0) === 100 && plots.value.length > 0
  return false
}

function canSafelyLeaveStep3(): boolean {
  if (currentStep.value === 3 && isDirty.value) {
    return window.confirm('小區標註尚有未儲存的變更，確定要切換步驟嗎？（建議先點擊「儲存小區」以保留進度）')
  }
  return true
}

function resetStepFormula(targetStep: 1 | 2 | 3 | 4) {
  // 僅步驟 4 啟用光譜指標，離開步驟 4 切換至其他步驟時自動重置為原始 RGB
  if (targetStep !== 4) {
    selectedFormula.value = 'rgb'
  }
}

function handleStepChange(targetStep: 1 | 2 | 3 | 4) {
  if (targetStep === currentStep.value) return
  if (!isStepUnlocked(targetStep)) {
    if ((selectedProject.value?.progress ?? 0) < 100) {
      alert(`需待正射影像拼接完成（目前進度 ${selectedProject.value?.progress ?? 0}%）方可進入該步驟`)
    } else if (targetStep === 4 && plots.value.length === 0) {
      alert('需先於步驟 3 完成小區網格標註與儲存方可進入各小區光譜分析')
    }
    return
  }
  if (currentStep.value === 3 && !canSafelyLeaveStep3()) {
    return
  }
  currentStep.value = targetStep
  resetStepFormula(targetStep)
  nextTick(() => {
    if (imageRef.value && imageRef.value.complete && imageRef.value.naturalWidth > 0) {
      onFitToScreen()
    }
    if (plotCanvasOverlayRef.value) {
      plotCanvasOverlayRef.value.syncCanvasSize()
      plotCanvasOverlayRef.value.redraw()
    }
  })
}

async function handleGoHome() {
  if (isDirty.value) {
    if (!confirm('您有未儲存的小區設定，是否確定返回主畫面？未儲存的變更將會遺失。')) {
      return
    }
  }
  selectedProject.value = null
  currentStep.value = 1
  await clearChat('home')
}


interface Formula {
  id: string
  expr: string
  help?: string
  range?: [number, number]
}

interface UploadItem {
  name: string
  size: string
  state: 'idle' | 'uploading' | 'done' | 'error'
  latitude: number
  longitude: number
}

interface Project {
  id: string
  name: string
  images?: number
  progress?: number
  fileNames?: string[]
  scenario?: any
}

const projects = ref<Project[]>([])
const selectedProject = ref<Project | null>(null)
const processingProject = ref<Project | null>(null)
const uploadList = ref<UploadItem[]>([])
const currentUploadedFileNames = ref<string[]>([])

function onScenarioUpdated(scenario: ScenarioData) {
  if (selectedProject.value) {
    selectedProject.value.scenario = scenario
  }
  setScenario(scenario)
}

function onScenarioSaved(scenario: ScenarioData) {
  if (selectedProject.value) {
    selectedProject.value.scenario = scenario
  }
  setScenario(scenario)
}
const isCreatingProject = ref(false)
const formulas = ref<Formula[]>([])
const selectedFormula = ref<string>('rgb')
const isImageLoading = ref(false)

const currentImageUrl = computed(() => {
  if (!selectedProject.value) return ''
  if (selectedFormula.value === 'rgb') {
    return `/api/task/odm-task-orthophoto/${selectedProject.value.id}`
  }
  return `/api/task/odm-task-spectral/${selectedProject.value.id}?formula=${selectedFormula.value}`
})

watch(selectedFormula, () => {
  isImageLoading.value = true
})
async function handleFileUpload(event: Event) {
  uploadList.value = []
  if (event) {
    const fileList = event.target?.files;
    for (const file of fileList) {
      const gps = await exifr.gps(file)
      if (!gps) {
        alert(`${file.name} 沒有GPS資訊`)
        event.target.value = '';
        break;
      }
      uploadList.value.push({
        name: file.name,
        size: (file.size / 1024 / 1024).toFixed(2) + 'MB',
        state: 'idle',
        latitude: gps.latitude,
        longitude: gps.longitude
      })
    }
  }
}
async function onProjectCreated(newProj: Project) {
  isCreatingProject.value = true
  try {
    const listRes = await fetch("/api/task/odm-task-list")
    const listData = await listRes.json()
    if (listRes.ok && listData.data) {
      projects.value = listData.data
    }
  } catch (err) {
    console.error("無法更新專案清單", err)
  }

  const found = projects.value.find((p) => p.id === newProj.id) || newProj
  if (newProj.fileNames && newProj.fileNames.length > 0) {
    currentUploadedFileNames.value = newProj.fileNames
  }
  selectedProject.value = found
  processingProject.value = found

  listenProgress(newProj.id, {
    onUpdate: (updated) => {
      if (selectedProject.value?.id === newProj.id && typeof updated.progress === 'number') {
        selectedProject.value.progress = updated.progress
      }
      if (processingProject.value?.id === newProj.id && typeof updated.progress === 'number') {
        processingProject.value.progress = updated.progress
      }
    },
    onComplete: () => {
      isCreatingProject.value = false
    },
    onError: () => {
      isCreatingProject.value = false
    },
  })
}


async function handleCancelStitching(id: string) {
  if (!confirm("確定要中斷航拍正射影像運算嗎？這將終止 NodeODM 拼圖運算並清理暫存。")) return
  const response = await fetch(`/api/task/odm-task/${id}`, {
    method: "DELETE",
  })
  if (!response.ok) {
    alert("中斷拼接任務失敗，請稍後再試")
    return
  }
  projects.value = projects.value.filter((p) => p.id !== id)
  if (selectedProject.value?.id === id) {
    await handleGoHome()
  }
}

async function handleDeleteProject(id: string) {
  if (!confirm("確定要刪除此專案嗎？")) return
  const response = await fetch(`/api/task/odm-task/${id}`, {
    method: "DELETE",
  })
  if (!response.ok) {
    alert("刪除專案失敗")
    return
  }
  projects.value = projects.value.filter((p) => p.id !== id)
  if (selectedProject.value?.id === id) {
    await handleGoHome()
  }
}

onMounted(async () => {
  window.addEventListener('resize', handleWindowResize)
  try {
    const formulasRes = await fetch("/api/task/odm-task-formulas")
    const formulasData = await formulasRes.json()
    if (formulasRes.ok && formulasData.data) {
      formulas.value = formulasData.data
    }
  } catch (err) {
    console.error("無法取得光譜演算法清單", err)
  }

  const response = await fetch("/api/task/odm-task-list")
  const data = await response.json()
  if (!response.ok) {
    return
  }
  projects.value = data.data
  processingProject.value = projects.value.find((p) => p.progress !== 100) || null
  if (processingProject.value) {
    const targetId = processingProject.value.id
    listenProgress(targetId, {
      onUpdate: (updated) => {
        if (processingProject.value?.id === targetId && typeof updated.progress === 'number') {
          processingProject.value.progress = updated.progress
        }
        if (selectedProject.value?.id === targetId && typeof updated.progress === 'number') {
          selectedProject.value.progress = updated.progress
        }
      },
      onComplete: () => {
        isCreatingProject.value = false
      },
    })
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleWindowResize)
})

watch(selectedProject, async (newProj) => {
  currentStep.value = 1
  uploadList.value = []
  selectedFormula.value = 'rgb'
  isImageLoading.value = true
  if (newProj?.id) {
    setScenario(newProj.scenario || null)
    await loadPlots(newProj.id)
  } else {
    setScenario(null)
  }
})

</script>

<template>
  <SidebarProvider :style="{
    '--sidebar-width': '350px',
  }">
    <AppSidebar v-model:is-creating-project="isCreatingProject" v-model:selected-project="selectedProject"
      v-model:projects="projects" />
    <SidebarInset>
      <header class="bg-background sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b px-4">
        <SidebarTrigger class="-ml-1 cursor-pointer" title="切換側邊欄" />
        <Separator orientation="vertical" class="mr-2 data-[orientation=vertical]:h-4" />
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink
                href="#"
                class="cursor-pointer font-medium"
                :class="{ 'text-foreground font-semibold': !selectedProject }"
                @click.prevent="handleGoHome"
              >
                主畫面
              </BreadcrumbLink>
            </BreadcrumbItem>
            <template v-if="selectedProject">
              <BreadcrumbSeparator class="hidden md:block" />
              <BreadcrumbItem>
                <BreadcrumbLink class="font-semibold text-foreground">
                  {{ selectedProject.name }}
                </BreadcrumbLink>
              </BreadcrumbItem>
            </template>
          </BreadcrumbList>
        </Breadcrumb>
        <Button
          v-if="selectedProject"
          variant="destructive"
          size="sm"
          class="ml-auto cursor-pointer"
          @click="handleDeleteProject(selectedProject.id)"
        >
          刪除專案
        </Button>
      </header>
      <!-- 當選定專案時的四步驟工作流 -->
      <div v-if="selectedProject" class="relative flex flex-1 flex-col h-[calc(100vh-theme(spacing.14))] overflow-hidden">
        <!-- 步驟 2：專案試驗情境特徵動態卡片 (可捲動表單) -->
        <div v-if="currentStep === 2" class="flex-1 min-h-0 overflow-y-auto p-6 pb-20 bg-muted/10 space-y-6">
          <div class="mx-auto max-w-5xl space-y-6">
            <ProjectScenarioCard
              :project-id="selectedProject.id"
              :project-name="selectedProject.name"
              :initial-scenario="selectedProject.scenario"
              :file-names="currentUploadedFileNames"
              :project-progress="selectedProject.progress"
              @update:scenario="onScenarioUpdated"
              @saved="onScenarioSaved"
            />
          </div>
        </div>

        <!-- 步驟 1、步驟 3 與步驟 4：Google 地圖式滿版暗場工作區 (Zero-Scroll 滿版黑底視圖) -->
        <div
          v-else-if="currentStep === 1 || currentStep === 3 || currentStep === 4"
          class="relative flex-1 min-h-0 w-full h-full bg-black overflow-hidden select-none"
        >
          <!-- 左上角懸浮專案資訊膠囊 HUD (Floating Project Info HUD) -->
          <div
            class="absolute top-4 left-4 z-20 flex flex-wrap items-center gap-3 rounded-2xl border border-white/15 bg-zinc-950/85 px-4 py-2 text-white shadow-2xl backdrop-blur-md"
          >
            <div class="flex flex-col">
              <span class="text-sm font-bold text-zinc-100 tracking-tight leading-tight">{{ selectedProject.name }}</span>
              <span class="font-mono text-[10px] text-zinc-400">ID: {{ selectedProject.id.slice(0, 13) }}...</span>
            </div>
            <div class="h-4 w-px bg-white/15" />
            <div class="flex items-center gap-1.5">
              <Badge :variant="selectedProject.progress === 100 ? 'default' : 'secondary'" class="text-xs">
                <CheckCircle2 v-if="selectedProject.progress === 100" class="size-3.5 mr-1" />
                <Spinner v-else class="size-3.5 mr-1 animate-spin" />
                {{ selectedProject.progress === 100 ? '已完成' : `處理中 (${selectedProject.progress ?? 0}%)` }}
              </Badge>
              <Badge variant="outline" class="text-xs text-zinc-300 border-white/20">
                <Images class="size-3.5 mr-1 text-zinc-400" />
                {{ selectedProject.images ?? 0 }} 張相片
              </Badge>
              <Badge
                v-if="selectedProject.progress === 100 && currentStep === 4"
                variant="outline"
                class="font-mono text-xs text-purple-300 border-purple-400/40 bg-purple-950/30"
              >
                {{ selectedFormula === 'rgb' ? '原始 (RGB)' : selectedFormula }}
              </Badge>
            </div>
          </div>

          <!-- 步驟 1 拼接運算中（進度未達 100%）：畫面中央毛玻璃進度對話卡 -->
          <div
            v-if="selectedProject.progress !== 100"
            class="absolute inset-0 z-30 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs"
          >
            <div class="w-full max-w-md rounded-2xl border border-white/15 bg-zinc-950/90 p-6 text-zinc-100 shadow-2xl backdrop-blur-md space-y-4">
              <div class="flex items-center justify-between text-sm">
                <span class="flex items-center gap-2 font-medium text-zinc-200">
                  <Spinner class="size-4 animate-spin text-purple-400" />
                  正射影像拼接運算中...
                </span>
                <span class="font-mono font-bold text-purple-400">{{ selectedProject.progress ?? 0 }}%</span>
              </div>
              <Progress :model-value="selectedProject.progress ?? 0" class="h-2 bg-white/10" />
              <p class="text-xs text-zinc-400 leading-relaxed">
                正在進行航拍特徵匹配與高解析度正射拼圖，完成後將在此直接顯示成果。您可先點擊下方切換按鈕前往「步驟 2：設定試驗情境」。
              </p>
              <div class="flex items-center justify-end gap-2 pt-1">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  class="h-8 gap-1.5 px-3 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive border-destructive/30 cursor-pointer"
                  @click="handleCancelStitching(selectedProject.id)"
                >
                  <XCircle class="size-3.5" />
                  <span>中斷拼接</span>
                </Button>
              </div>
            </div>
          </div>

          <!-- 左下角懸浮縮放 HUD 控制器 (Floating Zoom HUD) -->
          <div
            v-if="selectedProject.progress === 100"
            class="absolute bottom-4 left-4 z-20 flex items-center gap-1 rounded-xl border border-white/15 bg-zinc-950/85 p-1 text-zinc-200 shadow-2xl backdrop-blur-md"
          >
            <TooltipProvider :delay-duration="150">
              <Tooltip>
                <TooltipTrigger as-child>
                  <Button
                    size="sm"
                    variant="ghost"
                    class="size-7 p-0 cursor-pointer text-zinc-400 hover:text-white hover:bg-white/10"
                    @click="onZoomOut"
                  >
                    <ZoomOut class="size-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="top" class="text-xs">縮小視角</TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <span class="w-12 text-center font-mono text-xs font-semibold text-zinc-100 select-none">
              {{ viewport.zoomPercentage }}%
            </span>

            <TooltipProvider :delay-duration="150">
              <Tooltip>
                <TooltipTrigger as-child>
                  <Button
                    size="sm"
                    variant="ghost"
                    class="size-7 p-0 cursor-pointer text-zinc-400 hover:text-white hover:bg-white/10"
                    @click="onZoomIn"
                  >
                    <ZoomIn class="size-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="top" class="text-xs">放大視角</TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <div class="my-1 h-3.5 w-px bg-white/20" />

            <TooltipProvider :delay-duration="150">
              <Tooltip>
                <TooltipTrigger as-child>
                  <Button
                    size="sm"
                    variant="ghost"
                    class="h-7 gap-1 px-2 text-xs font-medium cursor-pointer text-zinc-300 hover:text-white hover:bg-white/10"
                    @click="onFitToScreen"
                  >
                    <Scan class="size-3.5" />
                    <span class="hidden sm:inline">最適大小</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="top" class="text-xs">重設為最適畫面尺寸 (Fit)</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          <!-- 右側垂直小畫家工具列 (僅步驟 3 顯示) -->
          <PlotToolbar
            v-if="selectedProject.progress === 100 && currentStep === 3"
            v-model:active-mode="activeMode"
            v-model:draw-tool="drawTool"
            :plots="plots"
            :selected-plot-number="selectedPlotNumber"
            :is-dirty="isDirty"
            :is-saving="isSaving"
            :is-drawing="isDrawing"
            :grid-state="gridState"
            class="absolute top-4 right-4 z-20"
            @save="handleSavePlots"
            @undo-point="plotCanvasOverlayRef?.undoLastPoint()"
            @cancel-drawing="plotCanvasOverlayRef?.cancelDrawing()"
            @delete-selected="selectedPlotNumber !== null && deletePlot(selectedPlotNumber)"
            @duplicate-selected="selectedPlotNumber !== null && handleDuplicatePlot(selectedPlotNumber)"
            @duplicate-all="handleDuplicateAll"
            @copy-to-clipboard="handleCopyToClipboard"
            @paste-from-clipboard="handlePasteFromClipboard"
            @open-copy-from-project="copyDialogOpen = true"
            @clear-all="handleClearAllPlots"
            @start-grid="startGridMode"
            @close-grid="closeGridMode"
            @confirm-grid="handleConfirmGrid"
            @clear-excluded-cells="clearExcludedGridCells"
            @update:grid-rows="gridState.rows = $event"
            @update:grid-cols="gridState.cols = $event"
            @update:grid-margin="gridState.marginRatio = $event; gridState.scaleX = Math.max(0.05, 1 - 2 * $event); gridState.scaleY = Math.max(0.05, 1 - 2 * $event)"
            @update:grid-scale-x="gridState.scaleX = $event; gridState.marginRatio = Number(((1 - $event) / 2).toFixed(3))"
            @update:grid-scale-y="gridState.scaleY = $event"
          />

          <!-- 右側懸浮公式快速切換按鈕群 (僅步驟 4 顯示) -->
          <div
            v-if="selectedProject.progress === 100 && currentStep === 4"
            class="absolute top-4 right-4 z-20 flex flex-col gap-1.5 rounded-2xl border border-white/15 bg-zinc-950/85 p-2 text-white shadow-2xl backdrop-blur-md"
          >
            <div class="flex items-center gap-1.5 px-2 py-1 text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
              <Layers class="size-3.5" />
              <span>光譜演算法</span>
            </div>
            <div class="flex flex-col gap-1 max-h-[320px] overflow-y-auto pr-0.5">
              <TooltipProvider :delay-duration="150">
                <Tooltip>
                  <TooltipTrigger as-child>
                    <Button
                      size="sm"
                      :variant="selectedFormula === 'rgb' ? 'default' : 'outline'"
                      class="h-8 justify-start gap-2 px-3 text-xs font-medium border-white/15 cursor-pointer"
                      @click="selectedFormula = 'rgb'"
                    >
                      <span
                        class="size-2 rounded-full"
                        :class="selectedFormula === 'rgb' ? 'bg-primary-foreground' : 'bg-emerald-500'"
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
                v-for="f in formulas"
                :key="f.id"
                :delay-duration="150"
              >
                <Tooltip>
                  <TooltipTrigger as-child>
                    <Button
                      size="sm"
                      :variant="selectedFormula === f.id ? 'default' : 'outline'"
                      class="h-8 justify-between gap-3 px-3 text-xs font-medium border-white/15 cursor-pointer"
                      @click="selectedFormula = f.id"
                    >
                      <span class="font-semibold">{{ f.id }}</span>
                      <span
                        v-if="selectedFormula === f.id"
                        class="size-1.5 rounded-full bg-primary-foreground animate-pulse"
                      />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="left" class="max-w-xs space-y-1 p-2 text-xs">
                    <p class="font-bold text-foreground">{{ f.id }}</p>
                    <p v-if="f.help" class="text-muted-foreground leading-relaxed">{{ f.help }}</p>
                    <p v-if="f.expr" class="font-mono text-[10px] text-muted-foreground/80 bg-muted/60 px-1.5 py-0.5 rounded">
                      公式: {{ f.expr }}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>

          <!-- 影像載入中遮罩 -->
          <div
            v-if="isImageLoading && selectedProject.progress === 100"
            class="absolute inset-0 z-25 flex flex-col items-center justify-center bg-black/60 backdrop-blur-xs"
          >
            <Spinner class="size-8 animate-spin text-purple-400" />
            <span class="mt-2 text-xs font-medium text-zinc-300">正射影像載入中...</span>
          </div>

          <!-- 正射影像與小區多邊形滿版黑底視角容器 -->
          <div
            ref="viewportRef"
            class="relative w-full h-full overflow-hidden select-none bg-black"
          >
            <img
              v-if="selectedProject.progress === 100"
              ref="imageRef"
              class="absolute top-0 left-0 max-w-none max-h-none pointer-events-none select-none transition-opacity duration-150"
              :class="{ 'opacity-40': isImageLoading }"
              :style="{
                width: `${viewport.baseWidth.value}px`,
                height: `${viewport.baseHeight.value}px`,
                transform: `translate3d(${viewport.panX.value}px, ${viewport.panY.value}px, 0) scale(${viewport.scale.value})`,
                transformOrigin: '0 0',
                imageRendering: 'auto',
              }"
              :src="currentImageUrl"
              :alt="selectedProject.name"
              @load="onImageLoaded"
              @error="isImageLoading = false"
            />
            <PlotCanvasOverlay
              v-if="selectedProject.progress === 100"
              ref="plotCanvasOverlayRef"
              :plots="currentStep === 3 || currentStep === 4 ? plots : []"
              :active-mode="currentStep === 3 ? activeMode : 'view'"
              :draw-tool="currentStep === 3 ? drawTool : 'select'"
              :selected-plot-number="currentStep === 3 || currentStep === 4 ? selectedPlotNumber : null"
              :get-plot-color="getPlotColor"
              :viewport="viewport"
              :grid-state="currentStep === 3 ? gridState : { isActive: false, corners: [], rows: 3, cols: 3, marginRatio: 0.1, scaleX: 0.8, scaleY: 0.8, paddingRatio: 0, offsetX: 0, offsetY: 0, excludedIndices: [] }"
              :preview-plots="currentStep === 3 ? previewGridPlots : []"
              @plot-drawn="onPlotDrawn"
              @edit-plot="onEditPlot"
              @update-plot-points="onUpdatePlotPoints"
              @select-plot="onSelectPlot"
              @update-grid-corner="updateGridCorner($event.index, $event.point)"
              @delete-plot="deletePlot"
              @duplicate-plot="handleDuplicatePlot"
              @move-plot="movePlot($event.plotNumber, $event.delta)"
              @toggle-exclude-grid-cell="toggleExcludeGridCell"
            />
          </div>

          <PlotTreatmentDialog
            v-if="currentStep === 3"
            v-model:open="treatmentDialogState.open"
            :plot-number="treatmentDialogState.plotNumber"
            :is-new-plot="treatmentDialogState.isNewPlot"
            :initial-treatment="treatmentDialogState.initialTreatment"
            :initial-dose="treatmentDialogState.initialDose"
            :initial-is-control="treatmentDialogState.initialIsControl"
            :existing-treatments="existingTreatments"
            @confirm="onDialogConfirm"
            @cancel="onDialogCancel"
            @delete="onDialogDelete"
          />

          <CopyPlotsDialog
            v-if="currentStep === 3"
            v-model:open="copyDialogOpen"
            :projects="projects"
            :current-project-id="selectedProject?.id"
            @confirm="handleConfirmCopyFromProject"
          />
        </div>

        <!-- 全步驟共用置底懸浮步驟切換膠囊 (Floating Step Navigation HUD) -->
        <div class="absolute bottom-4 left-1/2 -translate-x-1/2 z-30 pointer-events-auto">
          <StepNavigationHUD
            :current-step="currentStep"
            :project-progress="selectedProject.progress"
            :has-plots="plots.length > 0"
            @change-step="handleStepChange"
          />
        </div>
      </div>
      <div v-if="!selectedProject" class="h-[calc(100vh-3.5rem)] w-full overflow-hidden">
        <DroneHomeUpload @project-created="onProjectCreated" />
      </div>
    </SidebarInset>
  </SidebarProvider>
  <!-- 懸浮 Persona AI 代理人組件 (手動全流程測試暫時停用) -->
  <!--
  <FloatingPersona
    :project-id="selectedProject?.id"
    :project-name="selectedProject?.name"
    :selected-formula="selectedFormula"
    :project-progress="selectedProject?.progress"
    :has-plots="plots.length > 0"
    :is-home="!selectedProject"
    :current-step="currentStep"
  />
  -->
</template>
