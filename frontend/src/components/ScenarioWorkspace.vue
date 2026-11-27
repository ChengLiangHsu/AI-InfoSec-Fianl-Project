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

const { status, messages, loadInitialMessages, sendPrompt, injectAssistantMessage } = useChatAgent(
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

const quickScenarios = [
  {
    label: '農藥藥效試驗',
    icon: Bug,
    iconClass: 'text-primary',
    prompt: '我想規劃農藥藥效試驗，請跟我確認作物、藥劑名稱與劑量倍數來生成表單。',
  },
  {
    label: '肥料肥力試驗',
    icon: FlaskConical,
    iconClass: 'text-sky-500',
    prompt: '我想規劃肥料肥力試驗，請跟我確認作物、肥料品項與施用量來生成表單。',
  },
  {
    label: '品種比較試驗',
    icon: Sprout,
    iconClass: 'text-emerald-500',
    prompt: '我要做作物品種比較試驗（不需要劑量欄位），請跟我確認品種與想紀錄的項目來生成表單。',
  },
  {
    label: '長勢與缺株監測',
    icon: ScanSearch,
    iconClass: 'text-amber-500',
    prompt: '我要做田間長勢與缺株監測（非用藥情境），請協助我設計分區紀錄表單。',
  },
]

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
        </header>

        <!-- 對話內容區 -->
        <div class="flex-1 min-h-0 flex flex-col overflow-hidden">
          <Conversation class="flex-1 min-h-0">
            <ConversationContent>
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
            <div v-if="!isSplitMode" class="flex flex-wrap items-center gap-1.5 pb-0.5">
              <button
                v-for="item in quickScenarios"
                :key="item.label"
                type="button"
                :disabled="isBusy"
                class="inline-flex items-center gap-1.5 rounded-full border border-border/80 bg-muted/40 px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                @click="triggerQuickScenario(item.prompt)"
              >
                <component :is="item.icon" class="size-3.5" :class="item.iconClass" />
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
