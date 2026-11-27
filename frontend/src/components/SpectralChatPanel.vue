<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from '@/components/ai-elements/conversation'
import {
  Message,
  MessageBranch,
  MessageBranchContent,
  MessageContent,
  MessageResponse,
} from '@/components/ai-elements/message'
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputProvider,
  PromptInputSubmit,
  PromptInputTextarea,
  type PromptInputMessage,
} from '@/components/ai-elements/prompt-input'
import { useChatAgent } from '@/lib/useChatAgent'
import type { PlotItem } from '@/lib/usePlots'
import { Sparkles, Loader2, Trash2, ScanSearch, GitCompare, Eye, Target } from '@lucide/vue'

const props = defineProps<{
  projectId: string
  projectName?: string
  plots: PlotItem[]
  selectedPlotNumbers: number[]
  currentFormula: string
}>()

const { status, messages, loadInitialMessages, sendPrompt, clearChat } = useChatAgent(
  () => props.projectId,
  { channel: 'spectral' }
)

const isBusy = computed(() => status.value === 'submitted' || status.value === 'streaming')
const isThinking = computed(() => {
  if (!isBusy.value) return false
  const lastMsg = messages.value[messages.value.length - 1]
  return !lastMsg || lastMsg.role === 'user'
})

function formatPlotShort(plot: PlotItem): string {
  if (plot.is_control) return `#${plot.plot_number} (CK)`
  const parts = [plot.treatment, plot.dose].filter(Boolean)
  return parts.length > 0 ? `#${plot.plot_number} ${parts.join(' ')}` : `#${plot.plot_number}`
}

const targetSummary = computed(() => {
  if (props.selectedPlotNumbers.length === 0) {
    return `全田區（${props.plots.length} 區）`
  }
  const map = new Map(props.plots.map((p) => [p.plot_number, p]))
  if (props.selectedPlotNumbers.length === 1) {
    const p = map.get(props.selectedPlotNumbers[0])
    return p ? formatPlotShort(p) : `#${props.selectedPlotNumbers[0]}`
  }
  const preview = props.selectedPlotNumbers
    .slice(0, 3)
    .map((n) => `#${n}`)
    .join(', ')
  const suffix = props.selectedPlotNumbers.length > 3 ? ` 等 ${props.selectedPlotNumbers.length} 區` : ''
  return `${preview}${suffix}`
})

const currentLayerLabel = computed(() =>
  props.currentFormula === 'rgb' ? 'RGB 原圖' : props.currentFormula
)

interface QuickPrompt {
  label: string
  icon: typeof ScanSearch
  prompt: string
}

const quickPrompts = computed<QuickPrompt[]>(() => {
  if (props.selectedPlotNumbers.length === 0) {
    return [
      {
        label: '總結全田區各處理組表現',
        icon: GitCompare,
        prompt: '請根據目前全田區各處理組的光譜數值與對照組 (CK) 比較，簡明總結整體試驗表現。',
      },
      {
        label: '找出表現最弱的小區',
        icon: ScanSearch,
        prompt: '請找出全田區光譜指標表現最弱或與對照組落差最明顯的小區，並說明可能原因。',
      },
      {
        label: '視覺檢查全田區異常斑塊',
        icon: Eye,
        prompt: '請視覺判讀目前全田區影像，檢查是否有缺株、禿斑或生長不均的異常區域。',
      },
    ]
  }
  if (props.selectedPlotNumbers.length === 1) {
    const target = targetSummary.value
    return [
      {
        label: '分析此小區與 CK 差異',
        icon: GitCompare,
        prompt: `請分析目前選取的小區 ${target} 的各項適用光譜數值，以及相對對照組 (CK) 的差異意義。`,
      },
      {
        label: '視覺判讀此小區長勢與缺株',
        icon: Eye,
        prompt: `請裁切並視覺判讀小區 ${target} 的局部影像，觀察作物覆蓋度、缺株空洞或葉色變異。`,
      },
    ]
  }
  const target = targetSummary.value
  return [
    {
      label: '比較所選小區光譜差異',
      icon: GitCompare,
      prompt: `請比較目前選取的 ${target} 這幾個小區在各項適用光譜指標上的數值差異與排序。`,
    },
    {
      label: '評估處理組相較 CK 效果',
      icon: ScanSearch,
      prompt: `請根據目前選取的 ${target} 與對照組 (CK) 數據，評估各處理條件的效果表現。`,
    },
  ]
})

onMounted(() => {
  if (props.projectId) {
    void loadInitialMessages(props.projectId)
  }
})

watch(
  () => props.projectId,
  (newId) => {
    if (newId) {
      void loadInitialMessages(newId)
    }
  }
)

async function submitText(text: string): Promise<void> {
  if (isBusy.value || !text.trim()) return
  await sendPrompt(text, props.projectId, {
    mode: 'spectral',
    selectedPlotNumbers: [...props.selectedPlotNumbers],
    currentFormula: props.currentFormula,
  })
}

async function onSubmit(payload: PromptInputMessage): Promise<void> {
  await submitText(payload.text)
}

async function handleClearChat(): Promise<void> {
  if (isBusy.value || messages.value.length === 0) return
  if (typeof window !== 'undefined' && !window.confirm('確定要清空光譜分析對話紀錄嗎？（不影響步驟 2 的情境對話）')) {
    return
  }
  await clearChat(props.projectId)
}

const placeholderText = computed(() => {
  if (isBusy.value) return 'AI 正在分析光譜數值與影像中，請稍候...'
  return `針對「${targetSummary.value}」提問（選取小區不會自動發送，由您手動觸發）...`
})
</script>

