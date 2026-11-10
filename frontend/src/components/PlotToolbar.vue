<script setup lang="ts">
import { ref, computed } from 'vue'
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
  Check,
  Link,
  Unlink,
  Eraser,
  Copy,
  ClipboardCopy,
  ChevronDown,
} from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
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
  isDirty: boolean
  isSaving: boolean
  isDrawing: boolean
  gridState?: GridGeneratorState
}>()

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
            data-tour="grid-mode"
            size="sm"
            :variant="gridState?.isActive ? 'secondary' : 'ghost'"
            class="h-7 gap-1.5 px-3 text-xs font-medium shadow-none cursor-pointer"
            :class="{
              'bg-purple-100 text-purple-700 dark:bg-purple-950/80 dark:text-purple-300 ring-1 ring-purple-400/50': gridState?.isActive,
            }"
            title="辨識農田四角定位牌並剖分小區網格"
            @click="toggleGridMode"
          >
            <Grid class="size-3.5 text-purple-600 dark:text-purple-400" />
            <span>網格生成</span>
          </Button>
        </div>

        <!-- 手動繪製模式下的幾何工具切換 (矩形 vs 多邊形 vs 橡皮擦) -->
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
          <Button
            size="sm"
            :variant="drawTool === 'eraser' ? 'secondary' : 'ghost'"
            class="h-7 gap-1.5 px-2.5 text-xs font-medium shadow-none cursor-pointer"
            :class="{
              'bg-rose-100 text-rose-700 dark:bg-rose-950/80 dark:text-rose-300 ring-1 ring-rose-400/50': drawTool === 'eraser',
            }"
            title="橡皮擦工具：點擊任意小區即可快速消除"
            @click="setDrawTool('eraser')"
          >
            <Eraser class="size-3.5 text-rose-500" />
            <span>橡皮擦</span>
          </Button>
        </div>
      </div>

      <!-- 右側：複製網格選單、統計資訊與儲存按鈕 -->
      <div class="flex items-center gap-2">
        <!-- 複製功能選單 (重複利用小區網格) -->
        <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button
              size="sm"
              variant="outline"
              class="h-7 gap-1.5 px-2.5 text-xs font-medium cursor-pointer"
              title="複製與重複利用繪製好的小區網格"
            >
              <Copy class="size-3.5 text-blue-600 dark:text-blue-400" />
              <span>複製網格</span>
              <ChevronDown class="size-3 text-muted-foreground" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" class="w-56 text-xs bg-background">
            <DropdownMenuItem
              :disabled="plots.length === 0"
              class="cursor-pointer gap-2 py-1.5"
              title="將當前所有小區複製一份並輕微平移，方便標註相鄰田區"
              @click="emit('duplicate-all')"
            >
              <Copy class="size-3.5 text-blue-500" />
              <span>複製全部小區 (位移副本)</span>
            </DropdownMenuItem>

            <DropdownMenuItem
              :disabled="plots.length === 0"
              class="cursor-pointer gap-2 py-1.5"
              title="將當前所有小區座標以 JSON 複製到剪貼簿"
              @click="emit('copy-to-clipboard')"
            >
              <ClipboardCopy class="size-3.5 text-emerald-500" />
              <span>複製小區到剪貼簿</span>
            </DropdownMenuItem>

            <DropdownMenuItem
              class="cursor-pointer gap-2 py-1.5"
              title="貼上剪貼簿中的小區網格"
              @click="emit('paste-from-clipboard')"
            >
              <Copy class="size-3.5 text-purple-500" />
              <span>貼上剪貼簿網格</span>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <DropdownMenuItem
              class="cursor-pointer gap-2 py-1.5"
              title="從同田區或歷史航拍專案直接匯入小區網格"
              @click="emit('open-copy-from-project')"
            >
              <Grid class="size-3.5 text-amber-500" />
              <span>從歷史專案複製網格...</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

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

        <!-- 小區尺寸滑桿 (Plot Size / Scale) -->
        <div class="flex items-center gap-1.5" title="小區面積佔單元格之百分比，可縮小以緊密貼合作物植株">
          <span class="text-muted-foreground font-medium">小區尺寸:</span>
          <template v-if="isLinked">
            <input
              type="range"
              min="10"
              max="100"
              step="1"
              :value="currentScaleX"
              class="w-20 h-1.5 cursor-pointer accent-purple-600"
              @input="handleScaleXChange(Number(($event.target as HTMLInputElement).value))"
            />
            <span class="w-8 text-[11px] font-mono font-bold text-purple-700 dark:text-purple-300">
              {{ currentScaleX }}%
            </span>
          </template>
          <template v-else>
            <span class="text-[10px] text-muted-foreground">寬</span>
            <input
              type="range"
              min="10"
              max="100"
              step="1"
              :value="currentScaleX"
              class="w-14 h-1.5 cursor-pointer accent-purple-600"
              title="小區寬度"
              @input="handleScaleXChange(Number(($event.target as HTMLInputElement).value))"
            />
            <span class="w-6 text-[10px] font-mono font-bold text-purple-700 dark:text-purple-300">
              {{ currentScaleX }}%
            </span>
            <span class="text-[10px] text-muted-foreground ml-1">高</span>
            <input
              type="range"
              min="10"
              max="100"
              step="1"
              :value="currentScaleY"
              class="w-14 h-1.5 cursor-pointer accent-purple-600"
              title="小區高度"
              @input="handleScaleYChange(Number(($event.target as HTMLInputElement).value))"
            />
            <span class="w-6 text-[10px] font-mono font-bold text-purple-700 dark:text-purple-300">
              {{ currentScaleY }}%
            </span>
          </template>

          <!-- 寬高連動鎖定切換 -->
          <Button
            size="sm"
            variant="ghost"
            class="h-6 w-6 p-0 text-purple-600 hover:bg-purple-100 dark:text-purple-300 dark:hover:bg-purple-900/50 cursor-pointer"
            :title="isLinked ? '目前寬高連動，點擊解除各自獨立調整' : '點擊鎖定等比例寬高連動'"
            @click="isLinked = !isLinked"
          >
            <Link v-if="isLinked" class="size-3.5" />
            <Unlink v-else class="size-3.5 text-amber-600" />
          </Button>
        </div>

        <div class="h-4 w-px bg-purple-200 dark:bg-purple-800" />

        <!-- 橡皮擦排除誤繪小區 -->
        <Button
          size="sm"
          variant="outline"
          class="h-7 gap-1.5 px-2.5 text-xs font-medium cursor-pointer"
          :class="drawTool === 'eraser' ? 'bg-rose-100 text-rose-700 border-rose-300 dark:bg-rose-950/80 dark:text-rose-300 ring-1 ring-rose-400/50' : 'text-rose-600 border-rose-200 hover:bg-rose-50 dark:border-rose-900 dark:hover:bg-rose-950/30'"
          :title="drawTool === 'eraser' ? '橡皮擦啟用中：點擊網格小區即可排除消除' : '切換橡皮擦：點擊網格小區可排除消除（如落於道路、田埂之小區）'"
          @click="toggleEraserInGrid"
        >
          <Eraser class="size-3.5 text-rose-500" />
          <span>{{ drawTool === 'eraser' ? '橡皮擦 (點擊排除)' : '橡皮擦排除' }}</span>
          <span
            v-if="gridState.excludedIndices && gridState.excludedIndices.length > 0"
            class="px-1.5 text-[10px] rounded-full bg-rose-500 text-white font-mono"
            title="已排除小區數量"
          >
            -{{ gridState.excludedIndices.length }}
          </span>
        </Button>
        <button
          v-if="gridState.excludedIndices && gridState.excludedIndices.length > 0"
          type="button"
          class="text-[11px] text-muted-foreground hover:text-foreground cursor-pointer underline"
          @click="emit('clear-excluded-cells')"
        >
          恢復全部
        </button>
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
          <span>確認生成 ({{ gridState.rows * gridState.cols - (gridState.excludedIndices?.length || 0) }} 區)</span>
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
        <template v-else-if="drawTool === 'eraser'">
          <span class="text-rose-600 dark:text-rose-400 font-medium flex items-center gap-1.5">
            <Eraser class="size-3.5" />
            🧹 橡皮擦模式：點擊任意小區即可快速消除；按住滑鼠拖曳可滑動批量擦除。
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
          variant="outline"
          class="h-6 px-2 text-[11px] text-blue-600 border-blue-200 hover:bg-blue-50 dark:text-blue-400 dark:border-blue-900 dark:hover:bg-blue-950/50 cursor-pointer"
          title="複製目前選取的小區 (快速鍵 Ctrl+D)"
          @click="emit('duplicate-selected')"
        >
          <Copy class="size-3 mr-1 text-blue-500" />
          複製小區 #{{ selectedPlotNumber }}
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
