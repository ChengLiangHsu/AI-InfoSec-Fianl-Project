<script setup lang="ts">
import {
  Eye,
  Pencil,
  Square,
  Pentagon,
  Save,
  RotateCcw,
  X,
  Trash2,
  Grid,
  Sparkles,
  Check,
} from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import type { PlotItem, GridGeneratorState } from '@/lib/usePlots'

const props = defineProps<{
  plots: PlotItem[]
  activeMode: 'view' | 'draw'
  drawTool: 'rect' | 'polygon'
  selectedPlotNumber: number | null
  isDirty: boolean
  isSaving: boolean
  isDrawing: boolean
  gridState?: GridGeneratorState
}>()

const emit = defineEmits<{
  (e: 'update:activeMode', mode: 'view' | 'draw'): void
  (e: 'update:drawTool', tool: 'rect' | 'polygon'): void
  (e: 'save'): void
  (e: 'undo-point'): void
  (e: 'cancel-drawing'): void
  (e: 'delete-selected'): void
  (e: 'clear-all'): void
  (e: 'start-grid'): void
  (e: 'close-grid'): void
  (e: 'detect-markers'): void
  (e: 'confirm-grid'): void
  (e: 'update:grid-rows', rows: number): void
  (e: 'update:grid-cols', cols: number): void
  (e: 'update:grid-margin', margin: number): void
}>()

function setMode(mode: 'view' | 'draw') {
  if (props.gridState?.isActive) {
    emit('close-grid')
  }
  emit('update:activeMode', mode)
}

function setDrawTool(tool: 'rect' | 'polygon') {
  emit('update:drawTool', tool)
}

function toggleGridMode() {
  if (props.gridState?.isActive) {
    emit('close-grid')
  } else {
    emit('start-grid')
  }
}
</script>