<template>
  <section
    data-testid="spectral-chat-panel"
    aria-label="光譜分析代理人對話框"
    class="flex h-full min-h-0 flex-col rounded-2xl border border-border/70 bg-card text-card-foreground shadow-xs overflow-hidden"
  >
    <!-- 標頭 -->
    <header class="flex items-center justify-between gap-2 px-3.5 py-2.5 border-b border-border/50 bg-muted/20 shrink-0">
      <div class="flex items-center gap-2 min-w-0">
        <div class="flex size-7 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
          <Sparkles class="size-4" />
        </div>
        <div class="min-w-0">
          <h2 class="text-sm font-semibold text-foreground truncate">
            AI 光譜分析顧問
          </h2>
          <p class="text-[11px] text-muted-foreground truncate">
            唯讀數據與局部影像診斷 · 獨立對話紀錄
          </p>
        </div>
      </div>

      <Button
        type="button"
        data-testid="spectral-clear-chat-button"
        variant="ghost"
        size="sm"
        class="h-7 px-2 text-xs gap-1 text-muted-foreground hover:text-destructive hover:bg-destructive/10 shrink-0 cursor-pointer"
        :disabled="isBusy || messages.length === 0"
        aria-label="清空光譜分析對話紀錄"
        title="清空光譜分析對話紀錄"
        @click="handleClearChat"
      >
        <Trash2 class="size-3.5" />
        <span class="hidden xl:inline">清空</span>
      </Button>
    </header>

    <!-- 目前綁定的分析對象上下文條 -->
    <div
      data-testid="spectral-chat-context"
      class="flex flex-wrap items-center justify-between gap-1.5 px-3.5 py-2 border-b border-border/40 bg-muted/10 text-[11px] shrink-0"
    >
      <div class="flex items-center gap-1.5 min-w-0">
        <Target class="size-3.5 text-primary shrink-0" />
        <span class="text-muted-foreground shrink-0">分析對象：</span>
        <Badge
          data-testid="spectral-chat-target-badge"
          variant="secondary"
          class="text-[11px] font-medium truncate max-w-[180px]"
        >
          {{ targetSummary }}
        </Badge>
      </div>
      <Badge variant="outline" class="font-mono text-[10px] shrink-0">
        圖層：{{ currentLayerLabel }}
      </Badge>
    </div>

    <!-- 對話內容區 -->
    <div class="flex-1 min-h-0 flex flex-col overflow-hidden">
      <Conversation class="flex-1 min-h-0">
        <ConversationContent>
          <div
            v-if="messages.length === 0 && !isThinking"
            data-testid="spectral-chat-empty"
            class="flex h-full min-h-[160px] flex-col items-center justify-center gap-2 p-5 text-center text-muted-foreground my-auto select-none"
          >
            <Sparkles class="size-6 text-primary/60" />
            <p class="text-xs font-medium text-foreground/85">
              在右側地圖點選小區即可切換分析對象
            </p>
            <p class="text-[11px] text-muted-foreground/80 max-w-xs leading-relaxed">
              選取小區不會自動耗用 AI 總結；需要解讀數據或視覺檢查時，請點選下方快捷分析按鈕或直接輸入問題。
            </p>
          </div>

          <MessageBranch v-for="message in messages" :key="message.key" :default-branch="0">
            <MessageBranchContent>
              <Message
                v-for="version in message.versions"
                :key="`${message.key}-${version.id}`"
                :from="message.role"
              >
                <MessageContent>
                  <MessageResponse
                    v-if="message.role === 'assistant'"
                    :content="version.content"
                    class="text-sm leading-relaxed"
                  />
                  <span v-else class="whitespace-pre-wrap">{{ version.content }}</span>
                </MessageContent>
              </Message>
            </MessageBranchContent>
          </MessageBranch>

          <div
            v-if="isThinking"
            class="flex items-center gap-2 rounded-lg border border-border/50 bg-muted/40 px-3 py-2 text-xs text-muted-foreground w-fit animate-pulse my-2"
          >
            <Loader2 class="size-3.5 animate-spin text-primary" />
            <span>正在分析「{{ targetSummary }}」光譜資料...</span>
          </div>
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      <!-- 手動觸發快捷分析與輸入框 -->
      <div class="w-full px-3 pb-3 pt-2 space-y-2 border-t border-border/40 bg-background shrink-0">
        <div class="flex flex-wrap items-center gap-1.5">
          <button
            v-for="item in quickPrompts"
            :key="item.label"
            type="button"
            data-testid="spectral-quick-prompt"
            :disabled="isBusy"
            class="inline-flex min-h-7 items-center gap-1.5 rounded-full border border-border/80 bg-muted/40 px-2.5 py-1 text-[11px] font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            @click="submitText(item.prompt)"
          >
            <component :is="item.icon" class="size-3 shrink-0 text-primary" aria-hidden="true" />
            <span>{{ item.label }}</span>
          </button>
        </div>

        <PromptInputProvider @submit="onSubmit">
          <PromptInput multiple global-drop class="w-full">
            <PromptInputBody>
              <PromptInputTextarea :placeholder="placeholderText" :disabled="isBusy" />
            </PromptInputBody>
            <PromptInputFooter>
              <PromptInputSubmit :disabled="isBusy" :status="status" />
            </PromptInputFooter>
          </PromptInput>
        </PromptInputProvider>
      </div>
    </div>
  </section>
</template>
