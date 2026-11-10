<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useDraggable, useWindowSize, useIntervalFn } from '@vueuse/core'
import Persona, { type PersonaState } from '@/components/ai-elements/persona/Persona.vue'
import AskAgent from './AskAgent.vue'
import StepBadgeText from '@/components/StepBadgeText.vue'
import { useChatAgent } from '@/lib/useChatAgent'
import { Sparkles, X, Bot } from '@lucide/vue'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

const props = withDefaults(
  defineProps<{
    projectId?: string
    projectName?: string
    selectedFormula?: string
    projectProgress?: number
    hasPlots?: boolean
    isHome?: boolean
    currentStep?: 1 | 2 | 3
  }>(),
  {
    isHome: false,
    hasPlots: false,
    currentStep: 1,
  }
)

const { width: windowWidth, height: windowHeight } = useWindowSize()
const { status, messages, sendPrompt, injectAssistantMessage } = useChatAgent(() => props.projectId)

const personaContainer = ref<HTMLElement | null>(null)
const isDialogOpen = ref(false)
const showBubble = ref(false)

// 初始位置設定在畫面右下角
const initialX = Math.max(16, (typeof window !== 'undefined' ? window.innerWidth : 1200) - 72)
const initialY = Math.max(16, (typeof window !== 'undefined' ? window.innerHeight : 800) - 72)

const { x, y, isDragging } = useDraggable(personaContainer, {
  initialValue: { x: initialX, y: initialY },
  preventDefault: true,
})

// 確保組件永不超出視窗可視邊界 (16px padding, 48px 尺寸)
const clampedX = computed(() => {
  const maxX = Math.max(16, windowWidth.value - 64)
  return Math.min(Math.max(16, x.value), maxX)
})

const clampedY = computed(() => {
  const maxY = Math.max(16, windowHeight.value - 64)
  return Math.min(Math.max(16, y.value), maxY)
})

// 手勢位移閥值判定：超過 5px 視為拖曳，小於等於 5px 視為單擊點擊
let pointerStartX = 0
let pointerStartY = 0
let hasMoved = false

function onPointerDown(e: PointerEvent) {
  pointerStartX = e.clientX
  pointerStartY = e.clientY
  hasMoved = false
}

function onPointerMove(e: PointerEvent) {
  if (Math.hypot(e.clientX - pointerStartX, e.clientY - pointerStartY) > 5) {
    hasMoved = true
  }
}

function onPointerUp() {
  if (!hasMoved) {
    toggleDialog()
  }
}

function toggleDialog() {
  isDialogOpen.value = !isDialogOpen.value
}

function openDialog() {
  isDialogOpen.value = true
  showBubble.value = false
}

function closeDialog() {
  isDialogOpen.value = false
}

// Persona 動畫狀態與後端 Agent 狀態連動
const personaState = computed<PersonaState>(() => {
  if (status.value === 'submitted') return 'thinking'
  if (status.value === 'streaming') return 'speaking'
  return 'idle'
})

// 最新助理回覆文字（用於迷你氣泡）
const latestAssistantMessage = computed(() => {
  const assistantMsgs = messages.value.filter((m) => m.role === 'assistant')
  if (assistantMsgs.length === 0) return ''
  const last = assistantMsgs[assistantMsgs.length - 1]
  return last.versions?.[0]?.content || last.content || ''
})

// 五大工作流狀態機判定
type WorkflowState = 'HOME_INTRO' | 'STITCHING' | 'ASK_SCENARIO' | 'GUIDE_PLOTS' | 'ANALYZE_RESULTS'

const currentWorkflowState = computed<WorkflowState>(() => {
  if (props.isHome || !props.projectId) return 'HOME_INTRO'
  if (typeof props.projectProgress === 'number' && props.projectProgress < 100) return 'STITCHING'
  if (props.projectProgress === 100) {
    const assistantCount = messages.value.filter((m) => m.role === 'assistant').length
    if (assistantCount === 0) return 'ASK_SCENARIO'
    if (!props.hasPlots) return 'GUIDE_PLOTS'
    return 'ANALYZE_RESULTS'
  }
  return 'HOME_INTRO'
})

