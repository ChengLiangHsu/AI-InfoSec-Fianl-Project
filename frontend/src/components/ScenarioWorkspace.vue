<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
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
import ProjectScenarioCard from '@/components/ProjectScenarioCard.vue'
import { useChatAgent } from '@/lib/useChatAgent'
import {
  createManualDefaultScenario,
  hasConfiguredScenario,
  type ScenarioData,
} from '@/lib/scenarioSchema'
import {
  Sparkles,
  Loader2,
  Bug,
  FlaskConical,
  Sprout,
  ScanSearch,
  SlidersHorizontal,
  MessageSquare,
  Wand2,
  ListPlus,
  CalendarPlus,
  Plus,
  ToggleLeft,
  Pencil,
  Trash2,
} from '@lucide/vue'

const props = withDefaults(
  defineProps<{
    projectId: string
    projectName?: string
    initialScenario?: ScenarioData | null
    fileNames?: string[]
    projectProgress?: number
  }>(),
  {
    initialScenario: null,
    fileNames: () => [],
    projectProgress: 0,
  }
)

const emit = defineEmits<{
  (e: 'update:scenario', scenario: ScenarioData): void
  (e: 'saved', scenario: ScenarioData): void
}>()

const { status, messages, loadInitialMessages, sendPrompt, injectAssistantMessage, clearChat } = useChatAgent(
  () => props.projectId
)

const isBusy = computed(() => status.value === 'submitted' || status.value === 'streaming')
const isThinking = computed(() => {
  if (!isBusy.value) return false
  const lastMsg = messages.value[messages.value.length - 1]
  return !lastMsg || lastMsg.role === 'user'
})

const currentScenario = ref<ScenarioData | null>(props.initialScenario ?? null)
const manualExpanded = ref(false)
const greetedProjects = ref<Record<string, boolean>>({})

const isSplitMode = computed<boolean>(
  () => manualExpanded.value || hasConfiguredScenario(currentScenario.value)
)

const hasUserMessage = computed<boolean>(() =>
  messages.value.some((msg) => msg.role === 'user')
)

interface QuickSuggestion {
  label: string
  icon: typeof Bug
  iconClass: string
  prompt: string
}

const initialSuggestions: QuickSuggestion[] = [
  {
    label: '水稻農藥藥效（快得寧 500x/1000x/2000x）',
    icon: Bug,
    iconClass: 'text-primary',
    prompt: '我要做水稻殺蟲劑藥效試驗，測試藥劑「快得寧」500x、1000x、2000x 三個稀釋倍數與對照組，請直接幫我建立試驗表單。',
  },
  {
    label: '玉米肥料試驗（50%/100%/200%）',
    icon: FlaskConical,
    iconClass: 'text-sky-500',
    prompt: '我要做玉米肥料肥力試驗，使用「特肥一號」，比較減量 50%、標準 100%、倍量 200% 與對照組，請直接幫我建立試驗表單。',
  },
  {
    label: '水稻品種比較（台農71/台南11/高雄147）',
    icon: Sprout,
    iconClass: 'text-emerald-500',
    prompt: '我要做水稻品種比較試驗（不需要劑量欄位），比較台農71號、台南11號、高雄147號，並紀錄播種日期與是否覆膜，請直接幫我建立試驗表單。',
  },
  {
    label: '田間長勢與缺株監測',
    icon: ScanSearch,
    iconClass: 'text-amber-500',
    prompt: '我要做甘藍田間長勢與缺株監測（非用藥情境），分區紀錄生育期與缺株程度，請直接幫我建立試驗表單。',
  },
  {
    label: '先從問答開始（多輪引導）',
    icon: MessageSquare,
    iconClass: 'text-muted-foreground',
    prompt: '我想規劃一個田間農藥藥效試驗，請先跟我確認需要哪些資訊。',
  },
]

const interviewFollowUpSuggestions: QuickSuggestion[] = [
  {
    label: '水稻＋快得寧 500x/1000x/2000x',
    icon: Bug,
    iconClass: 'text-primary',
    prompt: '作物是水稻，目標病蟲害是飛蝨，預計測試「快得寧」500x、1000x、2000x 三個稀釋倍數，請幫我生成表單。',
  },
  {
    label: '改做水稻品種比較（無劑量）',
    icon: Sprout,
    iconClass: 'text-emerald-500',
    prompt: '這次不做用藥，改做水稻品種比較：台農71號、台南11號、高雄147號，請幫我生成表單。',
  },
  {
    label: '直接套用建議模板建表單',
    icon: Wand2,
    iconClass: 'text-amber-500',
    prompt: '先不用再問了，請直接依你的建議模板幫我生成表單草稿。',
  },
]

