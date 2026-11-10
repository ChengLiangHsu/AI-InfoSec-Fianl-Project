<script setup lang="ts">
import { computed } from 'vue'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

const props = withDefaults(
  defineProps<{
    currentStep: 1 | 2 | 3 | 4
    projectProgress?: number
    hasPlots?: boolean
  }>(),
  {
    projectProgress: 0,
    hasPlots: false,
  }
)

const emit = defineEmits<{
  (e: 'changeStep', step: 1 | 2 | 3 | 4): void
}>()

const isStep3Unlocked = computed(() => (props.projectProgress ?? 0) === 100)
const isStep4Unlocked = computed(() => isStep3Unlocked.value && Boolean(props.hasPlots))

function isStepUnlocked(stepId: 1 | 2 | 3 | 4): boolean {
  if (stepId === 1 || stepId === 2) return true
  if (stepId === 3) return isStep3Unlocked.value
  if (stepId === 4) return isStep4Unlocked.value
  return false
}

function getStepLockedReason(stepId: 1 | 2 | 3 | 4): string {
  if (stepId === 3) {
    return '需待步驟 1 航拍正射影像拼接完成（100%）方可解鎖小區標註'
  }
  if (stepId === 4) {
    if (!isStep3Unlocked.value) {
      return '需待步驟 1 航拍正射影像拼接完成（100%）方可解鎖'
    }
    if (!props.hasPlots) {
      return '需先於步驟 3 完成小區網格標註與儲存方可解鎖光譜分析'
    }
  }
  return ''
}

const nextStepId = computed<1 | 2 | 3 | 4>(() => {
  return Math.min(props.currentStep + 1, 4) as 1 | 2 | 3 | 4
})

const isNextUnlocked = computed<boolean>(() => {
  return isStepUnlocked(nextStepId.value)
})

const nextStepLockedReason = computed<string>(() => {
  return getStepLockedReason(nextStepId.value)
})

const nextStepLabel = computed<string>(() => {
  switch (props.currentStep) {
    case 1:
      return '下一步：試驗情境'
    case 2:
      return '下一步：小區標註'
    case 3:
      return '下一步：光譜分析'
    default:
      return ''
  }
})

function handlePrev() {
  if (props.currentStep > 1) {
    emit('changeStep', (props.currentStep - 1) as 1 | 2 | 3 | 4)
  }
}

function handleNext() {
  if (props.currentStep < 4 && isNextUnlocked.value) {
    emit('changeStep', nextStepId.value)
  }
}
</script>

<template>
  <nav
    aria-label="步驟導覽"
    class="flex items-center gap-3 rounded-2xl border border-white/15 bg-zinc-950/85 px-3 py-1.5 text-zinc-200 shadow-2xl backdrop-blur-md text-xs select-none"
  >
    <!-- 上一步按鈕 -->
    <Button
      variant="ghost"
      size="sm"
      class="h-7 gap-1 px-2.5 text-xs text-zinc-400 hover:text-white hover:bg-white/10 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
      :disabled="currentStep === 1"
      @click="handlePrev"
    >
      ← 上一步
    </Button>

    <!-- 當前進度 -->
    <span class="font-mono text-[11px] text-zinc-400 px-0.5">
      {{ currentStep }} / 4
    </span>

    <!-- 下一步按鈕：步驟 4 時完全隱藏 -->
    <template v-if="currentStep < 4">
      <!-- 已解鎖 -->
      <Button
        v-if="isNextUnlocked"
        variant="ghost"
        size="sm"
        class="h-7 gap-1 px-2.5 text-xs font-medium text-purple-300 hover:text-white hover:bg-purple-900/30 cursor-pointer"
        @click="handleNext"
      >
        <span>{{ nextStepLabel }}</span>
        <span>→</span>
      </Button>

      <!-- 未解鎖 Tooltip 提示 -->
      <TooltipProvider v-else :delay-duration="150">
        <Tooltip>
          <TooltipTrigger as-child>
            <span class="inline-flex">
              <Button
                variant="ghost"
                size="sm"
                class="h-7 gap-1 px-2.5 text-xs font-medium text-purple-300/40 cursor-not-allowed"
                disabled
              >
                <span>{{ nextStepLabel }}</span>
                <span>→</span>
              </Button>
            </span>
          </TooltipTrigger>
          <TooltipContent
            side="top"
            class="text-xs max-w-xs bg-zinc-900 text-zinc-100 border-white/15"
          >
            {{ nextStepLockedReason }}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </template>
  </nav>
</template>