interface ScenarioChip {
  label: string
  icon?: string
  prompt: string
}

const scenarioChips: ScenarioChip[] = [
  {
    label: '殺蟲劑藥效評估',
    icon: '🐛',
    prompt: '殺蟲劑藥效評估',
  },
  {
    label: '除草劑防除試驗',
    icon: '🌿',
    prompt: '除草劑防除試驗',
  },
  {
    label: '長勢與缺株監測',
    icon: '🌱',
    prompt: '長勢與缺株監測',
  },
]

// 紀錄已主動問候過的專案，避免重複打擾
const promptedProjects = ref<Record<string, boolean>>({})

async function handleSelectScenario(chip: ScenarioChip) {
  openDialog()
  await sendPrompt(chip.prompt, props.projectId || 'home')
}

// 生命週期狀態感知與主動問候觸發
watch(
  () => [currentWorkflowState.value, props.projectId, props.projectProgress, messages.value.length] as const,
  ([state, pid, progress, msgCount]) => {
    const key = (pid as string) || 'home'

    if (state === 'HOME_INTRO') {
      if (messages.value.length === 0) {
        injectAssistantMessage(
          '嗨！歡迎來到田間試驗評估系統～直接把空拍照片拖進來，就可以開始步驟 1：航拍上傳囉！',
          'home'
        )
      }
      if (!isDialogOpen.value) {
        showBubble.value = true
      }
    } else if (state === 'STITCHING') {
      if (!promptedProjects.value[`${key}_stitching`] && msgCount === 0) {
        promptedProjects.value[`${key}_stitching`] = true
        injectAssistantMessage(
          '正在為您進行正射影像拼接！趁等待時間，先在上方卡片設定這次的試驗情境（如農藥或劑量）吧～',
          key
        )
        if (!isDialogOpen.value) {
          showBubble.value = true
        }
      }
    } else if (state === 'ASK_SCENARIO') {
      if (!promptedProjects.value[key] && msgCount === 0) {
        promptedProjects.value[key] = true
        injectAssistantMessage(
          '太棒了，正射圖拼好囉！這次田裡是做什麼試驗呀？殺蟲還是除草呢？點選下方標籤告訴我吧！',
          key
        )
        if (!isDialogOpen.value) {
          showBubble.value = true
        }
      }
    }
  },
  { immediate: true }
)

// 當 Agent 開始串流輸出或完成時，若視窗未開則自動展示文字氣泡
watch(
  () => status.value,
  (newStatus, oldStatus) => {
    if (newStatus === 'streaming' || (oldStatus === 'streaming' && newStatus === 'ready')) {
      if (!isDialogOpen.value && latestAssistantMessage.value.trim().length > 0) {
        showBubble.value = true
      }
    }
  }
)

// 開啟完整對話視窗時自動隱藏迷你氣泡
watch(
  () => isDialogOpen.value,
  (open) => {
    if (open) {
      showBubble.value = false
    }
  }
)

// 當步驟切換時的主動引導問候
watch(
  () => props.currentStep,
  (newStep) => {
    if (props.isHome || !props.projectId) return
    const key = `${props.projectId}_step_${newStep}`
    if (newStep === 2) {
      if (!promptedProjects.value[key]) {
        promptedProjects.value[key] = true
        injectAssistantMessage(
          '歡迎來到步驟 2：試驗情境設定！請在左側卡片確認或調整農藥名稱、稀釋倍數與對照組。若需要試驗規劃建議，隨時點我提問喔！',
          props.projectId
        )
        if (!isDialogOpen.value) {
          showBubble.value = true
        }
      }
    } else if (newStep === 3) {
      if (!promptedProjects.value[key]) {
        promptedProjects.value[key] = true
        injectAssistantMessage(
          '太棒了！已進入步驟 3：小區繪製！您可以使用上方工具列自動偵測白色定位牌、批次生成小區網格，或手動繪製多邊形小區！',
          props.projectId
        )
        if (!isDialogOpen.value) {
          showBubble.value = true
        }
      }
    }
  }
)

// 動態吸附目標候選與指引文字
interface DockCandidate {
  selector: string
  hint: string
}