const splitModeSuggestions: QuickSuggestion[] = [
  {
    label: '新增「施用時期」下拉欄位',
    icon: ListPlus,
    iconClass: 'text-primary',
    prompt: '請在處理組欄位中新增一個「施用時期」下拉選單欄位，選項為「分蘗期」、「抽穗期」、「乳熟期」。',
  },
  {
    label: '新增「施用日期」日期欄位',
    icon: CalendarPlus,
    iconClass: 'text-sky-500',
    prompt: '請在試驗共通資訊中新增一個「施用日期」的日期欄位。',
  },
  {
    label: '新增一組實驗處理組',
    icon: Plus,
    iconClass: 'text-emerald-500',
    prompt: '請幫我再新增一組實驗處理組，並自動配一個不重複的高對比顏色。',
  },
  {
    label: '新增「是否覆膜」開關欄位',
    icon: ToggleLeft,
    iconClass: 'text-amber-500',
    prompt: '請在處理組欄位中新增一個「是否覆膜」的開關（boolean）欄位。',
  },
  {
    label: '修改對照組名稱',
    icon: Pencil,
    iconClass: 'text-muted-foreground',
    prompt: '請把對照組名稱改為「空白未處理對照 (CK)」。',
  },
]

const suggestionGroupLabel = computed<string>(() => {
  if (isSplitMode.value) return '快速測試表單微調（點擊直接送出）'
  if (hasUserMessage.value) return '快速回覆（點擊直接送出）'
  return '快速測試情境（點擊直接送出）'
})

const activeSuggestions = computed<QuickSuggestion[]>(() => {
  if (isSplitMode.value) return splitModeSuggestions
  if (hasUserMessage.value) return interviewFollowUpSuggestions
  return initialSuggestions
})

async function initProjectChat(pid: string) {
  await loadInitialMessages(pid)
  if (messages.value.length === 0 && !greetedProjects.value[pid]) {
    greetedProjects.value[pid] = true
    injectAssistantMessage(
      '嗨！這次無人機空拍主要是做什麼田間試驗呢？跟我聊聊作物、試驗目的，以及需不需要紀錄藥劑劑量，我來幫你動態生成下一步框選小區要用的表單～',
      pid
    )
  }
}

onMounted(() => {
  if (props.projectId) {
    initProjectChat(props.projectId)
  }
})

watch(
  () => props.projectId,
  (newId) => {
    manualExpanded.value = false
    currentScenario.value = props.initialScenario ?? null
    if (newId) {
      initProjectChat(newId)
    }
  }
)

watch(
  () => props.initialScenario,
  (newSc) => {
    currentScenario.value = newSc ?? null
  }
)

function handleScenarioFromAgent(scenario: ScenarioData) {
  currentScenario.value = scenario
  emit('update:scenario', scenario)
  emit('saved', scenario)
}

function handleCardScenarioUpdated(scenario: ScenarioData) {
  currentScenario.value = scenario
  emit('update:scenario', scenario)
}

function handleCardScenarioSaved(scenario: ScenarioData) {
  currentScenario.value = scenario
  emit('saved', scenario)
}

