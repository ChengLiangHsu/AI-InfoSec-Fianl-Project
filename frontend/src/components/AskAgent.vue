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
import { Conversation, ConversationContent, ConversationScrollButton } from '@/components/ai-elements/conversation'
import type { AttachmentData } from '@/components/ai-elements/attachments'

import { onMounted, watch } from 'vue'
import { Sparkles, Layers, Eye, BarChart2, CheckCircle2 } from '@lucide/vue'
import { useChatAgent } from '@/lib/useChatAgent'

const props = defineProps<{
  projectId?: string
  projectName?: string
  selectedFormula?: string
}>()

const { status, messages, loadInitialMessages, sendPrompt } = useChatAgent(() => props.projectId)

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
  await sendPrompt(payload.text, props.projectId)
}

async function triggerQuickPrompt(promptText: string): Promise<void> {
  if (status.value === 'streaming') return
  await sendPrompt(promptText, props.projectId)
}
</script>

<template>
  <div class="relative flex size-full flex-col divide-y overflow-hidden">
    <!-- 正射圖與光譜圖存取狀態列 -->
    <div class="flex items-center justify-between bg-muted/30 px-3.5 py-2 text-xs border-b">
      <div class="flex items-center gap-1.5 font-medium text-muted-foreground truncate">
        <span class="size-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
        <span class="truncate">已連結正射影像</span>
        <span class="text-muted-foreground/60">·</span>
        <span class="flex items-center gap-1 rounded bg-background px-1.5 py-0.5 font-mono text-[11px] font-semibold text-foreground border shadow-2xs">
          <Layers class="size-3 text-primary" />
          {{ (selectedFormula || 'rgb').toUpperCase() }}
        </span>
      </div>
      <span class="text-[11px] text-emerald-600 font-medium shrink-0 flex items-center gap-1">
        <CheckCircle2 class="size-3" />
        多模態就緒
      </span>
    </div>

    <!-- 對話內容區 -->
    <Conversation>
      <ConversationContent>
        <MessageBranch v-for="message in messages" :key="message.key" :default-branch="0">
          <MessageBranchContent>
            <Message v-for="version in message.versions" :key="`${message.key}-${version.id}`" :from="message.role">
              <MessageContent>
                <MessageResponse :content="version.content" />
              </MessageContent>
            </Message>
          </MessageBranchContent>
          <MessageBranchSelector v-if="message.versions.length > 1" :from="message.role">
            <MessageBranchPrevious />
            <MessageBranchPage />
            <MessageBranchNext />
          </MessageBranchSelector>
        </MessageBranch>
      </ConversationContent>
      <ConversationScrollButton />
    </Conversation>

    <!-- 輸入區與快捷分析行動標籤 -->
    <div class="w-full px-3.5 pb-3.5 pt-2 space-y-2 bg-background">
      <!-- 快捷分析動作標籤 -->
      <div class="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs no-scrollbar">
        <button
          type="button"
          :disabled="status === 'streaming'"
          class="inline-flex shrink-0 items-center gap-1 rounded-full border border-border/80 bg-muted/40 px-2.5 py-1 text-[11px] font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50 cursor-pointer shadow-2xs"
          @click="triggerQuickPrompt(`請使用視覺判讀工具觀察目前專案的 ${(selectedFormula || 'VARI').toUpperCase()} 光譜圖，分析作物植株排列與是否有缺株、變色或生長異常。`)"
        >
          <Eye class="size-3 text-primary" />
          <span>視覺診斷光譜</span>
        </button>
        <button
          type="button"
          :disabled="status === 'streaming'"
          class="inline-flex shrink-0 items-center gap-1 rounded-full border border-border/80 bg-muted/40 px-2.5 py-1 text-[11px] font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50 cursor-pointer shadow-2xs"
          @click="triggerQuickPrompt(`請計算當前專案的 ${(selectedFormula || 'VARI').toUpperCase()} 植生指標統計數據（包含平均值、標準差與健康植生比例），並評估田區均勻度。`)"
        >
          <BarChart2 class="size-3 text-emerald-500" />
          <span>光譜數值統計</span>
        </button>
        <button
          type="button"
          :disabled="status === 'streaming'"
          class="inline-flex shrink-0 items-center gap-1 rounded-full border border-border/80 bg-muted/40 px-2.5 py-1 text-[11px] font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50 cursor-pointer shadow-2xs"
          @click="triggerQuickPrompt('請讀取當前專案的高解析度原始正射圖 (RGB)，詳細檢查田區全貌與作物生長覆蓋狀況。')"
        >
          <Sparkles class="size-3 text-amber-500" />
          <span>正射全景檢查</span>
        </button>
      </div>

      <PromptInputProvider @submit="onSubmit">
        <PromptInput multiple global-drop class="w-full">
          <PromptInputBody>
            <PromptInputTextarea :placeholder="`詢問田間試驗、${(selectedFormula || 'VARI').toUpperCase()} 光譜或正射圖分析...`" />
          </PromptInputBody>
          <PromptInputFooter>
            <PromptInputSubmit :disabled="status === 'streaming'" :status="status" />
          </PromptInputFooter>
        </PromptInput>
      </PromptInputProvider>
    </div>
  </div>
</template>
<style></style>