const currentTargetInfo = ref<{ selector: string; hint: string } | null>(null)

function getDockCandidates(): DockCandidate[] {
  if (props.isHome || !props.projectId) {
    return [
      { selector: '[data-tour="cancel-upload"]', hint: '相片傳輸中，可隨時點此取消' },
      { selector: '[data-tour="start-stitching"]', hint: '點擊此處開始正射拼接！' },
      { selector: '[data-tour="upload-dropzone"]', hint: '把空拍照片拖進來開始～' },
    ]
  }

  // 步驟 1：航拍與正射結果檢視
  if (props.currentStep === 1) {
    if (typeof props.projectProgress === 'number' && props.projectProgress < 100) {
      return [
        { selector: '[data-tour="cancel-stitching"]', hint: '正在拼接中，可隨時中斷' },
        { selector: '[data-tour="step-tab-2"]', hint: '正射拼圖運算中，可先點此前往步驟 2 設定情境' },
      ]
    }
    return [
      { selector: '[data-tour="step-tab-2"]', hint: '正射影像拼接已完成！點此前往步驟 2 設定情境' },
    ]
  }

  // 步驟 2：試驗情境設定與討論
  if (props.currentStep === 2) {
    return [
      { selector: '[data-tour="save-scenario"]', hint: '情境設定完成後，請點此儲存' },
      { selector: '[data-tour="step-tab-3"]', hint: '情境設定完畢後，點此進入步驟 3 小區繪製' },
    ]
  }

  // 步驟 3：小區繪製與標註
  if (props.currentStep === 3) {
    if (!props.hasPlots) {
      return [
        { selector: '[data-tour="grid-mode"]', hint: '點選網格生成或標記辨識，快速標註小區' },
      ]
    }
    return [
      { selector: '[data-tour="save-plots"]', hint: '小區繪製或編輯完成後，請記得儲存' },
      { selector: '[data-tour="formula-selector"]', hint: '試驗小區已就緒，可切換植生指標檢視' },
    ]
  }

  return []
}

function updateDockPosition() {
  if (isDragging.value) return

  const candidates = getDockCandidates()
  let matchedEl: HTMLElement | null = null
  let matchedCandidate: DockCandidate | null = null

  for (const c of candidates) {
    const el = document.querySelector<HTMLElement>(c.selector)
    if (el) {
      const rect = el.getBoundingClientRect()
      if (rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.top < windowHeight.value) {
        matchedEl = el
        matchedCandidate = c
        break
      }
    }
  }

  currentTargetInfo.value = matchedCandidate

  if (!matchedEl) {
    x.value = Math.max(16, windowWidth.value - 64)
    y.value = Math.max(16, windowHeight.value - 64)
    return
  }

  const rect = matchedEl.getBoundingClientRect()
  const orbSize = 48
  const margin = 12

  // 優先在目標元素右側垂直居中
  let targetX = rect.right + margin
  let targetY = rect.top + (rect.height - orbSize) / 2

  // 若右側超出螢幕邊界，則停靠在目標左側
  if (targetX + orbSize > windowWidth.value - 16) {
    targetX = rect.left - orbSize - margin
  }

  targetX = Math.max(16, Math.min(windowWidth.value - orbSize - 16, targetX))
  targetY = Math.max(16, Math.min(windowHeight.value - orbSize - 16, targetY))

  x.value = Math.round(targetX)
  y.value = Math.round(targetY)
}

// 監聽工作流狀態與屬性變化即時重新對齊
watch(
  () => [props.isHome, props.projectId, props.projectProgress, props.hasPlots] as const,
  () => {
    updateDockPosition()
  }
)

useIntervalFn(updateDockPosition, 600, { immediate: true })

