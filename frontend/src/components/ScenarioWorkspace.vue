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
import ScenarioQuestionCard from '@/components/ScenarioQuestionCard.vue'
import { useChatAgent, type InterviewQuestion } from '@/lib/useChatAgent'
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

const {
  status,
  messages,
  activeQuestion,
  loadInitialMessages,
  sendPrompt,
  injectAssistantMessage,
  setActiveQuestion,
  clearChat,
} = useChatAgent(() => props.projectId)

const INITIAL_INTERVIEW_QUESTION: InterviewQuestion = {
  id: 'init-trial-type',
  step_label: '試驗規劃 · 第 1 步',
  question: '這次無人機空拍的田間試驗主題是什麼？',
  is_multi_select: false,
  allow_custom: true,
  can_generate_now: false,
  options: [
    {
      label: '農藥藥效試驗',
      description: '比較不同藥劑或稀釋倍數（如 500x / 1000x / 2000x）的防治效果',
      recommended: true,
    },
    {
      label: '肥料肥力試驗',
      description: '比較不同肥料品項或施用比例（如 50% / 100% / 200%）的肥效表現',
      recommended: false,
    },
    {
      label: '品種比較試驗',
      description: '評估不同作物品種的長勢與外觀差異（無須劑量欄位）',
      recommended: false,
    },
    {
      label: '田間長勢與缺株監測',
      description: '分區觀察生育期、栽培管理、覆膜或異常斑塊（非用藥情境）',
      recommended: false,
    },
  ],
}

const INITIAL_REFINE_QUESTION: InterviewQuestion = {
  id: 'init-refine-mode',
  step_label: '表單調整確認',
  question: '這份試驗表單目前有什麼需要調整的嗎？',
  is_multi_select: false,
  allow_custom: true,
  can_generate_now: false,
  options: [
    {
      label: '調整實驗處理組或參數',
      description: '新增、修改或刪除處理組別與對應劑量／處理條件',
      recommended: true,
    },
    {
      label: '增減紀錄欄位',
      description: '補充或調整共通資訊（如施用日期）與小區欄位（如施用時期、是否覆膜）',
      recommended: false,
    },
    {
      label: '檢視並補強表單完整度',
      description: '依這場田間試驗目標，協助確認是否還有遺漏的關鍵紀錄項目',
      recommended: false,
    },
    {
      label: '重新規劃試驗表單',
      description: '更換試驗類型或主題，從頭建立一份新的試驗表單',
      recommended: false,
    },
  ],
}

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

function startInitialGuidedQuestion(pid: string) {
  const configured = hasConfiguredScenario(currentScenario.value)
  const scenarioTitle = currentScenario.value?.title?.trim()
  injectAssistantMessage(
    configured
      ? `目前的${scenarioTitle ? `「${scenarioTitle}」` : '試驗'}表單已就緒，若有需要微調的地方，可以從下方選擇或直接告訴我：`
      : '歡迎來到試驗情境規劃。讓我先確認這次空拍的試驗主題，再逐步為您建立合適的小區紀錄表單：',
    pid
  )
  setActiveQuestion(configured ? INITIAL_REFINE_QUESTION : INITIAL_INTERVIEW_QUESTION, pid)
}

