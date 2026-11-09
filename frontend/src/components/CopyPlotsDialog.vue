<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Copy, FolderArchive, ArrowRight, Check } from '@lucide/vue'

export interface ProjectOption {
  id: string
  name: string
  progress?: number
}

const props = defineProps<{
  open: boolean
  projects: ProjectOption[]
  currentProjectId?: string
}>()

const emit = defineEmits<{
  (e: 'update:open', val: boolean): void
  (e: 'confirm', payload: { sourceProjectId: string; mode: 'replace' | 'append' }): void
}>()

const selectedSourceId = ref<string>('')
const importMode = ref<'replace' | 'append'>('replace')
const sourcePlotCount = ref<number | null>(null)
const isLoadingCount = ref(false)

const availableProjects = computed(() => {
  return props.projects.filter((p) => p.id !== props.currentProjectId)
})

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      if (availableProjects.value.length > 0) {
        selectedSourceId.value = availableProjects.value[0].id
        fetchSourcePlotCount(selectedSourceId.value)
      } else {
        selectedSourceId.value = ''
        sourcePlotCount.value = null
      }
    }
  }
)

watch(selectedSourceId, (newId) => {
  if (newId) {
    fetchSourcePlotCount(newId)
  } else {
    sourcePlotCount.value = null
  }
})

async function fetchSourcePlotCount(taskId: string) {
  if (!taskId) return
  isLoadingCount.value = true
  sourcePlotCount.value = null
  try {
    const res = await fetch(`/api/task/plots/${taskId}`)
    const json = await res.json()
    if (res.ok && json.result && Array.isArray(json.data)) {
      sourcePlotCount.value = json.data.length
    }
  } catch {
    sourcePlotCount.value = 0
  } finally {
    isLoadingCount.value = false
  }
}

function handleConfirm() {
  if (!selectedSourceId.value) return
  emit('confirm', {
    sourceProjectId: selectedSourceId.value,
    mode: importMode.value,
  })
}
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2 text-base">
          <Copy class="size-4 text-primary" />
          <span>從歷史專案複製小區網格</span>
        </DialogTitle>
        <DialogDescription class="text-xs">
          選取同田區之其他空拍專案，即可一鍵將已完成標註與分區的小區網格重複套用至目前專案。
        </DialogDescription>
      </DialogHeader>

      <div class="space-y-4 py-2 text-xs">
        <!-- 來源專案選取 -->
        <div class="space-y-1.5">
          <label class="font-medium text-foreground">來源專案</label>
          <div v-if="availableProjects.length === 0" class="text-muted-foreground italic p-2 border rounded-md">
            暫無其他歷史專案可供複製。
          </div>
          <select
            v-else
            v-model="selectedSourceId"
            class="w-full h-8 px-2 text-xs rounded-md border border-input bg-background shadow-xs focus:ring-1 focus:ring-primary focus:outline-hidden"
          >
            <option v-for="p in availableProjects" :key="p.id" :value="p.id">
              {{ p.name }} (ID: {{ p.id.slice(0, 8) }}...)
            </option>
          </select>

          <div v-if="selectedSourceId" class="flex items-center gap-2 pt-1 text-[11px] text-muted-foreground">
            <span>該專案小區數:</span>
            <Badge variant="outline" class="h-4 font-mono">
              {{ isLoadingCount ? '查詢中...' : (sourcePlotCount !== null ? `${sourcePlotCount} 區` : '無小區') }}
            </Badge>
          </div>
        </div>

        <!-- 匯入模式切換 -->
        <div class="space-y-1.5">
          <label class="font-medium text-foreground">複製套用模式</label>
          <div class="grid grid-cols-2 gap-2">
            <button
              type="button"
              class="flex flex-col items-start gap-1 p-2 rounded-lg border text-left cursor-pointer transition-all"
              :class="importMode === 'replace' ? 'border-primary bg-primary/5 text-foreground ring-1 ring-primary' : 'border-border text-muted-foreground hover:bg-muted/50'"
              @click="importMode = 'replace'"
            >
              <span class="font-semibold text-xs flex items-center gap-1">
                <Check v-if="importMode === 'replace'" class="size-3 text-primary" />
                替換現有小區
              </span>
              <span class="text-[10px] text-muted-foreground">清空當前專案既有小區並套用新網格</span>
            </button>

            <button
              type="button"
              class="flex flex-col items-start gap-1 p-2 rounded-lg border text-left cursor-pointer transition-all"
              :class="importMode === 'append' ? 'border-primary bg-primary/5 text-foreground ring-1 ring-primary' : 'border-border text-muted-foreground hover:bg-muted/50'"
              @click="importMode = 'append'"
            >
              <span class="font-semibold text-xs flex items-center gap-1">
                <Check v-if="importMode === 'append'" class="size-3 text-primary" />
                追加在後方
              </span>
              <span class="text-[10px] text-muted-foreground">保留現有小區，將新小區接續在編號後方</span>
            </button>
          </div>
        </div>
      </div>

      <DialogFooter class="flex gap-2">
        <Button variant="outline" size="sm" class="cursor-pointer" @click="emit('update:open', false)">
          取消
        </Button>
        <Button
          size="sm"
          class="gap-1.5 cursor-pointer bg-primary text-primary-foreground"
          :disabled="!selectedSourceId || sourcePlotCount === 0 || isLoadingCount"
          @click="handleConfirm"
        >
          <Copy class="size-3.5" />
          <span>確認複製</span>
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
