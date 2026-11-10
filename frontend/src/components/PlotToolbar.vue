<script setup lang="ts">
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import {
  MousePointer,
  Pencil,
  Square,
  Pentagon,
  Save,
  RotateCcw,
  X,
  Trash2,
  Grid,
  Check,
  Link,
  Unlink,
  Eraser,
  Copy,
  ClipboardCopy,
  ChevronRight,
  Minus,
} from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import type { PlotItem, GridGeneratorState } from '@/lib/usePlots'

const props = defineProps<{
  plots: PlotItem[]
  activeMode: 'view' | 'draw'
  drawTool: 'rect' | 'polygon' | 'eraser'
  selectedPlotNumber: number | null
  selectedPlotNumbers?: number[]
  isDirty: boolean
  isSaving: boolean
  isDrawing: boolean
  gridState?: GridGeneratorState
}>()

const hasSelection = computed(() => {
  if (props.selectedPlotNumbers && props.selectedPlotNumbers.length > 0) return true
  return props.selectedPlotNumber !== null
})

const selectionCount = computed(() => {
  if (props.selectedPlotNumbers && props.selectedPlotNumbers.length > 0) return props.selectedPlotNumbers.length
  return props.selectedPlotNumber !== null ? 1 : 0
})

const emit = defineEmits<{
  (e: 'update:activeMode', mode: 'view' | 'draw'): void
  (e: 'update:drawTool', tool: 'rect' | 'polygon' | 'eraser'): void
  (e: 'save'): void
  (e: 'undo-point'): void
  (e: 'cancel-drawing'): void
  (e: 'delete-selected'): void
  (e: 'duplicate-selected'): void
  (e: 'duplicate-all'): void
  (e: 'copy-to-clipboard'): void
  (e: 'paste-from-clipboard'): void
  (e: 'open-copy-from-project'): void
  (e: 'clear-all'): void
  (e: 'start-grid'): void
  (e: 'close-grid'): void
  (e: 'confirm-grid'): void
  (e: 'clear-excluded-cells'): void
  (e: 'update:grid-rows', rows: number): void
  (e: 'update:grid-cols', cols: number): void
  (e: 'update:grid-margin', margin: number): void
  (e: 'update:grid-scale-x', scaleX: number): void
  (e: 'update:grid-scale-y', scaleY: number): void
}>()

const isLinked = ref(true)

const currentScaleX = computed(() => {
  if (props.gridState?.scaleX !== undefined) return Math.round(props.gridState.scaleX * 100)
  if (props.gridState?.marginRatio !== undefined) return Math.round((1 - 2 * props.gridState.marginRatio) * 100)
  return 40
})

const currentScaleY = computed(() => {
  if (props.gridState?.scaleY !== undefined) return Math.round(props.gridState.scaleY * 100)
  if (props.gridState?.marginRatio !== undefined) return Math.round((1 - 2 * props.gridState.marginRatio) * 100)
  return 40
})

function handleScaleXChange(val: number) {
  const s = Math.max(5, Math.min(100, val)) / 100
  emit('update:grid-scale-x', s)
  if (isLinked.value) {
    emit('update:grid-scale-y', s)
  }
}

function handleScaleYChange(val: number) {
  const s = Math.max(5, Math.min(100, val)) / 100
  emit('update:grid-scale-y', s)
  if (isLinked.value) {
    emit('update:grid-scale-x', s)
  }
}

function setMode(mode: 'view' | 'draw') {
  if (props.gridState?.isActive) {
    emit('close-grid')
  }
  emit('update:activeMode', mode)
}

function setDrawTool(tool: 'rect' | 'polygon' | 'eraser') {
  emit('update:drawTool', tool)
}

function toggleEraserInGrid() {
  if (props.drawTool === 'eraser') {
    emit('update:drawTool', 'rect')
  } else {
    emit('update:drawTool', 'eraser')
  }
}

function toggleGridMode() {
  if (props.gridState?.isActive) {
    emit('close-grid')
  } else {
    emit('start-grid')
  }
}

// 網格配置面板自由拖曳與最小化狀態
const isMinimized = ref(false)
const dragOffset = ref({ x: 0, y: 0 })
const panelRef = ref<HTMLElement | null>(null)

