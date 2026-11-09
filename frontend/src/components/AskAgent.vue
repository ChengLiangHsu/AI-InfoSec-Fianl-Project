<script setup lang="ts">
import { ref } from 'vue'
import type { PromptInputMessage } from '@/components/ai-elements/prompt-input'
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputProvider,
  PromptInputSubmit,
  PromptInputTextarea,
} from '@/components/ai-elements/prompt-input'
import {
  Message,
  MessageBranch,
  MessageBranchContent,
  MessageBranchNext,
  MessageBranchPage,
  MessageBranchPrevious,
  MessageBranchSelector,
  MessageContent,
  MessageResponse,
} from '@/components/ai-elements/message'
import StepBadgeText from '@/components/StepBadgeText.vue'
import { Conversation, ConversationContent, ConversationScrollButton } from '@/components/ai-elements/conversation'
import type { AttachmentData } from '@/components/ai-elements/attachments'

import { onMounted, watch, computed } from 'vue'
import { Eye, BarChart2, Sparkles, HelpCircle, FileText, Bug, Sprout, ShieldAlert, Loader2 } from '@lucide/vue'
import { useChatAgent } from '@/lib/useChatAgent'

const props = withDefaults(
  defineProps<{
    projectId?: string
    projectName?: string
    selectedFormula?: string
    isHome?: boolean
    hasPlots?: boolean
  }>(),
  {
    isHome: false,
    hasPlots: false,
  }
)

const { status, messages, loadInitialMessages, sendPrompt } = useChatAgent(() => props.projectId)

const isBusy = computed(() => status.value === 'submitted' || status.value === 'streaming')

const isThinking = computed(() => {
  if (!isBusy.value) return false
  const lastMsg = messages.value[messages.value.length - 1]
  return !lastMsg || lastMsg.role === 'user'
})

onMounted(() => {
  loadInitialMessages(props.projectId)
})

watch(
  () => props.projectId,
  (newId) => {
    if (newId) {
      loadInitialMessages(newId)
    }
  }
)

async function onSubmit(payload: PromptInputMessage): Promise<void> {
  if (isBusy.value) return
  await sendPrompt(payload.text, props.projectId)
}

async function triggerQuickPrompt(promptText: string): Promise<void> {
  if (isBusy.value) return
  await sendPrompt(promptText, props.projectId)
}

const placeholderText = computed(() => {
  if (isBusy.value) {
    return 'AI 正在思考與分析中，請稍候...'
  }
  if (props.isHome) {
    return '跟田間助理聊聊系統功能、相片拼接或植生指標...'
  }
  return `詢問田間試驗、${(props.selectedFormula || 'VARI').toUpperCase()} 光譜或小區狀況...`
})
</script>

