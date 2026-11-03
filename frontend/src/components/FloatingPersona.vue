<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useDraggable, useWindowSize } from '@vueuse/core'
import Persona, { type PersonaState } from '@/components/ai-elements/persona/Persona.vue'
import AskAgent from './AskAgent.vue'
import { useChatAgent } from '@/lib/useChatAgent'
import { Sparkles, X, Bot } from '@lucide/vue'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

const props = defineProps<{
  projectId?: string
  projectName?: string
  selectedFormula?: string
}>()

const { width: windowWidth, height: windowHeight } = useWindowSize()
const { status, messages, clearChat } = useChatAgent(() => props.projectId)

const personaContainer = ref<HTMLElement | null>(null)
const isDialogOpen = ref(false)
const showBubble = ref(false)

// 初始位置設定在畫面右下角
const initialX = Math.max(16, (typeof window !== 'undefined' ? window.innerWidth : 1200) - 96)
const initialY = Math.max(16, (typeof window !== 'undefined' ? window.innerHeight : 800) - 96)

const { x, y, isDragging } = useDraggable(personaContainer, {
  initialValue: { x: initialX, y: initialY },
  preventDefault: true,
})

// 確保組件永不超出視窗可視邊界 (16px padding, 64px 尺寸)
const clampedX = computed(() => {
  const maxX = Math.max(16, windowWidth.value - 80)
  return Math.min(Math.max(16, x.value), maxX)
})

const clampedY = computed(() => {
  const maxY = Math.max(16, windowHeight.value - 80)
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

// 自適應碰撞避障定位演算法：根據 Persona 四象限座標動態決定展開方向
const dialogStyle = computed(() => {
  const px = clampedX.value
  const py = clampedY.value
  const ww = windowWidth.value
  const wh = windowHeight.value

  const dialogW = Math.min(420, ww - 32)
  const dialogH = Math.min(600, wh - 32)

  let posX: number
  // 水平判定：若 Persona 在右半側，彈窗優先向左展開；反之向右展開
  if (px > ww / 2) {
    posX = px - dialogW - 12
    if (posX < 16) {
      posX = Math.max(16, Math.min(ww - dialogW - 16, px - dialogW / 2))
    }
  } else {
    posX = px + 64 + 12
    if (posX + dialogW > ww - 16) {
      posX = Math.max(16, ww - dialogW - 16)
    }
  }

  let posY: number
  // 垂直判定：若 Persona 在下半側，彈窗優先對齊底部向上延伸
  if (py > wh / 2) {
    posY = py + 64 - dialogH
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

// 迷你文字氣泡自適應定位
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
    posX = px + 64 + 12
  }
  posX = Math.max(16, Math.min(ww - bubbleW - 16, posX))

  let posY = py + 32 - 40
  posY = Math.max(16, Math.min(wh - 140, posY))

  return {
    left: `${posX}px`,
    top: `${posY}px`,
    maxWidth: `${bubbleW}px`,
  }
})

onMounted(() => {
  // 確保初始位置在視窗範圍內
  if (typeof window !== 'undefined') {
    x.value = Math.max(16, window.innerWidth - 96)
    y.value = Math.max(16, window.innerHeight - 96)
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
    class="fixed z-50 select-none touch-none cursor-grab active:cursor-grabbing transition-transform duration-150"
    :class="[
      isDragging ? 'scale-105 opacity-95' : 'hover:scale-105',
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
      class="relative flex size-16 items-center justify-center rounded-full border border-primary/25 bg-background/85 shadow-2xl backdrop-blur-xl transition-all duration-300 hover:border-primary/50 hover:shadow-primary/20 ring-1 ring-primary/20 overflow-hidden"
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
      v-if="showBubble && !isDialogOpen && latestAssistantMessage.trim().length > 0"
      class="fixed z-40 flex flex-col gap-1.5 rounded-2xl border border-border/80 bg-background/90 p-3 shadow-2xl backdrop-blur-xl text-foreground cursor-pointer hover:border-primary/50 transition-colors group"
      :style="bubbleStyle"
      @click="openDialog"
    >
      <div class="flex items-center justify-between gap-2 border-b border-border/50 pb-1.5 text-xs text-muted-foreground">
        <div class="flex items-center gap-1.5 font-medium text-foreground">
          <Bot class="size-3.5 text-primary" />
          <span class="text-[11px] font-semibold">AI 試驗診斷</span>
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
          <X class="size-3.5" />
        </button>
      </div>

      <p class="text-xs text-foreground/90 leading-relaxed line-clamp-3 select-none">
        {{ latestAssistantMessage }}
      </p>

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
            AskAgent ({{ projectName || '專案分析' }})
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
        />
      </div>
    </section>
  </Transition>
</template>
