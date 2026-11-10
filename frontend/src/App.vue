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
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import FloatingPersona from './components/FloatingPersona.vue'
import DroneHomeUpload from './components/DroneHomeUpload.vue'
import ProjectScenarioCard, { type ScenarioData } from './components/ProjectScenarioCard.vue'
import PlotToolbar from './components/PlotToolbar.vue'
import PlotCanvasOverlay from './components/PlotCanvasOverlay.vue'
import PlotTreatmentDialog, { type TreatmentData } from './components/PlotTreatmentDialog.vue'
import TaskStepper from './components/TaskStepper.vue'
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
  const container = viewportRef.value || orthoContainerRef.value
  const img = imageRef.value
  if (!container || !img) return
  viewport.fitToViewport(
    container.clientWidth,
    container.clientHeight,
    img.naturalWidth || 1,
    img.naturalHeight || 1,
    16
  )
  nextTick(() => {
    plotCanvasOverlayRef.value?.syncCanvasSize()
  })
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

const currentStep = ref<1 | 2 | 3>(1)

function isStepUnlocked(stepId: 1 | 2 | 3): boolean {
  if (stepId === 1 || stepId === 2) return true
  return (selectedProject.value?.progress ?? 0) === 100
}

function canSafelyLeaveStep3(): boolean {
  if (currentStep.value === 3 && isDirty.value) {
    return window.confirm('小區標註尚有未儲存的變更，確定要切換步驟嗎？（建議先點擊「儲存小區」以保留進度）')
  }
  return true
}

