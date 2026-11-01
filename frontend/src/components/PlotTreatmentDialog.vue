<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Trash2, Check, X, ShieldAlert, Sparkles } from '@lucide/vue'

export interface TreatmentData {
  isControl: boolean
  treatment: string
  dose: string
}

export interface ExistingTreatment {
  isControl: boolean
  treatment: string
  dose: string
  label: string
}

const props = defineProps<{
  open: boolean
  plotNumber: number | null
  isNewPlot: boolean
  initialTreatment?: string
  initialDose?: string
  initialIsControl?: boolean
  existingTreatments: ExistingTreatment[]
}>()

const emit = defineEmits<{
  (e: 'update:open', val: boolean): void
  (e: 'confirm', data: TreatmentData): void
  (e: 'cancel'): void
  (e: 'delete', plotNumber: number): void
}>()

const isControl = ref(false)
const treatment = ref('')
const dose = ref('')
const treatmentInputRef = ref<HTMLInputElement | null>(null)

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      isControl.value = props.initialIsControl ?? false
      treatment.value = props.initialTreatment ?? ''
      dose.value = props.initialDose ?? ''

      nextTick(() => {
        if (!isControl.value && treatmentInputRef.value) {
          treatmentInputRef.value.focus()
          treatmentInputRef.value.select()
        }
      })
    }
  },
  { immediate: true }
)

function setTreatmentType(control: boolean) {
  isControl.value = control
  if (control) {
    treatment.value = ''
    dose.value = ''
  } else {
    nextTick(() => {
      treatmentInputRef.value?.focus()
    })
  }
}

function selectPreset(preset: ExistingTreatment) {
  isControl.value = preset.isControl
  treatment.value = preset.treatment
  dose.value = preset.dose
}

function handleConfirm() {
  emit('confirm', {
    isControl: isControl.value,
    treatment: isControl.value ? '' : treatment.value.trim(),
    dose: isControl.value ? '' : dose.value.trim(),
  })
  emit('update:open', false)
}

function handleCancel() {
  emit('cancel')
  emit('update:open', false)
}

function handleDelete() {
  if (props.plotNumber !== null) {
    emit('delete', props.plotNumber)
    emit('update:open', false)
  }
}

function onOpenChange(val: boolean) {
  if (!val) {
    handleCancel()
  } else {
    emit('update:open', true)
  }
}
</script>

<template>
  <Dialog :open="open" @update:open="onOpenChange">
    <DialogContent class="sm:max-w-[440px] select-none">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2 text-base">
          <span
            class="flex size-6 items-center justify-center rounded-md bg-primary/10 text-xs font-bold text-primary font-mono"
          >
            #{{ plotNumber ?? '?' }}
          </span>
          <span>{{ isNewPlot ? '新繪小區處理設定' : '編輯小區處理設定' }}</span>
        </DialogTitle>
        <DialogDescription class="text-xs text-muted-foreground">
          {{ isNewPlot ? '請為剛剛劃定的小區指派試驗農藥與劑量，或設定為對照組。' : '修改或刪除此小區之農藥處理資訊。' }}
        </DialogDescription>
      </DialogHeader>

      <div class="flex flex-col gap-4 py-2">
        <!-- 處理組類型選擇切換器 -->
        <div class="grid grid-cols-2 gap-2 p-1 bg-muted/50 rounded-lg border">
          <Button
            type="button"
            size="sm"
            :variant="!isControl ? 'default' : 'ghost'"
            class="h-8 text-xs font-medium cursor-pointer shadow-none transition-all"
            @click="setTreatmentType(false)"
          >
            <Sparkles class="size-3.5 mr-1.5" />
            農藥處理組
          </Button>
          <Button
            type="button"
            size="sm"
            :variant="isControl ? 'default' : 'ghost'"
            class="h-8 text-xs font-medium cursor-pointer shadow-none transition-all"
            @click="setTreatmentType(true)"
          >
            <ShieldAlert class="size-3.5 mr-1.5" />
            未施藥對照 (CK)
          </Button>
        </div>

        <!-- 農藥名稱與劑量輸入欄位（非對照組時顯示） -->
        <div v-if="!isControl" class="flex flex-col gap-3">
          <div class="flex flex-col gap-1.5">
            <Label for="treatment-name" class="text-xs font-medium">農藥名稱 / 處理組</Label>
            <input
              id="treatment-name"
              ref="treatmentInputRef"
              v-model="treatment"
              type="text"
              placeholder="例如: 益達胺、拜芬第、除草劑 A"
              class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-xs shadow-xs transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              @keydown.enter.prevent="handleConfirm"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <Label for="treatment-dose" class="text-xs font-medium">施用劑量 / 稀釋倍數</Label>
            <input
              id="treatment-dose"
              v-model="dose"
              type="text"
              placeholder="例如: 1000倍、500 ppm、2 L/ha"
              class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-xs shadow-xs transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              @keydown.enter.prevent="handleConfirm"
            />
          </div>
        </div>

        <div
          v-else
          class="flex items-center gap-2 rounded-md bg-slate-100 dark:bg-slate-900/60 p-3 text-xs text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800"
        >
          <ShieldAlert class="size-4 shrink-0 text-slate-500" />
          <span>此小區設定為未施藥空白對照組 (CK / Untreated Control)，將呈現對照專屬灰色標記。</span>
        </div>

        <!-- 既有處理組快速套用按鈕 -->
        <div v-if="existingTreatments.length > 0" class="flex flex-col gap-1.5 pt-1 border-t">
          <span class="text-[11px] font-medium text-muted-foreground">快速帶入專案既有組別:</span>
          <div class="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
            <Badge
              v-for="(preset, idx) in existingTreatments"
              :key="idx"
              variant="secondary"
              class="cursor-pointer hover:bg-primary/15 text-[11px] font-normal transition-colors py-0.5 px-2"
              @click="selectPreset(preset)"
            >
              {{ preset.label }}
            </Badge>
          </div>
        </div>
      </div>

      <DialogFooter class="flex sm:justify-between items-center gap-2 pt-2">
        <div>
          <Button
            v-if="!isNewPlot"
            type="button"
            size="sm"
            variant="ghost"
            class="h-8 text-xs text-destructive hover:bg-destructive/10 cursor-pointer"
            @click="handleDelete"
          >
            <Trash2 class="size-3.5 mr-1" />
            刪除此小區
          </Button>
        </div>

        <div class="flex items-center gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            class="h-8 text-xs cursor-pointer"
            @click="handleCancel"
          >
            <X class="size-3.5 mr-1" />
            {{ isNewPlot ? '放棄繪製' : '取消' }}
          </Button>
          <Button
            type="button"
            size="sm"
            class="h-8 text-xs cursor-pointer"
            @click="handleConfirm"
          >
            <Check class="size-3.5 mr-1" />
            確定套用 (Enter)
          </Button>
        </div>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