// 自適應碰撞避障定位演算法：根據 Persona 四象限座標動態決定展開方向 (48px 尺寸)
const dialogStyle = computed(() => {
  const px = clampedX.value
  const py = clampedY.value
  const ww = windowWidth.value
  const wh = windowHeight.value

  const dialogW = Math.min(420, ww - 32)
  const dialogH = Math.min(600, wh - 32)

  let posX: number
  if (px > ww / 2) {
    posX = px - dialogW - 12
    if (posX < 16) {
      posX = Math.max(16, Math.min(ww - dialogW - 16, px - dialogW / 2))
    }
  } else {
    posX = px + 48 + 12
    if (posX + dialogW > ww - 16) {
      posX = Math.max(16, ww - dialogW - 16)
    }
  }

  let posY: number
  if (py > wh / 2) {
    posY = py + 48 - dialogH
    if (posY < 16) posY = 16
  } else {
    posY = py
    if (posY + dialogH > wh - 16) {
      posY = Math.max(16, wh - dialogH - 16)
    }
  }

  return {
    left: `${posX}px`,
    top: `${posY}px`,
    width: `${dialogW}px`,
    height: `${dialogH}px`,
  }
})

// 迷你文字氣泡自適應定位 (48px 尺寸)
const bubbleStyle = computed(() => {
  const px = clampedX.value
  const py = clampedY.value
  const ww = windowWidth.value
  const wh = windowHeight.value
  const bubbleW = 280

  let posX: number
  if (px > ww / 2) {
    posX = px - bubbleW - 12
  } else {
    posX = px + 48 + 12
  }
  posX = Math.max(16, Math.min(ww - bubbleW - 16, posX))

  let posY = py + 24 - 40
  posY = Math.max(16, Math.min(wh - 140, posY))

  return {
    left: `${posX}px`,
    top: `${posY}px`,
    maxWidth: `${bubbleW}px`,
  }
})

onMounted(() => {
  if (typeof window !== 'undefined') {
    window.addEventListener('scroll', updateDockPosition, true)
    window.addEventListener('resize', updateDockPosition)
    updateDockPosition()
  }
})

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('scroll', updateDockPosition, true)
    window.removeEventListener('resize', updateDockPosition)
  }
})
</script>