<template>
  <div class="relative flex size-full flex-col divide-y overflow-hidden">
    <!-- 對話內容區 -->
    <Conversation>
      <ConversationContent>
        <div v-if="messages.length === 0" class="flex h-full min-h-[160px] flex-col items-center justify-center p-4 text-center text-muted-foreground my-auto select-none">
          <p class="text-xs text-muted-foreground/75">
            {{ isHome ? '點選下方快捷功能或輸入問題，讓田間助理為你介紹～' : '點選下方快捷分析標籤或輸入試驗情境開始討論' }}
          </p>
        </div>
        <MessageBranch v-for="message in messages" :key="message.key" :default-branch="0">
          <MessageBranchContent>
            <Message v-for="version in message.versions" :key="`${message.key}-${version.id}`" :from="message.role">
              <MessageContent>
                <StepBadgeText :text="version.content" />
              </MessageContent>
            </Message>
          </MessageBranchContent>
          <MessageBranchSelector v-if="message.versions.length > 1" :from="message.role">
            <MessageBranchPrevious />
            <MessageBranchPage />
            <MessageBranchNext />
          </MessageBranchSelector>
        </MessageBranch>

        <!-- 當 AI 正在思考中且尚未回傳內容時顯示載入指示器 -->
        <div
          v-if="isThinking"
          class="flex items-center gap-2 rounded-lg border border-border/50 bg-muted/40 px-3 py-2 text-xs text-muted-foreground w-fit animate-pulse my-2"
        >
          <Loader2 class="size-3.5 animate-spin text-primary" />
          <span>田間助理正在思考與分析中...</span>
        </div>
      </ConversationContent>
      <ConversationScrollButton />
    </Conversation>

    <!-- 輸入區與快捷分析行動標籤 -->
    <div class="w-full px-3.5 pb-3.5 pt-2 space-y-2 bg-background">
      <!-- 快捷分析動作標籤 -->
      <div class="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs no-scrollbar">
        <!-- 首頁專屬引導標籤 -->
        <template v-if="isHome">
          <button
            type="button"
            :disabled="isBusy"
            class="inline-flex shrink-0 items-center gap-1 rounded-full border border-border/80 bg-muted/40 px-2.5 py-1 text-[11px] font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none cursor-pointer shadow-2xs"
            @click="triggerQuickPrompt('系統功能介紹')"
          >
            <HelpCircle class="size-3 text-primary" />
            <span>系統功能介紹</span>
          </button>
          <button
            type="button"
            :disabled="isBusy"
            class="inline-flex shrink-0 items-center gap-1 rounded-full border border-border/80 bg-muted/40 px-2.5 py-1 text-[11px] font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none cursor-pointer shadow-2xs"
            @click="triggerQuickPrompt('空拍拍攝建議')"
          >
            <FileText class="size-3 text-sky-500" />
            <span>空拍拍攝建議</span>
          </button>
          <button
            type="button"
            :disabled="isBusy"
            class="inline-flex shrink-0 items-center gap-1 rounded-full border border-border/80 bg-muted/40 px-2.5 py-1 text-[11px] font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none cursor-pointer shadow-2xs"
            @click="triggerQuickPrompt('支援植生指標')"
          >
            <Sparkles class="size-3 text-amber-500" />
            <span>支援植生指標</span>
          </button>
        </template>

        <!-- 專案情境標籤 (未劃分小區前優先顯示情境選擇) -->
        <template v-else-if="!hasPlots">
          <button
            type="button"
            :disabled="isBusy"
            class="inline-flex shrink-0 items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-foreground transition-colors hover:bg-primary/20 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none cursor-pointer shadow-2xs"
            @click="triggerQuickPrompt('殺蟲劑藥效評估')"
          >
            <Bug class="size-3 text-primary" />
            <span>殺蟲劑藥效評估</span>
          </button>
          <button
            type="button"
            :disabled="isBusy"
            class="inline-flex shrink-0 items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-foreground transition-colors hover:bg-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none cursor-pointer shadow-2xs"
            @click="triggerQuickPrompt('除草劑防除試驗')"
          >
            <ShieldAlert class="size-3 text-emerald-500" />
            <span>除草劑防除試驗</span>
          </button>
          <button
            type="button"
            :disabled="isBusy"
            class="inline-flex shrink-0 items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-[11px] font-medium text-foreground transition-colors hover:bg-amber-500/20 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none cursor-pointer shadow-2xs"
            @click="triggerQuickPrompt('長勢與缺株監測')"
          >
            <Sprout class="size-3 text-amber-500" />
            <span>長勢與缺株監測</span>
          </button>
        </template>

        <!-- 專案通用光譜診斷動作 -->
        <template v-if="!isHome">
          <button
            type="button"
            :disabled="isBusy"
            class="inline-flex shrink-0 items-center gap-1 rounded-full border border-border/80 bg-muted/40 px-2.5 py-1 text-[11px] font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none cursor-pointer shadow-2xs"
            @click="triggerQuickPrompt('視覺診斷光譜')"
          >
            <Eye class="size-3 text-primary" />
            <span>視覺診斷光譜</span>
          </button>
          <button
            type="button"
            :disabled="isBusy"
            class="inline-flex shrink-0 items-center gap-1 rounded-full border border-border/80 bg-muted/40 px-2.5 py-1 text-[11px] font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none cursor-pointer shadow-2xs"
            @click="triggerQuickPrompt('光譜數值統計')"
          >
            <BarChart2 class="size-3 text-emerald-500" />
            <span>光譜數值統計</span>
          </button>
          <button
            type="button"
            :disabled="isBusy"
            class="inline-flex shrink-0 items-center gap-1 rounded-full border border-border/80 bg-muted/40 px-2.5 py-1 text-[11px] font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none cursor-pointer shadow-2xs"
            @click="triggerQuickPrompt('正射全景檢查')"
          >
            <Sparkles class="size-3 text-amber-500" />
            <span>正射全景檢查</span>
          </button>
        </template>
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
</template>
<style></style>
