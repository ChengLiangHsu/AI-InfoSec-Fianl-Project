<script setup lang="ts">
import { computed } from 'vue'
import {
  Pencil,
  Tag,
  Eye,
  Save,
  RotateCcw,
  X,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Maximize,
  Minimize,
} from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { PlotItem, ActiveBrush } from '@/lib/usePlots'

const props = defineProps<{
  plots: PlotItem[]
  activeMode: 'view' | 'draw' | 'assign'
  selectedPlotNumber: number | null
  activeBrush: ActiveBrush
  isDirty: boolean
  isSaving: boolean
  isDrawing: boolean
  isFullscreen?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:activeMode', mode: 'view' | 'draw' | 'assign'): void
  (e: 'update:activeBrush', brush: ActiveBrush): void
  (e: 'save'): void
  (e: 'undo-point'): void
  (e: 'cancel-drawing'): void
  (e: 'delete-selected'): void
  (e: 'clear-all'): void
  (e: 'toggle-fullscreen'): void
}>()

// 取得既有專案中出現過的獨立處理組清單，作為快捷選取按鈕
const existingTreatments = computed(() => {
  const set = new Set<string>()
  for (const p of props.plots) {
    if (p.is_control) {
      set.add('CK')
    } else if (p.treatment) {
      set.add(`${p.treatment}::${p.dose}`)
    }
  }
  return Array.from(set).map((item) => {
    if (item === 'CK') {
      return { isControl: true, treatment: '', dose: '', label: '未施藥對照 (CK)' }
    }
    const [treatment, dose] = item.split('::')
    return {
      isControl: false,
      treatment,
      dose,
      label: `${treatment}${dose ? ' (' + dose + ')' : ''}`,
    }
  })
})

function setMode(mode: 'view' | 'draw' | 'assign') {
  emit('update:activeMode', mode)
}

function updateBrush(partial: Partial<ActiveBrush>) {
  emit('update:activeBrush', { ...props.activeBrush, ...partial })
}

function onTreatmentTypeChange(val: string) {
  if (val === 'ck') {
    updateBrush({ isControl: true, treatment: '', dose: '' })
  } else {
    updateBrush({ isControl: false })
  }
}

function selectPreset(preset: { isControl: boolean; treatment: string; dose: string }) {
  emit('update:activeBrush', {
    isControl: preset.isControl,
    treatment: preset.treatment,
    dose: preset.dose,
  })
}
</script>