<template>
  <!-- 1. 懸浮 Persona 球體本體 -->
  <div
    ref="personaContainer"
    role="button"
    tabindex="0"
    aria-label="AI Agent Persona 懸浮助手"
    :aria-expanded="isDialogOpen"
    class="fixed z-50 select-none touch-none cursor-grab active:cursor-grabbing"
    :class="[
      isDragging ? 'scale-105 opacity-95' : 'hover:scale-105 transition-[left,top,transform] duration-300 ease-out',
    ]"
    :style="{
      left: `${clampedX}px`,
      top: `${clampedY}px`,
    }"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @keydown.enter.prevent="toggleDialog"
    @keydown.space.prevent="toggleDialog"
  >
    <div
      class="relative flex size-12 items-center justify-center rounded-full border-2 border-zinc-900 bg-zinc-950 shadow-2xl backdrop-blur-xl transition-all duration-300 hover:border-black hover:shadow-black/60 ring-2 ring-zinc-800/80 overflow-hidden"
    >
      <!-- Rive Persona Obsidian 動態圖示 -->
      <Persona
        variant="obsidian"
        :state="personaState"
        class="size-full pointer-events-none scale-110"
      />
    </div>
  </div>

  <!-- 2. 最新回覆迷你文字氣泡 (身旁串流顯示) -->
  <Transition
    enter-active-class="transition-all duration-200 ease-out"
    enter-from-class="opacity-0 translate-y-2 scale-95"
    enter-to-class="opacity-100 translate-y-0 scale-100"
    leave-active-class="transition-all duration-150 ease-in"
    leave-from-class="opacity-100 translate-y-0 scale-100"
    leave-to-class="opacity-0 translate-y-2 scale-95"
  >
    <div
      v-if="showBubble && !isDialogOpen && (latestAssistantMessage.trim().length > 0 || !!currentTargetInfo?.hint)"
      class="fixed z-40 flex flex-col gap-1.5 rounded-2xl border border-border/80 bg-background/90 p-3 shadow-2xl backdrop-blur-xl text-foreground cursor-pointer hover:border-primary/50 transition-colors group"
      :style="bubbleStyle"
      @click="openDialog"
    >
      <div class="flex items-center justify-between gap-2 border-b border-border/50 pb-1.5 text-xs text-muted-foreground">
        <div class="flex items-center gap-1.5 font-medium text-foreground">
          <Bot class="size-4 text-primary" />
          <span class="text-xs font-semibold">
            {{ isHome ? '田間試驗好夥伴' : 'AI 試驗診斷' }}
          </span>
          <span
            v-if="status === 'streaming'"
            class="size-1.5 rounded-full bg-emerald-500 animate-pulse"
          />
        </div>
        <button
          type="button"
          aria-label="關閉氣泡"
          class="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
          @click.stop="showBubble = false"
        >
          <X class="size-4" />
        </button>
      </div>

      <!-- 當前下一步動作微型導引標籤 -->
      <div
        v-if="currentTargetInfo?.hint"
        class="inline-flex items-center gap-1.5 self-start rounded-md bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary"
      >
        <Sparkles class="size-3" />
        <span>{{ currentTargetInfo.hint }}</span>
      </div>

      <div v-if="latestAssistantMessage.trim().length > 0" class="text-sm text-foreground/90 leading-relaxed line-clamp-3 select-none">
        <StepBadgeText :text="latestAssistantMessage" />
      </div>

      <!-- 快捷情境按鈕列 (正射運算中、剛完成或小區未劃定前) -->
      <div
        v-if="currentWorkflowState === 'STITCHING' || currentWorkflowState === 'ASK_SCENARIO' || (props.projectId && !hasPlots)"
        class="flex flex-wrap gap-1 pt-1"
        @click.stop
      >
        <button
          v-for="chip in scenarioChips"
          :key="chip.label"
          type="button"
          class="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-foreground hover:bg-primary/20 transition-colors cursor-pointer"
          @click="handleSelectScenario(chip)"
        >
          <span>{{ chip.icon }}</span>
          <span>{{ chip.label }}</span>
        </button>
      </div>

      <div class="flex items-center justify-between pt-1 text-[10px] text-muted-foreground/75 font-medium">
        <span>點擊展開完整對話</span>
        <span class="text-primary group-hover:translate-x-0.5 transition-transform">↗</span>
      </div>
    </div>
  </Transition>

  <!-- 3. 自適應錨定完整對話視窗 (AskAgent) -->
  <Transition
    enter-active-class="transition-all duration-200 ease-out"
    enter-from-class="opacity-0 scale-95"
    enter-to-class="opacity-100 scale-100"
    leave-active-class="transition-all duration-150 ease-in"
    leave-from-class="opacity-100 scale-100"
    leave-to-class="opacity-0 scale-95"
  >
    <section
      v-if="isDialogOpen"
      id="ask-agent-window"
      aria-labelledby="ask-agent-title"
      class="fixed z-50 flex flex-col overflow-hidden rounded-2xl border border-border/80 bg-background/95 text-foreground shadow-2xl backdrop-blur-2xl"
      :style="dialogStyle"
    >
      <!-- 視窗頂部標題列 -->
      <header class="flex shrink-0 items-center justify-between border-b px-3.5 py-2.5 bg-muted/25">
        <div class="flex items-center gap-2 min-w-0">
          <Sparkles class="size-4 text-primary shrink-0" />
          <h2 id="ask-agent-title" class="font-semibold text-sm truncate">
            AskAgent ({{ isHome ? '首頁助理' : (projectName || '專案分析') }})
          </h2>
        </div>
        <div class="flex items-center gap-1 shrink-0">
          <TooltipProvider :delay-duration="150">
            <Tooltip>
              <TooltipTrigger as-child>
                <button
                  type="button"
                  aria-label="關閉 AskAgent"
                  class="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring cursor-pointer transition-colors"
                  @click="closeDialog"
                >
                  <X class="size-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom" class="text-xs">
                關閉視窗
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </header>

      <!-- 嵌入既有 AskAgent 核心視圖 -->
      <div class="flex-1 min-h-0 overflow-hidden">
        <AskAgent
          :project-id="projectId"
          :project-name="projectName"
          :selected-formula="selectedFormula"
          :is-home="isHome"
          :has-plots="hasPlots"
        />
      </div>
    </section>
  </Transition>
</template>
