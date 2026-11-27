<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import type { InterviewQuestion } from '@/lib/useChatAgent'
import { Check, HelpCircle, Send, Sparkles, Wand2 } from '@lucide/vue'

const props = withDefaults(
  defineProps<{
    question: InterviewQuestion
    disabled?: boolean
  }>(),
  {
    disabled: false,
  }
)

const emit = defineEmits<{
  (e: 'answer', answerText: string): void
  (e: 'generateNow'): void
}>()

const selectedLabels = ref<string[]>([])
const showCustomInput = ref(false)
const customText = ref('')

watch(
  () => props.question.id,
  () => {
    selectedLabels.value = []
    showCustomInput.value = false
    customText.value = ''
  }
)

const isMulti = computed(() => Boolean(props.question.is_multi_select))
const allowCustom = computed(() => props.question.allow_custom !== false)

const canSubmitMulti = computed(() => {
  return selectedLabels.value.length > 0 || customText.value.trim().length > 0
})

function isSelected(label: string): boolean {
  return selectedLabels.value.includes(label)
}

function handleOptionClick(label: string) {
  if (props.disabled) return
  if (!isMulti.value) {
    emit('answer', label)
    return
  }
  const idx = selectedLabels.value.indexOf(label)
  if (idx >= 0) {
    selectedLabels.value = selectedLabels.value.filter((item) => item !== label)
  } else {
    selectedLabels.value = [...selectedLabels.value, label]
  }
}

function submitCustomOnly() {
  if (props.disabled) return
  const text = customText.value.trim()
  if (!text) return
  emit('answer', text)
  customText.value = ''
  showCustomInput.value = false
}

function submitMultiSelection() {
  if (props.disabled || !canSubmitMulti.value) return
  const parts = [...selectedLabels.value]
  const custom = customText.value.trim()
  if (custom) {
    parts.push(custom)
  }
  emit('answer', parts.join('、'))
  selectedLabels.value = []
  customText.value = ''
  showCustomInput.value = false
}
</script>

<template>
  <section
    data-testid="scenario-question-card"
    aria-label="試驗規劃引導問題"
    class="my-2 w-full max-w-full min-w-0 rounded-xl border border-primary/25 bg-card/95 shadow-xs overflow-hidden"
  >
    <div class="flex items-center justify-between gap-2 px-3.5 py-2.5 bg-primary/5 border-b border-primary/15 min-w-0">
      <div class="flex items-center gap-1.5 min-w-0">
        <HelpCircle class="size-3.5 text-primary shrink-0" aria-hidden="true" />
        <span class="text-[11px] font-semibold text-primary truncate">
          {{ question.step_label || '試驗規劃確認' }}
        </span>
      </div>
      <Badge variant="outline" class="text-[10px] px-1.5 py-0 h-4.5 border-primary/30 text-muted-foreground shrink-0 whitespace-nowrap">
        {{ isMulti ? '可複選' : '單選' }}
      </Badge>
    </div>

    <div class="p-3.5 space-y-2.5">
      <p data-testid="scenario-question-title" class="text-sm font-semibold text-foreground leading-snug">
        {{ question.question }}
      </p>

      <div class="space-y-1.5" role="group" :aria-label="question.question">
        <button
          v-for="(opt, idx) in question.options"
          :key="opt.label"
          type="button"
          data-testid="scenario-question-option"
          :disabled="disabled"
          :aria-pressed="isMulti ? isSelected(opt.label) : undefined"
          class="w-full text-left flex items-start gap-2.5 rounded-lg border px-3 py-2 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          :class="[
            isMulti && isSelected(opt.label)
              ? 'border-primary bg-primary/10'
              : opt.recommended
                ? 'border-primary/40 bg-primary/5 hover:bg-primary/10'
                : 'border-border/80 bg-background hover:bg-accent/60 hover:border-border',
          ]"
          @click="handleOptionClick(opt.label)"
        >
          <span
            class="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-md border text-[11px] font-semibold transition-colors"
            :class="[
              isMulti && isSelected(opt.label)
                ? 'border-primary bg-primary text-primary-foreground'
                : opt.recommended
                  ? 'border-primary/40 bg-primary/10 text-primary'
                  : 'border-border bg-muted/50 text-muted-foreground',
            ]"
          >
            <Check v-if="isMulti && isSelected(opt.label)" class="size-3" />
            <template v-else>{{ idx + 1 }}</template>
          </span>

          <div class="flex-1 min-w-0">
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="text-xs sm:text-[13px] font-medium text-foreground leading-snug">
                {{ opt.label }}
              </span>
              <Badge
                v-if="opt.recommended"
                data-testid="scenario-question-recommended"
                variant="secondary"
                class="h-4 px-1.5 text-[10px] font-medium bg-primary/15 text-primary border-0 gap-0.5"
              >
                <Sparkles class="size-2.5" aria-hidden="true" />
                推薦
              </Badge>
            </div>
            <p v-if="opt.description" class="mt-0.5 text-[11px] text-muted-foreground leading-relaxed">
              {{ opt.description }}
            </p>
          </div>
        </button>
      </div>

      <!-- 自訂輸入（其他） -->
      <div v-if="allowCustom" class="pt-0.5">
        <button
          v-if="!showCustomInput"
          type="button"
          data-testid="scenario-question-custom-toggle"
          :disabled="disabled"
          class="text-xs text-muted-foreground hover:text-foreground underline underline-offset-4 cursor-pointer disabled:opacity-50"
          @click="showCustomInput = true"
        >
          其他（自行輸入補充說明）
        </button>
        <div v-else class="flex items-center gap-1.5">
          <Input
            v-model="customText"
            data-testid="scenario-question-custom-input"
            type="text"
            :disabled="disabled"
            placeholder="輸入你的自訂回答..."
            class="h-8 text-xs"
            @keydown.enter.prevent="isMulti ? submitMultiSelection() : submitCustomOnly()"
          />
          <Button
            v-if="!isMulti"
            type="button"
            size="sm"
            data-testid="scenario-question-custom-submit"
            class="h-8 px-2.5 text-xs gap-1 shrink-0 cursor-pointer"
            :disabled="disabled || !customText.trim()"
            @click="submitCustomOnly"
          >
            <Send class="size-3" />
            送出
          </Button>
        </div>
      </div>

      <!-- 多選確認列 / 直接建表單 -->
      <div
        v-if="isMulti || question.can_generate_now"
        class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border/50"
      >
        <Button
          v-if="question.can_generate_now"
          type="button"
          variant="outline"
          size="sm"
          data-testid="scenario-question-generate-now"
          class="h-7 px-2.5 text-xs gap-1.5 cursor-pointer"
          :disabled="disabled"
          @click="emit('generateNow')"
        >
          <Wand2 class="size-3.5 text-amber-500" />
          直接依目前資訊建立表單
        </Button>
        <div v-else />

        <Button
          v-if="isMulti"
          type="button"
          size="sm"
          data-testid="scenario-question-multi-submit"
          class="h-7 px-3 text-xs gap-1.5 cursor-pointer"
          :disabled="disabled || !canSubmitMulti"
          @click="submitMultiSelection"
        >
          <Send class="size-3" />
          確認送出{{ selectedLabels.length > 0 ? ` (${selectedLabels.length})` : '' }}
        </Button>
      </div>
    </div>
  </section>
</template>