<template>
  <div class="flex flex-col gap-2.5 border-b bg-background/95 backdrop-blur-xs p-3">
    <!-- 第一列：模式切換、統計資訊與儲存按鈕 -->
    <div class="flex flex-wrap items-center justify-between gap-2">
      <!-- 模式切換按鈕群 -->
      <div class="inline-flex rounded-lg border bg-muted/40 p-0.5">
        <Button
          size="sm"
          :variant="activeMode === 'view' ? 'secondary' : 'ghost'"
          class="h-7 gap-1.5 px-3 text-xs font-medium shadow-none cursor-pointer"
          @click="setMode('view')"
        >
          <Eye class="size-3.5" />
          <span>檢視</span>
        </Button>
        <Button
          size="sm"
          :variant="activeMode === 'draw' ? 'secondary' : 'ghost'"
          class="h-7 gap-1.5 px-3 text-xs font-medium shadow-none cursor-pointer"
          @click="setMode('draw')"
        >
          <Pencil class="size-3.5 text-blue-500" />
          <span>繪製小區</span>
        </Button>
        <Button
          size="sm"
          :variant="activeMode === 'assign' ? 'secondary' : 'ghost'"
          class="h-7 gap-1.5 px-3 text-xs font-medium shadow-none cursor-pointer"
          @click="setMode('assign')"
        >
          <Tag class="size-3.5 text-emerald-500" />
          <span>套用處理</span>
        </Button>
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

        <Button
          size="sm"
          variant="outline"
          class="h-7 gap-1.5 px-2.5 text-xs font-medium cursor-pointer"
          :title="isFullscreen ? '結束全螢幕 (Esc)' : '進入全螢幕畫布'"
          @click="emit('toggle-fullscreen')"
        >
          <Minimize v-if="isFullscreen" class="size-3.5 text-primary" />
          <Maximize v-else class="size-3.5" />
          <span class="hidden sm:inline">{{ isFullscreen ? '結束全螢幕' : '全螢幕' }}</span>
        </Button>
      </div>
    </div>

    <!-- 第二列：繪製模式下的操作工具列 -->
    <div
      v-if="activeMode === 'draw'"
      class="flex flex-wrap items-center justify-between gap-2 rounded-md bg-blue-50/60 dark:bg-blue-950/20 px-3 py-1.5 border border-blue-200/50 dark:border-blue-900/50 text-xs"
    >
      <div class="flex items-center gap-2 text-muted-foreground">
        <span v-if="isDrawing" class="font-medium text-blue-600 dark:text-blue-400 flex items-center gap-1.5">
          <span class="size-2 rounded-full bg-blue-500 animate-ping" />
          繪製中：點擊起點吸附或雙擊閉合小區
        </span>
        <span v-else class="text-muted-foreground">
          點擊影像空白處開始繪製多邊形；或點擊既有小區以拖曳頂點微調
        </span>
      </div>

      <div class="flex items-center gap-1.5">
        <Button
          v-if="isDrawing"
          size="sm"
          variant="ghost"
          class="h-6 px-2 text-[11px] cursor-pointer"
          @click="emit('undo-point')"
        >
          <RotateCcw class="size-3 mr-1" />
          復原點
        </Button>
        <Button
          v-if="isDrawing"
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

    <!-- 第二列：套用處理模式下的筆刷與快選設定 -->
    <div
      v-if="activeMode === 'assign'"
      class="flex flex-col gap-2 rounded-md bg-emerald-50/60 dark:bg-emerald-950/20 p-2.5 border border-emerald-200/50 dark:border-emerald-900/50 text-xs"
    >
      <div class="flex flex-wrap items-center gap-2">
        <span class="font-semibold text-emerald-800 dark:text-emerald-300 shrink-0">
          作用中筆刷：
        </span>

        <!-- 類別下拉選單 (未施藥對照 CK vs 農藥處理) -->
        <Select
          :model-value="activeBrush.isControl ? 'ck' : 'pesticide'"
          @update:model-value="(val) => onTreatmentTypeChange(String(val))"
        >
          <SelectTrigger class="h-7 w-36 text-xs bg-background">
            <SelectValue placeholder="選擇處理類型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="pesticide" class="text-xs cursor-pointer">
              農藥處理
            </SelectItem>
            <SelectItem value="ck" class="text-xs cursor-pointer">
              未施藥對照 (CK)
            </SelectItem>
          </SelectContent>
        </Select>

        <!-- 農藥名稱與施用劑量輸入框（僅在選擇「農藥處理」時顯示） -->
        <template v-if="!activeBrush.isControl">
          <Input
            :model-value="activeBrush.treatment"
            placeholder="農藥名稱 (例: 益達胺)"
            class="h-7 w-36 text-xs bg-background"
            @update:model-value="(val) => updateBrush({ treatment: String(val) })"
          />
          <Input
            :model-value="activeBrush.dose"
            placeholder="施用劑量 (例: 1000倍)"
            class="h-7 w-32 text-xs bg-background"
            @update:model-value="(val) => updateBrush({ dose: String(val) })"
          />
        </template>

        <span class="text-muted-foreground text-[11px] ml-auto shrink-0">
          👉 點擊畫布上的小區即可直接套用
        </span>
      </div>

      <!-- 快捷標籤清單 -->
      <div v-if="existingTreatments.length > 0" class="flex flex-wrap items-center gap-1.5 pt-1 border-t border-emerald-200/40 dark:border-emerald-900/40">
        <span class="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">快速套用既有組別:</span>
        <Badge
          v-for="(preset, idx) in existingTreatments"
          :key="idx"
          variant="secondary"
          class="cursor-pointer hover:bg-emerald-100 dark:hover:bg-emerald-900/40 text-[11px] font-normal transition-colors"
          @click="selectPreset(preset)"
        >
          {{ preset.label }}
        </Badge>
      </div>
    </div>
  </div>
</template>
