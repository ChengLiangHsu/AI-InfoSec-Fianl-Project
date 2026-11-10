<script setup lang="ts">
import { computed } from 'vue'
import {
  Check,
  Lock,
  ChevronRight,
  ImageIcon,
  FlaskConical,
  Grid,
} from '@lucide/vue'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

export interface StepItem {
  id: 1 | 2 | 3
  title: string
  subtitle: string
  icon: any
}

const props = withDefaults(
  defineProps<{
    currentStep: 1 | 2 | 3
    projectProgress?: number
  }>(),
  {
    projectProgress: 0,
  }
)

const emit = defineEmits<{
  (e: 'changeStep', step: 1 | 2 | 3): void
}>()

const steps: StepItem[] = [
  {
    id: 1,
    title: '步驟 1：航拍與正射結果',
    subtitle: '拼接進度與正射底圖檢視',
    icon: ImageIcon,
  },
  {
    id: 2,
    title: '步驟 2：試驗情境設定',
    subtitle: '農藥、除草劑與劑量設定',
    icon: FlaskConical,
  },
  {
    id: 3,
    title: '步驟 3：試驗小區標註',
    subtitle: '小區網格劃分與處理組配置',
    icon: Grid,
  },
]

const isStep3Unlocked = computed(() => (props.projectProgress ?? 0) === 100)

function isStepUnlocked(stepId: 1 | 2 | 3): boolean {
  if (stepId === 1 || stepId === 2) return true
  return isStep3Unlocked.value
}

function handleStepClick(stepId: 1 | 2 | 3) {
  if (!isStepUnlocked(stepId)) return
  if (stepId !== props.currentStep) {
    emit('changeStep', stepId)
  }
}
</script>

<template>
  <nav aria-label="專案三步驟工作流導覽" class="w-full rounded-xl border bg-card p-3 shadow-xs">
    <ol class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 sm:gap-3">
      <template v-for="(step, index) in steps" :key="step.id">
        <!-- 步驟項目本體 -->
        <li class="flex-1 min-w-0">
          <TooltipProvider :delay-duration="150">
            <Tooltip>
              <TooltipTrigger as-child>
                <button
                  type="button"
                  :data-tour="`step-tab-${step.id}`"
                  class="group flex w-full items-center gap-3 rounded-lg border p-2.5 sm:p-3 text-left transition-all duration-200 outline-none select-none"
                  :class="[
                    currentStep === step.id
                      ? 'border-primary/50 bg-primary/5 shadow-xs ring-1 ring-primary/20'
                      : isStepUnlocked(step.id)
                        ? 'border-transparent hover:border-border hover:bg-muted/50 cursor-pointer'
                        : 'border-transparent opacity-50 cursor-not-allowed bg-muted/20'
                  ]"
                  :aria-current="currentStep === step.id ? 'step' : undefined"
                  :disabled="!isStepUnlocked(step.id)"
                  @click="handleStepClick(step.id)"
                >
                  <!-- 步驟圖示徽章 -->
                  <div
                    class="flex size-9 shrink-0 items-center justify-center rounded-lg border transition-colors"
                    :class="[
                      currentStep === step.id
                        ? 'border-primary bg-primary text-primary-foreground font-bold shadow-xs'
                        : isStepUnlocked(step.id) && currentStep > step.id
                          ? 'border-primary/30 bg-primary/10 text-primary'
                          : !isStepUnlocked(step.id)
                            ? 'border-border/60 bg-muted/60 text-muted-foreground'
                            : 'border-border bg-background text-muted-foreground group-hover:border-primary/30 group-hover:text-foreground'
                    ]"
                  >
                    <!-- 已完成打勾 -->
                    <Check
                      v-if="isStepUnlocked(step.id) && currentStep > step.id"
                      class="size-4.5 stroke-[2.5]"
                    />
                    <!-- 未解鎖鎖定 -->
                    <Lock
                      v-else-if="!isStepUnlocked(step.id)"
                      class="size-4 stroke-[2]"
                    />
                    <!-- 當前或待點擊圖示 -->
                    <component
                      :is="step.icon"
                      v-else
                      class="size-4.5"
                    />
                  </div>

                  <!-- 步驟標題文字 -->
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                      <span
                        class="text-xs sm:text-sm font-semibold truncate transition-colors"
                        :class="[
                          currentStep === step.id
                            ? 'text-foreground font-bold'
                            : isStepUnlocked(step.id)
                              ? 'text-muted-foreground group-hover:text-foreground'
                              : 'text-muted-foreground/60'
                        ]"
                      >
                        {{ step.title }}
                      </span>
                    </div>
                    <p
                      class="text-[11px] sm:text-xs truncate transition-colors"
                      :class="[
                        currentStep === step.id
                          ? 'text-primary font-medium'
                          : 'text-muted-foreground/70'
                      ]"
                    >
                      {{ step.subtitle }}
                    </p>
                  </div>
                </button>
              </TooltipTrigger>
              <TooltipContent v-if="!isStepUnlocked(step.id)" side="bottom" class="text-xs">
                需待步驟 1 航拍正射影像拼接完成（100%）方可解鎖小區標註
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </li>

        <!-- 步驟間分隔指示箭頭 (僅桌面排版顯示) -->
        <li
          v-if="index < steps.length - 1"
          aria-hidden="true"
          class="hidden sm:flex shrink-0 items-center justify-center text-muted-foreground/40"
        >
          <ChevronRight class="size-4 stroke-[2]" />
        </li>
      </template>
    </ol>
  </nav>
</template>