let startPointer = { x: 0, y: 0 }
let initialOffset = { x: 0, y: 0 }
let hasDragged = false

watch(
  () => props.gridState?.isActive,
  (active) => {
    if (active) {
      dragOffset.value = { x: 0, y: 0 }
      isMinimized.value = false
    }
  }
)

function startPanelDrag(e: PointerEvent) {
  if (e.button !== 0) return
  e.stopPropagation()

  startPointer = { x: e.clientX, y: e.clientY }
  initialOffset = { ...dragOffset.value }
  hasDragged = false

  window.addEventListener('pointermove', onPanelPointerMove)
  window.addEventListener('pointerup', onPanelPointerUp)
}

function onPanelPointerMove(e: PointerEvent) {
  const dx = e.clientX - startPointer.x
  const dy = e.clientY - startPointer.y
  if (!hasDragged && Math.hypot(dx, dy) > 4) {
    hasDragged = true
  }
  if (!hasDragged) return

  applyClampedOffset(initialOffset.x + dx, initialOffset.y + dy)
}

function applyClampedOffset(targetX: number, targetY: number) {
  if (!panelRef.value) {
    dragOffset.value = { x: targetX, y: targetY }
    return
  }

  const pad = 12
  const rect = panelRef.value.getBoundingClientRect()
  const baseLeft = rect.left - dragOffset.value.x
  const baseTop = rect.top - dragOffset.value.y

  const minX = pad - baseLeft
  const maxX = window.innerWidth - pad - rect.width - baseLeft
  const minY = pad - baseTop
  const maxY = window.innerHeight - pad - rect.height - baseTop

  dragOffset.value = {
    x: Math.round(Math.max(minX, Math.min(maxX, targetX))),
    y: Math.round(Math.max(minY, Math.min(maxY, targetY))),
  }
}

function onPanelPointerUp() {
  window.removeEventListener('pointermove', onPanelPointerMove)
  window.removeEventListener('pointerup', onPanelPointerUp)

  if (!hasDragged && isMinimized.value) {
    expandPanel()
  }
}

function expandPanel() {
  isMinimized.value = false
  nextTick(() => {
    applyClampedOffset(dragOffset.value.x, dragOffset.value.y)
  })
}

function minimizePanel() {
  isMinimized.value = true
  nextTick(() => {
    applyClampedOffset(dragOffset.value.x, dragOffset.value.y)
  })
}

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onPanelPointerMove)
  window.removeEventListener('pointerup', onPanelPointerUp)
})
</script>

