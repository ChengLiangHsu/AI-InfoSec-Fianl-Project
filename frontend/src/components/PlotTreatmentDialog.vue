<script setup lang="ts">
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Trash2, Check, X } from '@lucide/vue'

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
  color?: string
}

const props = defineProps<{
  open: boolean
  plotNumber?: number | null
  plotNumbers?: number[]
  isNewPlot?: boolean
  initialTreatment?: string
  initialDose?: string
  initialIsControl?: boolean
  isMixed?: boolean
  existingTreatments: ExistingTreatment[]
}>()

const emit = defineEmits<{
  (e: 'update:open', val: boolean): void
  (e: 'confirm', data: TreatmentData): void
  (e: 'cancel'): void
  (e: 'delete', payload: { plotNumber: number | null; plotNumbers: number[] }): void
}>()

function isSelected(preset: ExistingTreatment): boolean {
  if (props.isMixed) return false
  if (props.initialIsControl && preset.isControl) return true
  if (!props.initialIsControl && !preset.isControl) {
    const initialTrt = (props.initialTreatment || '').trim()
    const initialDs = (props.initialDose || '').trim()
    const presetTrt = (preset.treatment || '').trim()
    const presetDs = (preset.dose || '').trim()
    return initialTrt === presetTrt && initialDs === presetDs
  }
  return false
}

function handleSelectPreset(preset: ExistingTreatment): void {
  emit('confirm', {
    isControl: preset.isControl,
    treatment: preset.isControl ? '' : preset.treatment.trim(),
    dose: preset.isControl ? '' : preset.dose.trim(),
  })
  emit('update:open', false)
}

function handleCancel(): void {
  emit('cancel')
  emit('update:open', false)
}

function handleDelete(): void {
  const targetNumbers = props.plotNumbers && props.plotNumbers.length > 0
    ? props.plotNumbers
    : (props.plotNumber !== null && props.plotNumber !== undefined ? [props.plotNumber] : [])

  emit('delete', {
    plotNumber: props.plotNumber ?? null,
    plotNumbers: targetNumbers,
  })
  emit('update:open', false)
}

function onOpenChange(val: boolean): void {
  if (!val) {
    handleCancel()
  } else {
    emit('update:open', true)
  }
}
</script>

<template>
  <Dialog :open="open" @update:open="onOpenChange">
    <DialogContent class="sm:max-w-[420px] select-none">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2 text-base">
          <span
            v-if="plotNumbers && plotNumbers.length > 1"
            class="flex px-2 h-6 items-center justify-center rounded-md bg-primary/10 text-xs font-bold text-primary font-mono"
          >
            共 {{ plotNumbers.length }} 個小區
          </span>
          <span
            v-else
            class="flex size-6 items-center justify-center rounded-md bg-primary/10 text-xs font-bold text-primary font-mono"
          >
            #{{ plotNumber ?? '?' }}
          </span>
          <span>{{ (plotNumbers && plotNumbers.length > 1) ? '批次小區處理組別設定' : '小區處理組別設定' }}</span>
        </DialogTitle>
        <DialogDescription class="text-xs text-muted-foreground">
          {{ (plotNumbers && plotNumbers.length > 1)
            ? '點選下方任一組別即可批次套用至所有已選小區。'
            : '點選下方任一組別即可快速為此小區套用設定。'
          }}
        </DialogDescription>
      </DialogHeader>

      <div class="flex flex-col gap-2 py-2 max-h-[360px] overflow-y-auto pr-1">
        <button
          v-for="(preset, idx) in existingTreatments"
          :key="idx"
          type="button"
          class="flex items-center justify-between w-full px-3.5 py-2.5 rounded-lg border text-xs text-left transition-all cursor-pointer select-none group"
          :class="[
            isSelected(preset)
              ? 'border-primary bg-primary/10 font-semibold shadow-xs ring-1 ring-primary/20'
              : 'border-border bg-card/60 hover:bg-accent/80 hover:border-accent-foreground/20 text-foreground'
          ]"
          @click="handleSelectPreset(preset)"
        >
          <div class="flex items-center gap-2.5 min-w-0">
            <span
              class="size-3 rounded-full shrink-0 border border-black/10 dark:border-white/20 shadow-xs transition-transform group-hover:scale-110"
              :style="{ backgroundColor: preset.color || (preset.isControl ? '#94a3b8' : '#3b82f6') }"
            />
            <span class="truncate">{{ preset.label }}</span>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <span v-if="preset.dose && !preset.isControl" class="text-[11px] text-muted-foreground font-mono">
              {{ preset.dose }}
            </span>
            <Check v-if="isSelected(preset)" class="size-4 text-primary shrink-0" />
          </div>
        </button>
      </div>

      <DialogFooter class="flex sm:justify-between items-center gap-2 pt-2 border-t">
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
            {{ (plotNumbers && plotNumbers.length > 1) ? `刪除選取的 ${plotNumbers.length} 個小區` : '刪除此小區' }}
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
            關閉
          </Button>
        </div>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