async function handleManualStart() {
  const defaultScenario = createManualDefaultScenario()
  currentScenario.value = defaultScenario
  manualExpanded.value = true
  emit('update:scenario', defaultScenario)
  if (props.projectId && props.projectId !== 'home') {
    try {
      const res = await fetch(`/api/task/scenario/${props.projectId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: defaultScenario }),
      })
      const data = await res.json().catch(() => null)
      if (res.ok && data?.data) {
        currentScenario.value = data.data
        emit('update:scenario', data.data)
        emit('saved', data.data)
      }
    } catch (err) {
      console.error('初始化手動表單失敗:', err)
    }
  }
}

async function onSubmit(payload: PromptInputMessage): Promise<void> {
  if (isBusy.value || !payload.text.trim()) return
  await sendPrompt(payload.text, props.projectId, {
    mode: 'scenario',
    onScenarioUpdated: handleScenarioFromAgent,
  })
}

async function triggerQuickScenario(promptText: string): Promise<void> {
  if (isBusy.value) return
  await sendPrompt(promptText, props.projectId, {
    mode: 'scenario',
    onScenarioUpdated: handleScenarioFromAgent,
  })
}

async function handleClearChat(): Promise<void> {
  if (isBusy.value || messages.value.length === 0) return
  if (typeof window !== 'undefined' && !window.confirm('確定要清空目前的對話紀錄嗎？')) {
    return
  }
  await clearChat(props.projectId)
}

const placeholderText = computed(() => {
  if (isBusy.value) return 'AI 正在整理試驗情境與表單中，請稍候...'
  if (isSplitMode.value) {
    return '繼續跟 AI 調整表單（例：新增「施用時期」下拉欄位、加入 2000x 組別）...'
  }
  return '描述你的田間試驗情境（作物、試驗目的、要比較的組別）...'
})
</script>

<template>
  <div class="flex-1 h-full max-h-full min-h-0 flex flex-col px-4 sm:px-6 pt-4 pb-20 bg-muted/10 overflow-hidden">
    <div
      data-testid="scenario-workspace-layout"
      class="mx-auto w-full flex-1 h-full max-h-full min-h-0 flex flex-col lg:flex-row gap-4 overflow-hidden transition-all duration-300 ease-out"
      :class="isSplitMode ? 'max-w-none' : 'max-w-3xl'"
    >
      <!-- 左側（初始置中單欄）：AI 情境訪談對話面板 -->
      <section
        data-testid="scenario-chat-panel"
        class="flex flex-col min-h-0 max-h-full rounded-2xl border border-border/70 bg-card shadow-xs overflow-hidden transition-all duration-300 ease-out"
        :class="isSplitMode ? 'w-full flex-1 basis-0 min-w-0 min-h-0 lg:h-full' : 'w-full flex-1 h-full'"
      >
        <!-- 對話面板頂部 -->
        <header class="flex items-center justify-between gap-2 px-4 py-3 border-b border-border/50 bg-muted/20 shrink-0">
          <div class="flex items-center gap-2 min-w-0">
            <div class="flex size-7 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
              <Sparkles class="size-4" />
            </div>
            <div class="min-w-0">
              <h2 class="text-sm font-semibold text-foreground truncate">
                AI 試驗情境規劃助手
              </h2>
              <p class="text-[11px] text-muted-foreground truncate">
                {{ isSplitMode ? '隨時透過對話新增欄位或調整組別，並自動存檔' : '聊完情境後將自動為你展開右側多型態實驗表單' }}
              </p>
            </div>
          </div>

          <div class="flex items-center gap-1.5 shrink-0">
            <Button
              v-if="!isSplitMode"
              type="button"
              variant="outline"
              size="sm"
              class="h-7 px-2.5 text-xs gap-1.5 shrink-0 cursor-pointer"
              @click="handleManualStart"
            >
              <SlidersHorizontal class="size-3.5" />
              <span>直接手動建立表單</span>
            </Button>
            <Badge
              v-else
              variant="outline"
              class="text-[10px] text-primary border-primary/30 bg-primary/5 shrink-0"
            >
              雙向同步中
            </Badge>

            <Button
              type="button"
              data-testid="clear-chat-button"
              variant="ghost"
              size="sm"
              class="h-7 px-2 text-xs gap-1 text-muted-foreground hover:text-destructive hover:bg-destructive/10 shrink-0 cursor-pointer"
              :disabled="isBusy || messages.length === 0"
              aria-label="清空對話紀錄"
              title="清空對話紀錄"
              @click="handleClearChat"
            >
              <Trash2 class="size-3.5" />
              <span class="hidden sm:inline">清空對話</span>
            </Button>
          </div>
        </header>

        <!-- 對話內容區 -->
        <div class="flex-1 min-h-0 flex flex-col overflow-hidden">
          <Conversation class="flex-1 min-h-0">
            <ConversationContent>
              <div
                v-if="messages.length === 0 && !isThinking"
                data-testid="scenario-chat-empty"
                class="flex h-full min-h-[160px] flex-col items-center justify-center p-4 text-center text-muted-foreground my-auto select-none"
              >
                <p class="text-xs text-muted-foreground/75">
                  對話紀錄已清空，請點選下方快捷建議或直接輸入開始新的討論
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
                      <MessageResponse v-if="message.role === 'assistant'" :content="version.content" class="text-sm leading-relaxed" />
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
                <span>AI 正在分析情境並建構表單...</span>
              </div>
            </ConversationContent>
            <ConversationScrollButton />
          </Conversation>

          <!-- 快捷情境標籤 + 輸入框 -->
          <div class="w-full px-3.5 pb-3.5 pt-2 space-y-2 border-t border-border/40 bg-background shrink-0">
            <div data-testid="scenario-quick-suggestions" class="space-y-1.5">
              <p
                id="scenario-suggestions-heading"
                class="text-[11px] font-medium text-muted-foreground"
              >
                {{ suggestionGroupLabel }}
              </p>
              <ul
                role="list"
                aria-labelledby="scenario-suggestions-heading"
                class="flex flex-wrap items-center gap-1.5 pb-0.5 list-none m-0 p-0"
              >
                <li v-for="item in activeSuggestions" :key="item.label">
                  <button
                    type="button"
                    data-testid="scenario-suggestion-chip"
                    :disabled="isBusy"
                    class="inline-flex min-h-7 items-center gap-1.5 rounded-full border border-border/80 bg-muted/40 px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                    @click="triggerQuickScenario(item.prompt)"
                  >
                    <component
                      :is="item.icon"
                      aria-hidden="true"
                      class="size-3.5 shrink-0"
                      :class="item.iconClass"
                    />
                    <span>{{ item.label }}</span>
                  </button>
                </li>
              </ul>
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

      <!-- 右側（討論出情境或手動啟動後展開）：多型態動態試驗表單 -->
      <Transition
        enter-active-class="transition-all duration-300 ease-out"
        enter-from-class="opacity-0 translate-x-4"
        enter-to-class="opacity-100 translate-x-0"
      >
        <div
          v-if="isSplitMode"
          data-testid="scenario-form-panel"
          class="w-full flex-1 basis-0 min-w-0 min-h-0 lg:h-full overflow-y-auto pr-0.5"
        >
          <ProjectScenarioCard
            :project-id="projectId"
            :project-name="projectName"
            :initial-scenario="currentScenario"
            :file-names="fileNames"
            :project-progress="projectProgress"
            @update:scenario="handleCardScenarioUpdated"
            @saved="handleCardScenarioSaved"
          />
        </div>
      </Transition>
    </div>
  </div>
</template>