<template>
  <div class="flex flex-col gap-2.5 border-b bg-background/95 backdrop-blur-xs p-3">
    <!-- 第一列：模式切換、小區工具、自動網格與儲存按鈕 -->
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="flex flex-wrap items-center gap-2">
        <!-- 主模式切換 (檢視 vs 手動繪製 vs 一鍵網格) -->
        <div class="inline-flex rounded-lg border bg-muted/40 p-0.5">
          <Button
            size="sm"
            :variant="activeMode === 'view' && !gridState?.isActive ? 'secondary' : 'ghost'"
            class="h-7 gap-1.5 px-3 text-xs font-medium shadow-none cursor-pointer"
            @click="setMode('view')"
          >
            <Eye class="size-3.5 text-slate-500" />
            <span>檢視</span>
          </Button>

          <Button
            size="sm"
            :variant="activeMode === 'draw' && !gridState?.isActive ? 'secondary' : 'ghost'"
            class="h-7 gap-1.5 px-3 text-xs font-medium shadow-none cursor-pointer"
            @click="setMode('draw')"
          >
            <Pencil class="size-3.5 text-blue-500" />
            <span>手動繪製</span>
          </Button>

          <Button
            size="sm"
            :variant="gridState?.isActive ? 'secondary' : 'ghost'"
            class="h-7 gap-1.5 px-3 text-xs font-medium shadow-none cursor-pointer"
            :class="{
              'bg-purple-100 text-purple-700 dark:bg-purple-950/80 dark:text-purple-300 ring-1 ring-purple-400/50': gridState?.isActive,
            }"
            title="一鍵辨識農田白色定位牌並剖分小區"
            @click="toggleGridMode"
          >
            <Grid class="size-3.5 text-purple-600 dark:text-purple-400" />
            <span>⚡ 自動網格生成</span>
          </Button>
        </div>

        <!-- 手動繪製模式下的幾何工具切換 (矩形 vs 多邊形) -->
        <div
          v-if="activeMode === 'draw' && !gridState?.isActive"
          class="inline-flex rounded-lg border bg-muted/40 p-0.5"
        >
          <Button
            size="sm"
            :variant="drawTool === 'rect' ? 'secondary' : 'ghost'"
            class="h-7 gap-1.5 px-2.5 text-xs font-medium shadow-none cursor-pointer"
            title="按住滑鼠左鍵拖曳秒畫矩形小區"
            @click="setDrawTool('rect')"
          >
            <Square class="size-3.5 text-primary" />
            <span>矩形拉框</span>
          </Button>
          <Button
            size="sm"
            :variant="drawTool === 'polygon' ? 'secondary' : 'ghost'"
            class="h-7 gap-1.5 px-2.5 text-xs font-medium shadow-none cursor-pointer"
            title="逐點點選多邊形頂點，適用特殊地形"
            @click="setDrawTool('polygon')"
          >
            <Pentagon class="size-3.5 text-amber-500" />
            <span>多邊形</span>
          </Button>
        </div>
      </div>

      <!-- 右側：統計資訊與儲存按鈕 -->
      <div class="flex items-center gap-2">
        <Badge variant="outline" class="font-normal text-xs text-muted-foreground">
          小區總數: <strong class="ml-1 text-foreground font-semibold">{{ plots.length }}</strong>
        </Badge>

        <Button
          size="sm"
          :variant="isDirty ? 'default' : 'outline'"
          :disabled="isSaving"
          class="h-7 gap-1.5 px-3 text-xs font-medium cursor-pointer transition-all"
          :class="{ 'ring-2 ring-primary/40': isDirty }"
          @click="emit('save')"
        >
          <Spinner v-if="isSaving" class="size-3.5 animate-spin" />
          <Save v-else class="size-3.5" />
          <span>{{ isSaving ? '儲存中...' : isDirty ? '儲存小區設定*' : '已儲存' }}</span>
          <span
            v-if="isDirty"
            class="size-1.5 rounded-full bg-amber-400 animate-pulse ml-0.5"
            title="有未儲存的變更"
          />
        </Button>
      </div>
    </div>

    <!-- 情況 A：自動網格生成控制列 -->
    <div
      v-if="gridState?.isActive"
      class="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-purple-50/80 dark:bg-purple-950/30 p-2.5 border border-purple-200/80 dark:border-purple-900/60 text-xs shadow-xs"
    >
      <div class="flex flex-wrap items-center gap-3">
        <!-- 一鍵自動偵測定位牌按鈕 -->
        <Button
          size="sm"
          variant="outline"
          :disabled="gridState.isDetecting"
          class="h-7 gap-1.5 px-3 text-xs font-medium bg-background border-purple-300 text-purple-700 hover:bg-purple-100 dark:border-purple-700 dark:text-purple-300 dark:hover:bg-purple-900/50 cursor-pointer shadow-xs"
          @click="emit('detect-markers')"
        >
          <Spinner v-if="gridState.isDetecting" class="size-3.5 animate-spin text-purple-600" />
          <Sparkles v-else class="size-3.5 text-purple-600" />
          <span>{{ gridState.isDetecting ? '辨識中...' : '自動辨識四角定位牌' }}</span>
        </Button>

        <div class="h-4 w-px bg-purple-200 dark:bg-purple-800" />

        <!-- 列數輸入 (Rows) -->
        <div class="flex items-center gap-1.5">
          <span class="text-muted-foreground font-medium">列數 (Rows):</span>
          <input
            type="number"
            min="1"
            max="20"
            :value="gridState.rows"
            class="w-12 h-6 px-1 text-center font-bold text-xs rounded border border-input bg-background shadow-2xs focus:ring-1 focus:ring-purple-500 focus:outline-hidden"
            @input="emit('update:grid-rows', Math.max(1, Math.min(20, Number(($event.target as HTMLInputElement).value) || 1)))"
          />
        </div>

        <!-- 行數輸入 (Cols) -->
        <div class="flex items-center gap-1.5">
          <span class="text-muted-foreground font-medium">行數 (Cols):</span>
          <input
            type="number"
            min="1"
            max="20"
            :value="gridState.cols"
            class="w-12 h-6 px-1 text-center font-bold text-xs rounded border border-input bg-background shadow-2xs focus:ring-1 focus:ring-purple-500 focus:outline-hidden"
            @input="emit('update:grid-cols', Math.max(1, Math.min(20, Number(($event.target as HTMLInputElement).value) || 1)))"
          />
        </div>

        <div class="h-4 w-px bg-purple-200 dark:bg-purple-800" />

        <!-- 走道間距滑桿 (Margin Gap) -->
        <div class="flex items-center gap-2">
          <span class="text-muted-foreground font-medium">走道間隔:</span>
          <input
            type="range"
            min="0"
            max="20"
            step="1"
            :value="Math.round(gridState.marginRatio * 100)"
            class="w-20 h-1.5 cursor-pointer accent-purple-600"
            @input="emit('update:grid-margin', (Number(($event.target as HTMLInputElement).value) || 0) / 100)"
          />
          <span class="w-7 text-[11px] font-mono text-purple-700 dark:text-purple-300">
            {{ Math.round(gridState.marginRatio * 100) }}%
          </span>
        </div>
      </div>

      <!-- 右側：確認生成與離開 -->
      <div class="flex items-center gap-2">
        <Button
          size="sm"
          class="h-7 gap-1.5 px-3 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs cursor-pointer"
          title="將目前預覽網格轉化為正式試驗小區"
          @click="emit('confirm-grid')"
        >
          <Check class="size-3.5" />
          <span>確認生成 ({{ gridState.rows * gridState.cols }} 區)</span>
        </Button>

        <Button
          size="sm"
          variant="ghost"
          class="h-7 px-2 text-xs text-muted-foreground hover:text-foreground cursor-pointer"
          @click="emit('close-grid')"
        >
          <X class="size-3.5 mr-1" />
          <span>關閉</span>
        </Button>
      </div>
    </div>

    <!-- 情況 B：手動繪製模式下的操作指引與快捷按鈕 -->
    <div
      v-else-if="activeMode === 'draw'"
      class="flex flex-wrap items-center justify-between gap-2 rounded-md bg-blue-50/60 dark:bg-blue-950/20 px-3 py-1.5 border border-blue-200/50 dark:border-blue-900/50 text-xs"
    >
      <div class="flex items-center gap-2 text-muted-foreground">
        <template v-if="drawTool === 'rect'">
          <span class="text-blue-700 dark:text-blue-300 font-medium">
            📐 拖曳拉框：在影像上按住滑鼠左鍵並拖曳即可秒速框出小區；放開後立即彈窗選擇農藥。
          </span>
        </template>
        <template v-else>
          <span v-if="isDrawing" class="font-medium text-blue-600 dark:text-blue-400 flex items-center gap-1.5">
            <span class="size-2 rounded-full bg-blue-500 animate-ping" />
            繪製中：點擊起點吸附或雙擊閉合小區；閉合後立即彈窗選擇農藥
          </span>
          <span v-else class="text-muted-foreground">
            點擊影像空白處開始繪製多邊形頂點；點擊既有小區可隨時修改農藥設定
          </span>
        </template>
      </div>

      <div class="flex items-center gap-1.5">
        <Button
          v-if="isDrawing && drawTool === 'polygon'"
          size="sm"
          variant="ghost"
          class="h-6 px-2 text-[11px] cursor-pointer"
          @click="emit('undo-point')"
        >
          <RotateCcw class="size-3 mr-1" />
          復原點
        </Button>
        <Button
          v-if="isDrawing && drawTool === 'polygon'"
          size="sm"
          variant="ghost"
          class="h-6 px-2 text-[11px] text-destructive cursor-pointer"
          @click="emit('cancel-drawing')"
        >
          <X class="size-3 mr-1" />
          放棄繪製
        </Button>
        <Button
          v-if="selectedPlotNumber !== null && !isDrawing"
          size="sm"
          variant="ghost"
          class="h-6 px-2 text-[11px] text-destructive hover:bg-destructive/10 cursor-pointer"
          @click="emit('delete-selected')"
        >
          <Trash2 class="size-3 mr-1" />
          刪除小區 #{{ selectedPlotNumber }}
        </Button>
      </div>
    </div>
  </div>
</template>