<template>
  <div class="select-none pointer-events-none">
    <!-- 右側垂直直列主工具列 (小畫家樣式) -->
    <div
      class="flex flex-col items-center gap-1.5 rounded-2xl border border-white/15 bg-zinc-950/85 p-1.5 shadow-2xl backdrop-blur-md pointer-events-auto"
    >
      <TooltipProvider :delay-duration="120">
        <!-- 選取與檢視模式按鈕 -->
        <Tooltip>
          <TooltipTrigger as-child>
            <Button
              size="icon"
              variant="ghost"
              class="size-9 rounded-xl transition-all cursor-pointer"
              :class="activeMode === 'view' && !gridState?.isActive ? 'bg-white/20 text-white font-bold shadow-xs' : 'text-zinc-400 hover:text-white hover:bg-white/10'"
              @click="setMode('view')"
            >
              <MousePointer class="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left" class="text-xs">
            選取與檢視模式 (單擊選取小區、快點 2 下編輯特徵)
          </TooltipContent>
        </Tooltip>

        <!-- 手動繪製模式按鈕 -->
        <Tooltip>
          <TooltipTrigger as-child>
            <Button
              size="icon"
              variant="ghost"
              class="size-9 rounded-xl transition-all cursor-pointer"
              :class="activeMode === 'draw' && !gridState?.isActive ? 'bg-blue-600 text-white font-bold shadow-xs' : 'text-zinc-400 hover:text-white hover:bg-white/10'"
              @click="setMode('draw')"
            >
              <Pencil class="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left" class="text-xs">
            手動繪製模式 (矩形拉框 / 多邊形逐點)
          </TooltipContent>
        </Tooltip>

        <!-- 一鍵網格生成按鈕 -->
        <Tooltip>
          <TooltipTrigger as-child>
            <Button
              data-tour="grid-mode"
              size="icon"
              variant="ghost"
              class="size-9 rounded-xl transition-all cursor-pointer"
              :class="gridState?.isActive ? 'bg-purple-600 text-white font-bold ring-2 ring-purple-400/50 shadow-xs' : 'text-zinc-400 hover:text-white hover:bg-white/10'"
              @click="toggleGridMode"
            >
              <Grid class="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left" class="text-xs">
            一鍵自動網格剖分 (雙線性插值批次生成)
          </TooltipContent>
        </Tooltip>

        <!-- 手動繪製模式下的二級幾何工具組 -->
        <template v-if="activeMode === 'draw' && !gridState?.isActive">
          <div class="my-0.5 h-px w-5 bg-white/15" />

          <!-- 矩形拉框 -->
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                size="icon"
                variant="ghost"
                class="size-8 rounded-lg transition-all cursor-pointer"
                :class="drawTool === 'rect' ? 'bg-blue-500/30 text-blue-300 ring-1 ring-blue-400/60' : 'text-zinc-400 hover:text-white hover:bg-white/10'"
                @click="setDrawTool('rect')"
              >
                <Square class="size-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left" class="text-xs">
              矩形拉框：按住滑鼠左鍵拖曳秒速框劃小區
            </TooltipContent>
          </Tooltip>

          <!-- 多邊形逐點 -->
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                size="icon"
                variant="ghost"
                class="size-8 rounded-lg transition-all cursor-pointer"
                :class="drawTool === 'polygon' ? 'bg-amber-500/30 text-amber-300 ring-1 ring-amber-400/60' : 'text-zinc-400 hover:text-white hover:bg-white/10'"
                @click="setDrawTool('polygon')"
              >
                <Pentagon class="size-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left" class="text-xs">
              多邊形：逐點點選頂點，點擊起點或雙擊閉合
            </TooltipContent>
          </Tooltip>

          <!-- 橡皮擦 -->
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                size="icon"
                variant="ghost"
                class="size-8 rounded-lg transition-all cursor-pointer"
                :class="drawTool === 'eraser' ? 'bg-rose-500/30 text-rose-300 ring-1 ring-rose-400/60' : 'text-zinc-400 hover:text-white hover:bg-white/10'"
                @click="setDrawTool('eraser')"
              >
                <Eraser class="size-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left" class="text-xs">
              橡皮擦：點擊任意小區即可快速刪除消除
            </TooltipContent>
          </Tooltip>
        </template>

        <div class="my-0.5 h-px w-5 bg-white/15" />

        <!-- 複製網格下拉選單 (左向展開) -->
        <DropdownMenu>
          <Tooltip>
            <TooltipTrigger as-child>
              <DropdownMenuTrigger as-child>
                <Button
                  size="icon"
                  variant="ghost"
                  class="size-9 rounded-xl text-zinc-400 hover:text-white hover:bg-white/10 transition-all cursor-pointer"
                >
                  <Copy class="size-4" />
                </Button>
              </DropdownMenuTrigger>
            </TooltipTrigger>
            <TooltipContent side="left" class="text-xs">
              複製與剪貼簿網格工具
            </TooltipContent>
          </Tooltip>
          <DropdownMenuContent side="left" align="center" class="w-56 text-xs bg-zinc-900 border-zinc-700 text-zinc-200">
            <DropdownMenuItem
              :disabled="plots.length === 0"
              class="cursor-pointer gap-2 py-1.5 focus:bg-zinc-800 focus:text-white"
              @click="emit('duplicate-all')"
            >
              <Copy class="size-3.5 text-blue-400" />
              <span>複製全部小區 (位移副本)</span>
            </DropdownMenuItem>

            <DropdownMenuItem
              :disabled="plots.length === 0"
              class="cursor-pointer gap-2 py-1.5 focus:bg-zinc-800 focus:text-white"
              @click="emit('copy-to-clipboard')"
            >
              <ClipboardCopy class="size-3.5 text-emerald-400" />
              <span>複製小區到剪貼簿</span>
            </DropdownMenuItem>

            <DropdownMenuItem
              class="cursor-pointer gap-2 py-1.5 focus:bg-zinc-800 focus:text-white"
              @click="emit('paste-from-clipboard')"
            >
              <Copy class="size-3.5 text-purple-400" />
              <span>貼上剪貼簿網格</span>
            </DropdownMenuItem>

            <DropdownMenuSeparator class="bg-zinc-700" />

            <DropdownMenuItem
              class="cursor-pointer gap-2 py-1.5 focus:bg-zinc-800 focus:text-white"
              @click="emit('open-copy-from-project')"
            >
              <Grid class="size-3.5 text-amber-400" />
              <span>從歷史專案複製網格...</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <!-- 繪製中控制項 (多邊形復原點與放棄) -->
        <template v-if="isDrawing && drawTool === 'polygon'">
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                size="icon"
                variant="ghost"
                class="size-8 rounded-lg text-zinc-300 hover:text-white hover:bg-white/10 cursor-pointer"
                @click="emit('undo-point')"
              >
                <RotateCcw class="size-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left" class="text-xs">復原上一個頂點</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                size="icon"
                variant="ghost"
                class="size-8 rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-500/20 cursor-pointer"
                @click="emit('cancel-drawing')"
              >
                <X class="size-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left" class="text-xs">放棄本次繪製</TooltipContent>
          </Tooltip>
        </template>

        <!-- 選取小區時的快捷操作 (複製 / 刪除) -->
        <template v-if="hasSelection && !isDrawing">
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                size="icon"
                variant="ghost"
                class="size-8 rounded-lg text-blue-400 hover:text-blue-300 hover:bg-blue-500/20 cursor-pointer"
                @click="emit('duplicate-selected')"
              >
                <Copy class="size-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left" class="text-xs">
              {{ selectionCount > 1 ? `複製選取的 ${selectionCount} 個小區 (Ctrl+C)` : `複製選取小區 #${selectedPlotNumber} (Ctrl+C)` }}
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                size="icon"
                variant="ghost"
                class="size-8 rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-500/20 cursor-pointer"
                @click="emit('delete-selected')"
              >
                <Trash2 class="size-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left" class="text-xs">
              {{ selectionCount > 1 ? `刪除選取的 ${selectionCount} 個小區 (Delete)` : `刪除選取小區 #${selectedPlotNumber} (Delete)` }}
            </TooltipContent>
          </Tooltip>
        </template>

        <!-- 全部清空按鈕 -->
        <Tooltip v-if="plots.length > 0 && !isDrawing">
          <TooltipTrigger as-child>
            <Button
              size="icon"
              variant="ghost"
              class="size-8 rounded-lg text-zinc-400 hover:text-rose-400 hover:bg-rose-500/20 cursor-pointer"
              @click="emit('clear-all')"
            >
              <Trash2 class="size-3.5 opacity-60 hover:opacity-100" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left" class="text-xs">清空畫布所有小區 (共 {{ plots.length }} 區)</TooltipContent>
        </Tooltip>

        <div class="my-0.5 h-px w-5 bg-white/15" />

        <!-- 儲存小區設定按鈕 -->
        <Tooltip>
          <TooltipTrigger as-child>
            <Button
              size="icon"
              variant="ghost"
              :disabled="isSaving"
              class="relative size-9 rounded-xl transition-all cursor-pointer"
              :class="isDirty ? 'bg-primary text-primary-foreground shadow-md ring-2 ring-primary/50' : 'text-zinc-400 hover:text-white hover:bg-white/10'"
              @click="emit('save')"
            >
              <Spinner v-if="isSaving" class="size-4 animate-spin" />
              <Save v-else class="size-4" />
              <span
                v-if="isDirty"
                class="absolute top-1 right-1 size-2 rounded-full bg-amber-400 animate-pulse ring-2 ring-zinc-950"
              />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left" class="text-xs">
            {{ isSaving ? '儲存中...' : isDirty ? '儲存小區設定 (有未儲存變更*)' : '小區設定已儲存' }}
          </TooltipContent>
        </Tooltip>

        <!-- 小區總數角標 -->
        <span class="mt-1 font-mono text-[10px] text-zinc-400" title="小區總數">
          #{{ plots.length }}
        </span>
      </TooltipProvider>
    </div>

    <!-- 情況 A：自動網格生成屬性面板 (支援自由拖曳與圓形浮動收合) -->
    <template v-if="gridState?.isActive">
      <!-- 最小化狀態：紫色網格浮動圓形按鈕 -->
      <div
        v-if="isMinimized"
        ref="panelRef"
        class="absolute right-full mr-3 top-1/2 -translate-y-1/2 z-30 pointer-events-auto flex items-center justify-center cursor-grab active:cursor-grabbing select-none"
        :style="{ transform: `translate3d(${dragOffset.x}px, ${dragOffset.y}px, 0)` }"
        @pointerdown="startPanelDrag"
      >
        <TooltipProvider :delay-duration="150">
          <Tooltip>
            <TooltipTrigger as-child>
              <button
                type="button"
                class="size-11 rounded-full border border-purple-500/50 bg-zinc-950/90 text-purple-300 shadow-2xl backdrop-blur-md flex items-center justify-center hover:scale-105 hover:bg-purple-900/40 hover:text-white transition-all ring-2 ring-purple-500/30 cursor-pointer"
              >
                <Grid class="size-5" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="left" class="text-xs">
              雙線性網格配置 ({{ gridState.rows }}×{{ gridState.cols }}) - 點擊展開 / 按住拖曳
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      <!-- 展開狀態：完整網格剖分配置面板 -->
      <div
        v-else
        ref="panelRef"
        class="absolute right-full mr-3 top-1/2 -translate-y-1/2 w-80 max-h-[calc(100vh-6rem)] overflow-y-auto rounded-2xl border border-purple-500/40 bg-zinc-950/95 p-4 text-zinc-100 shadow-2xl backdrop-blur-md space-y-3 z-30 pointer-events-auto"
        :style="{ transform: `translate3d(${dragOffset.x}px, ${dragOffset.y}px, 0)` }"
      >
        <div
          class="flex items-center justify-between border-b border-white/10 pb-2 cursor-grab active:cursor-grabbing select-none"
          title="按住拖曳移動面板位置"
          @pointerdown="startPanelDrag"
        >
          <div class="flex items-center gap-1.5 text-xs font-semibold text-purple-300">
            <Grid class="size-4" />
            <span>雙線性網格剖分配置</span>
          </div>
          <div class="flex items-center gap-1">
            <Button
              size="icon"
              variant="ghost"
              class="size-6 rounded-md text-zinc-400 hover:text-white cursor-pointer"
              title="最小化為懸浮按鈕"
              @click.stop="minimizePanel"
            >
              <Minus class="size-3.5" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              class="size-6 rounded-md text-zinc-400 hover:text-white cursor-pointer"
              title="關閉網格配置"
              @click="emit('close-grid')"
            >
              <X class="size-3.5" />
            </Button>
          </div>
        </div>

      <!-- 列數與行數配置 -->
      <div class="grid grid-cols-2 gap-2 text-xs">
        <div class="space-y-1">
          <span class="text-zinc-400 text-[11px]">列數 (Rows):</span>
          <input
            type="number"
            min="1"
            max="50"
            :value="gridState.rows"
            class="w-full h-7 px-2 text-center font-mono font-bold text-xs rounded-lg border border-white/15 bg-white/5 text-white focus:ring-1 focus:ring-purple-400 focus:outline-hidden"
            @input="emit('update:grid-rows', Math.max(1, Math.min(50, Number(($event.target as HTMLInputElement).value) || 1)))"
          />
        </div>

        <div class="space-y-1">
          <span class="text-zinc-400 text-[11px]">行數 (Cols):</span>
          <input
            type="number"
            min="1"
            max="50"
            :value="gridState.cols"
            class="w-full h-7 px-2 text-center font-mono font-bold text-xs rounded-lg border border-white/15 bg-white/5 text-white focus:ring-1 focus:ring-purple-400 focus:outline-hidden"
            @input="emit('update:grid-cols', Math.max(1, Math.min(50, Number(($event.target as HTMLInputElement).value) || 1)))"
          />
        </div>
      </div>

      <!-- 小區尺寸滑桿 (Scale / Margin) -->
      <div class="space-y-1.5 rounded-lg bg-white/5 p-2.5 border border-white/10 text-xs">
        <div class="flex items-center justify-between text-[11px]">
          <span class="text-zinc-300 font-medium">小區尺寸比例:</span>
          <Button
            size="sm"
            variant="ghost"
            class="h-5 px-1.5 text-[10px] text-purple-300 hover:bg-purple-900/40 cursor-pointer"
            :title="isLinked ? '寬高連動中，點擊解除各自獨立調整' : '點擊鎖定等比例寬高連動'"
            @click="isLinked = !isLinked"
          >
            <Link v-if="isLinked" class="size-3 mr-1" />
            <Unlink v-else class="size-3 mr-1 text-amber-400" />
            <span>{{ isLinked ? '等比鎖定' : '獨立調整' }}</span>
          </Button>
        </div>

        <template v-if="isLinked">
          <div class="flex items-center gap-2">
            <input
              type="range"
              min="10"
              max="100"
              step="1"
              :value="currentScaleX"
              class="flex-1 h-1.5 cursor-pointer accent-purple-500 bg-white/20 rounded-lg"
              @input="handleScaleXChange(Number(($event.target as HTMLInputElement).value))"
            />
            <span class="w-8 text-right font-mono text-[11px] font-bold text-purple-300">
              {{ currentScaleX }}%
            </span>
          </div>
        </template>
        <template v-else>
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <span class="text-[10px] text-zinc-400 w-4">寬</span>
              <input
                type="range"
                min="10"
                max="100"
                step="1"
                :value="currentScaleX"
                class="flex-1 h-1.5 cursor-pointer accent-purple-500 bg-white/20 rounded-lg"
                @input="handleScaleXChange(Number(($event.target as HTMLInputElement).value))"
              />
              <span class="w-8 text-right font-mono text-[10px] text-purple-300">{{ currentScaleX }}%</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[10px] text-zinc-400 w-4">高</span>
              <input
                type="range"
                min="10"
                max="100"
                step="1"
                :value="currentScaleY"
                class="flex-1 h-1.5 cursor-pointer accent-purple-500 bg-white/20 rounded-lg"
                @input="handleScaleYChange(Number(($event.target as HTMLInputElement).value))"
              />
              <span class="w-8 text-right font-mono text-[10px] text-purple-300">{{ currentScaleY }}%</span>
            </div>
          </div>
        </template>
      </div>

      <!-- 橡皮擦排除網格單元格 -->
      <div class="flex items-center justify-between gap-2 pt-1 text-xs">
        <Button
          size="sm"
          variant="outline"
          class="h-7 gap-1.5 px-2 text-xs font-medium cursor-pointer transition-all"
          :class="drawTool === 'eraser' ? 'bg-rose-950/80 text-rose-300 border-rose-500 ring-1 ring-rose-400/50' : 'text-zinc-300 border-white/20 hover:bg-white/10'"
          @click="toggleEraserInGrid"
        >
          <Eraser class="size-3.5 text-rose-400" />
          <span>{{ drawTool === 'eraser' ? '點擊消除中' : '消除單元格' }}</span>
          <span
            v-if="gridState.excludedIndices && gridState.excludedIndices.length > 0"
            class="px-1.5 text-[10px] rounded-full bg-rose-600 text-white font-mono"
          >
            -{{ gridState.excludedIndices.length }}
          </span>
        </Button>

        <button
          v-if="gridState.excludedIndices && gridState.excludedIndices.length > 0"
          type="button"
          class="text-[11px] text-zinc-400 hover:text-white cursor-pointer underline"
          @click="emit('clear-excluded-cells')"
        >
          恢復全部
        </button>
      </div>

      <!-- 確認生成按鈕 -->
      <div class="pt-2 border-t border-white/10 flex items-center justify-end gap-2">
        <Button
          size="sm"
          variant="ghost"
          class="h-7 text-xs text-zinc-400 hover:text-white cursor-pointer"
          @click="emit('close-grid')"
        >
          取消
        </Button>
        <Button
          size="sm"
          class="h-7 gap-1.5 px-3 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm cursor-pointer"
          @click="emit('confirm-grid')"
        >
          <Check class="size-3.5" />
          <span>確認生成 ({{ gridState.rows * gridState.cols - (gridState.excludedIndices?.length || 0) }} 區)</span>
        </Button>
      </div>
    </div>
    </template>
  </div>
</template>