function handleStepChange(targetStep: 1 | 2 | 3) {
  if (targetStep === currentStep.value) return
  if (!isStepUnlocked(targetStep)) {
    alert(`需待正射影像拼接完成（目前進度 ${selectedProject.value?.progress ?? 0}%）方可進入小區標註步驟`)
    return
  }
  if (currentStep.value === 3 && !canSafelyLeaveStep3()) {
    return
  }
  currentStep.value = targetStep
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
      <div v-if="selectedProject" class="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
        <!-- 專案工作流三步驟導覽指示條 -->
        <TaskStepper
          :current-step="currentStep"
          :project-progress="selectedProject.progress"
          @change-step="handleStepChange"
        />

        <!-- 步驟 1 與步驟 3：專案主卡片（動態切換：拼接中進度條 / 拼接完成正射圖檢視與小區標註） -->
        <Card v-if="currentStep === 1 || currentStep === 3">
          <CardHeader class="flex flex-row items-center justify-between pb-3">
            <div class="space-y-1">
              <CardTitle class="text-xl font-bold">{{ selectedProject.name }}</CardTitle>
              <CardDescription class="font-mono text-xs text-muted-foreground">
                ID: {{ selectedProject.id }}
              </CardDescription>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <Badge :variant="selectedProject.progress === 100 ? 'default' : 'secondary'">
                <CheckCircle2 v-if="selectedProject.progress === 100" class="size-3.5 mr-1" />
                <Spinner v-else class="size-3.5 mr-1 animate-spin" />
                {{ selectedProject.progress === 100 ? '已完成' : `處理中 (${selectedProject.progress ?? 0}%)` }}
              </Badge>
              <Badge variant="outline" class="text-xs">
                <Images class="size-3.5 mr-1 text-muted-foreground" />
                {{ selectedProject.images ?? 0 }} 張相片
              </Badge>
              <Badge
                v-if="selectedProject.progress === 100"
                data-tour="formula-selector"
                variant="outline"
                class="font-mono text-xs"
              >
                目前顯示：{{ selectedFormula === 'rgb' ? '原始正射影像 (RGB)' : selectedFormula }}
              </Badge>
            </div>
          </CardHeader>

          <!-- 拼接運算中（進度未達 100%）：顯示進度條、提示與中斷按鈕 -->
          <CardContent v-if="selectedProject.progress !== 100" class="space-y-4 pt-2">
            <div class="space-y-3 rounded-lg border border-dashed bg-muted/20 p-6 text-center">
              <div class="mx-auto flex max-w-lg flex-col gap-4">
                <div class="flex items-center justify-between text-sm">
                  <span class="flex items-center gap-1.5 font-medium text-foreground">
                    <Spinner class="size-4 animate-spin text-primary" />
                    正射影像拼接運算中...
                  </span>
                  <span class="font-mono font-semibold text-primary">{{ selectedProject.progress ?? 0 }}%</span>
                </div>
                <Progress :model-value="selectedProject.progress ?? 0" class="h-2" />
                <div class="flex items-center justify-between gap-4 pt-1">
                  <p class="text-xs text-muted-foreground text-left">
                    正在進行航拍特徵匹配與高解析度正射拼圖，完成後將在此直接顯示成果。您可先點擊下方按鈕前往「步驟 2：設定試驗情境」。
                  </p>
                  <Button
                    data-tour="cancel-stitching"
                    type="button"
                    variant="outline"
                    size="sm"
                    class="h-8 gap-1.5 px-3 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive border-destructive/30 shrink-0 cursor-pointer"
                    @click="handleCancelStitching(selectedProject.id)"
                  >
                    <XCircle class="size-3.5" />
                    <span>中斷拼接</span>
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>

          <!-- 小區多邊形分割與處理組工具列 (僅步驟 3 顯示) -->
          <PlotToolbar
            v-if="currentStep === 3"
            v-model:active-mode="activeMode"
            v-model:draw-tool="drawTool"
            :plots="plots"
            :selected-plot-number="selectedPlotNumber"
            :is-dirty="isDirty"
            :is-saving="isSaving"
            :is-drawing="isDrawing"
            :grid-state="gridState"
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

          <CardContent v-if="selectedProject.progress === 100" class="p-4">
            <div
              ref="orthoContainerRef"
              class="relative flex flex-col w-full overflow-hidden select-none min-h-[460px] h-[68vh] rounded-lg border bg-muted/20 p-1"
            >
              <!-- 右下角懸浮縮放 HUD 控制器 (Floating Zoom HUD) -->
              <div
                class="absolute bottom-4 right-4 z-30 flex items-center gap-1 rounded-xl border border-border/80 bg-background/85 p-1 shadow-lg backdrop-blur-md"
              >
                <TooltipProvider :delay-duration="150">
                  <Tooltip>
                    <TooltipTrigger as-child>
                      <Button
                        size="sm"
                        variant="ghost"
                        class="size-7 p-0 cursor-pointer text-muted-foreground hover:text-foreground"
                        @click="onZoomOut"
                      >
                        <ZoomOut class="size-3.5" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="top" class="text-xs">縮小視角</TooltipContent>
                  </Tooltip>
                </TooltipProvider>

                <span class="w-12 text-center font-mono text-xs font-semibold text-foreground select-none">
                  {{ viewport.zoomPercentage }}%
                </span>

                <TooltipProvider :delay-duration="150">
                  <Tooltip>
                    <TooltipTrigger as-child>
                      <Button
                        size="sm"
                        variant="ghost"
                        class="size-7 p-0 cursor-pointer text-muted-foreground hover:text-foreground"
                        @click="onZoomIn"
                      >
                        <ZoomIn class="size-3.5" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="top" class="text-xs">放大視角</TooltipContent>
                  </Tooltip>
                </TooltipProvider>

                <div class="my-1 h-3.5 w-px bg-border/60" />

                <TooltipProvider :delay-duration="150">
                  <Tooltip>
                    <TooltipTrigger as-child>
                      <Button
                        size="sm"
                        variant="ghost"
                        class="h-7 gap-1 px-2 text-xs font-medium cursor-pointer text-muted-foreground hover:text-foreground"
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

              <!-- 懸浮公式快速切換按鈕群 (Floating Formula Switcher) -->
              <div
                class="absolute top-3 right-3 z-20 flex flex-col gap-1.5 rounded-xl border border-border/80 bg-background/85 p-1.5 shadow-lg backdrop-blur-md">
                <div class="flex items-center gap-1.5 px-2 py-1 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
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
                          class="h-8 justify-start gap-2 px-3 text-xs font-medium shadow-xs transition-all"
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

                  <div class="my-0.5 h-px bg-border/60" />

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
                          class="h-8 justify-between gap-3 px-3 text-xs font-medium shadow-xs transition-all"
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
              <div v-if="isImageLoading"
                class="absolute inset-0 z-25 flex flex-col items-center justify-center bg-background/60 backdrop-blur-xs">
                <Spinner class="size-8 animate-spin text-primary" />
                <span class="mt-2 text-xs font-medium text-muted-foreground">影像載入中...</span>
              </div>

              <!-- 正射影像與小區多邊形視角容器 -->
              <div
                ref="viewportRef"
                class="relative flex-1 w-full h-full overflow-hidden select-none"
              >
                <img
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
                >
                <PlotCanvasOverlay
                  ref="plotCanvasOverlayRef"
                  :plots="currentStep === 3 ? plots : []"
                  :active-mode="currentStep === 3 ? activeMode : 'view'"
                  :draw-tool="drawTool"
                  :selected-plot-number="currentStep === 3 ? selectedPlotNumber : null"
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
            </div>
          </CardContent>

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
        </Card>

        <!-- 步驟 2：專案試驗情境特徵動態卡片 (僅步驟 2 顯示) -->
        <ProjectScenarioCard
          v-if="currentStep === 2"
          :project-id="selectedProject.id"
          :project-name="selectedProject.name"
          :initial-scenario="selectedProject.scenario"
          :file-names="currentUploadedFileNames"
          :project-progress="selectedProject.progress"
          @update:scenario="onScenarioUpdated"
          @saved="onScenarioSaved"
        />
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
