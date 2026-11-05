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
import PlotToolbar from './components/PlotToolbar.vue'
import PlotCanvasOverlay from './components/PlotCanvasOverlay.vue'
import PlotTreatmentDialog, { type TreatmentData } from './components/PlotTreatmentDialog.vue'
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
  startGridMode,
  closeGridMode,
  updateGridCorner,
  detectMarkers,
  computeGridPlots,
  confirmBatchGenerate,
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

const drawTool = ref<'rect' | 'polygon'>('rect')

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
  const maxNum = plots.value.reduce((acc, cur) => Math.max(acc, cur.plot_number), 0)
  treatmentDialogState.value = {
    open: true,
    isNewPlot: true,
    plotNumber: maxNum + 1,
    points,
    initialTreatment: '',
    initialDose: '',
    initialIsControl: false,
  }
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

async function handleGoHome() {
  if (isDirty.value) {
    if (!confirm('您有未儲存的小區設定，是否確定返回主畫面？未儲存的變更將會遺失。')) {
      return
    }
  }
  selectedProject.value = null
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
}

const projects = ref<Project[]>([])
const selectedProject = ref<Project | null>(null)
const processingProject = ref<Project | null>(null)
const uploadList = ref<UploadItem[]>([])
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
  uploadList.value = []
  selectedFormula.value = 'rgb'
  isImageLoading.value = true
  if (newProj?.id) {
    await loadPlots(newProj.id)
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
      <header v-if="selectedProject" class="bg-background sticky top-0 flex shrink-0 items-center gap-2 border-b p-4">
        <SidebarTrigger class="-ml-1" />
        <Separator orientation="vertical" class="mr-2 data-[orientation=vertical]:h-4" />
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem class="hidden md:block">
              <BreadcrumbLink href="#" class="cursor-pointer" @click.prevent="handleGoHome">
                主畫面
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator class="hidden md:block" />
            <BreadcrumbItem>
              <BreadcrumbLink>
                {{ selectedProject.name }}
              </BreadcrumbLink>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
        <Button variant="destructive" size="sm" class="ml-auto" @click="handleDeleteProject(selectedProject.id)">
          刪除專案
        </Button>
      </header>
      <div v-if="selectedProject" class="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
        <!-- 專案資訊卡片 -->
        <Card>
          <CardHeader class="pb-3">
            <div class="flex items-start justify-between gap-4">
              <div class="space-y-1">
                <CardTitle class="text-xl font-bold">{{ selectedProject.name }}</CardTitle>
                <CardDescription class="font-mono text-xs text-muted-foreground">
                  ID: {{ selectedProject.id }}
                </CardDescription>
              </div>
              <Badge :variant="selectedProject.progress === 100 ? 'default' : 'secondary'">
                <CheckCircle2 v-if="selectedProject.progress === 100" class="size-3.5 mr-1" />
                <Spinner v-else class="size-3.5 mr-1 animate-spin" />
                {{ selectedProject.progress === 100 ? '已完成' : `處理中 (${selectedProject.progress ?? 0}%)` }}
              </Badge>
            </div>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex flex-wrap items-center gap-6 text-sm text-muted-foreground">
              <div class="flex items-center gap-2">
                <Images class="size-4" />
                <span>圖片數量：<strong class="text-foreground">{{ selectedProject.images ?? 0 }}</strong> 張</span>
              </div>
              <div class="flex items-center gap-2">
                <Clock class="size-4" />
                <span>運算進度：<strong class="text-foreground">{{ selectedProject.progress ?? 0 }}%</strong></span>
              </div>
            </div>

            <!-- 處理中進度條 -->
            <div v-if="selectedProject.progress !== 100" class="space-y-2 pt-2">
              <Progress :model-value="selectedProject.progress ?? 0" />
              <p class="text-xs text-muted-foreground">正在進行航拍正射影像運算，請稍候...</p>
            </div>
          </CardContent>
        </Card>

        <!-- 正射影像成果卡片 -->
        <Card v-if="selectedProject.progress === 100">
          <CardHeader class="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle class="text-lg">正射影像成果 (Orthophoto)</CardTitle>
              <CardDescription>拼接完成的空拍高解析度影像與植生指標運算</CardDescription>
            </div>
            <div class="flex items-center gap-2">
              <Badge variant="outline" class="font-mono text-xs">
                目前顯示：{{ selectedFormula === 'rgb' ? '原始正射影像 (RGB)' : selectedFormula }}
              </Badge>
            </div>
          </CardHeader>

          <!-- 小區多邊形分割與處理組工具列 -->
          <PlotToolbar
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
            @start-grid="startGridMode"
            @close-grid="closeGridMode"
            @detect-markers="handleDetectMarkers"
            @confirm-grid="handleConfirmGrid"
            @update:grid-rows="gridState.rows = $event"
            @update:grid-cols="gridState.cols = $event"
            @update:grid-margin="gridState.marginRatio = $event"
          />

          <CardContent class="p-4">
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
                  :plots="plots"
                  :active-mode="activeMode"
                  :draw-tool="drawTool"
                  :selected-plot-number="selectedPlotNumber"
                  :get-plot-color="getPlotColor"
                  :viewport="viewport"
                  :grid-state="gridState"
                  :preview-plots="previewGridPlots"
                  @plot-drawn="onPlotDrawn"
                  @edit-plot="onEditPlot"
                  @update-plot-points="onUpdatePlotPoints"
                  @select-plot="onSelectPlot"
                  @update-grid-corner="updateGridCorner($event.index, $event.point)"
                />
              </div>
            </div>
          </CardContent>

          <PlotTreatmentDialog
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
        </Card>

        <!-- 運算中提示 -->
        <Card v-else class="border-dashed p-8 text-center text-muted-foreground">
          <div class="flex flex-col items-center justify-center gap-3">
            <Spinner class="size-8 animate-spin text-primary" />
            <div class="text-sm font-medium text-foreground">正射影像生成中...</div>
            <p class="text-xs text-muted-foreground">任務完成後將在此自動顯示拼接成果影像</p>
          </div>
        </Card>
      </div>
      <div v-if="!selectedProject" class="h-[calc(100vh-1rem)] w-full">
        <DroneHomeUpload @project-created="onProjectCreated" />
      </div>
    </SidebarInset>
  </SidebarProvider>
  <!-- 懸浮 Persona AI 代理人組件 (全域常駐) -->
  <FloatingPersona
    :project-id="selectedProject?.id"
    :project-name="selectedProject?.name"
    :selected-formula="selectedFormula"
    :project-progress="selectedProject?.progress"
    :has-plots="plots.length > 0"
    :is-home="!selectedProject"
  />
</template>