async function initProjectChat(pid: string) {
  await loadInitialMessages(pid)
  if (messages.value.length === 0 && !greetedProjects.value[pid]) {
    greetedProjects.value[pid] = true
    startInitialGuidedQuestion(pid)
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
  setActiveQuestion(null, props.projectId)
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

async function handleQuestionAnswer(answerText: string): Promise<void> {
  if (isBusy.value || !answerText.trim()) return
  const currentQId = activeQuestion.value?.id
  if (currentQId === INITIAL_REFINE_QUESTION.id && answerText.trim() === '重新規劃試驗表單') {
    setActiveQuestion(INITIAL_INTERVIEW_QUESTION, props.projectId)
    return
  }

  let promptText = answerText.trim()
  if (currentQId === INITIAL_INTERVIEW_QUESTION.id) {
    promptText = `這次的試驗主題是「${promptText}」，請一步步引導我確認試驗細節與表單欄位。`
  } else if (currentQId === INITIAL_REFINE_QUESTION.id) {
    promptText = `針對目前的表單，我想「${promptText}」，請引導我確認需要調整的細節。`
  }
  await sendPrompt(promptText, props.projectId, {
    mode: 'scenario',
    onScenarioUpdated: handleScenarioFromAgent,
  })
}

async function handleQuestionGenerateNow(): Promise<void> {
  if (isBusy.value) return
  await sendPrompt('先不用再問了，請直接依目前討論的資訊與你的建議模板幫我建立表單。', props.projectId, {
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
  <!-- 步驟 2 採用與步驟 1、3 一致的暗色系工作區樣式 -->
  <div class="dark flex-1 h-full max-h-full min-h-0 flex flex-col px-4 sm:px-6 pt-4 pb-20 bg-black text-foreground [color-scheme:dark] overflow-hidden">
    <div
      data-testid="scenario-workspace-layout"
      class="mx-auto w-full flex-1 h-full max-h-full min-h-0 flex flex-col lg:flex-row gap-4 overflow-hidden transition-all duration-300 ease-out"
      :class="isSplitMode ? 'max-w-none' : 'max-w-3xl'"
    >
      <!-- 左側（初始置中單欄）：AI 情境訪談對話面板 -->
      <section
        data-testid="scenario-chat-panel"
        class="flex flex-col min-h-0 max-h-full rounded-2xl border border-white/15 bg-zinc-950/90 shadow-2xl backdrop-blur-md overflow-hidden transition-all duration-300 ease-out"
        :class="isSplitMode ? 'w-full flex-1 basis-0 min-w-0 min-h-0 lg:h-full' : 'w-full flex-1 h-full'"
      >
        <!-- 對話面板頂部 -->
        <header class="flex items-center justify-between gap-2 px-4 py-3 border-b border-white/10 bg-zinc-900/60 shrink-0">
          <div class="flex items-center gap-2 min-w-0">
            <div class="flex size-7 items-center justify-center rounded-lg border border-purple-400/30 bg-purple-500/15 text-purple-300 shrink-0">
              <Sparkles class="size-4" />
            </div>
            <div class="min-w-0">
              <h2 class="text-sm font-semibold text-zinc-100 truncate">
                AI 試驗情境規劃助手
              </h2>
              <p class="text-[11px] text-zinc-400 truncate">
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
              class="h-7 px-2.5 text-xs gap-1.5 shrink-0 cursor-pointer border-white/15 bg-zinc-900/80 text-zinc-200 hover:bg-zinc-800 hover:text-white"
              @click="handleManualStart"
            >
              <SlidersHorizontal class="size-3.5" />
              <span>直接手動建立表單</span>
            </Button>
            <Badge
              v-else
              variant="outline"
              class="text-[10px] text-purple-300 border-purple-400/40 bg-purple-950/40 shrink-0"
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
                class="flex h-full min-h-[160px] flex-col items-center justify-center gap-2.5 p-4 text-center text-muted-foreground my-auto select-none"
              >
                <p class="text-xs text-muted-foreground/75">
                  對話紀錄已清空，請點選下方快捷建議、直接輸入，或重新啟動 AI 互動引導
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  data-testid="restart-guided-interview-button"
                  class="h-7 px-3 text-xs gap-1.5 cursor-pointer"
                  @click="startInitialGuidedQuestion(projectId)"
                >
                  <Sparkles class="size-3.5 text-primary" />
                  開始 AI 逐題引導
                </Button>
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

              <ScenarioQuestionCard
                v-if="activeQuestion && !isBusy"
                :question="activeQuestion"
                :disabled="isBusy"
                @answer="handleQuestionAnswer"
                @generate-now="handleQuestionGenerateNow"
              />
            </ConversationContent>
            <ConversationScrollButton />
          </Conversation>

          <!-- 快捷情境標籤 + 輸入框 -->
          <div class="w-full px-3.5 pb-3.5 pt-2 space-y-2 border-t border-white/10 bg-zinc-950/95 shrink-0">
            <div data-testid="scenario-quick-suggestions" class="space-y-1.5">
              <p
                id="scenario-suggestions-heading"
                class="text-[11px] font-medium text-zinc-400"
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
                    class="inline-flex min-h-7 items-center gap-1.5 rounded-full border border-white/15 bg-zinc-900/80 px-2.5 py-1 text-xs font-medium text-zinc-200 transition-colors hover:bg-zinc-800 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
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
