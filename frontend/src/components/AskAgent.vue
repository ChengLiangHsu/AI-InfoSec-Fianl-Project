<script setup lang="ts">
import type { PromptInputMessage } from '@/components/ai-elements/prompt-input'
import type { ChatStatus, ToolUIPart } from 'ai'
import axios from 'axios'
import { Conversation, ConversationContent, ConversationScrollButton } from '@/components/ai-elements/conversation'
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
import {
  PromptInput,
  PromptInputActionAddAttachments,
  PromptInputActionMenu,
  PromptInputActionMenuContent,
  PromptInputActionMenuTrigger,
  PromptInputBody,
  PromptInputButton,
  PromptInputFooter,
  PromptInputHeader,
  PromptInputSpeechButton,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from '@/components/ai-elements/prompt-input'
import { Reasoning, ReasoningContent, ReasoningTrigger } from '@/components/ai-elements/reasoning'
import { Source, Sources, SourcesContent, SourcesTrigger } from '@/components/ai-elements/sources'
import { Suggestion, Suggestions } from '@/components/ai-elements/suggestion'
import { computed, ref } from 'vue'

interface MessageVersion {
  id: string
  content: string
}

interface MessageSource {
  href: string
  title: string
}

interface MessageReasoning {
  content: string
  duration: number
}

interface MessageTool {
  name: string
  description: string
  status: ToolUIPart['state']
  parameters: Record<string, unknown>
  result?: string
  error?: string
}

interface MessageType {
  key: string
  from: 'user' | 'assistant'
  sources?: MessageSource[]
  versions: MessageVersion[]
  reasoning?: MessageReasoning
  tools?: MessageTool[]
}

const apiInstance = axios.create({
  baseURL: 'http://127.0.0.1:8000',
})

const suggestions = [
  '無人機田間試驗應評估哪些指標？',
  '如何規劃無人機田間試驗的試驗區與對照組？',
  '如何評估飛行高度與速度對田間作業效果的影響？',
  '如何評估無人機噴灑的均勻度與覆蓋率？',
  '田間試驗應記錄哪些氣象與作物生長資料？',
  '如何比較無人機與傳統作業的效率及成本？',
  '如何分析田間試驗結果並提出改善建議？',
  '請協助整理無人機田間試驗的評估報告架構。',
]

const status = ref<ChatStatus>('ready')
const messages = ref<MessageType[]>([])
const requestError = ref('')
const isBusy = computed(() => status.value === 'submitted' || status.value === 'streaming')



function updateStreamingContent(versionId: string, content: string) {
  const target = messages.value.find(msg => msg.versions.some(version => version.id === versionId))
  if (!target)
    return
  const version = target.versions.find(v => v.id === versionId)
  if (!version)
    return
  version.content = content
  messages.value = [...messages.value]
}

async function streamResponse(versionId: string, content: string) {
  status.value = 'streaming'
  const words = content.split(' ')
  let currentContent = ''

  for (let i = 0; i < words.length; i += 1) {
    currentContent += (i > 0 ? ' ' : '') + words[i]
    updateStreamingContent(versionId, currentContent)
    await new Promise(resolve => setTimeout(resolve, Math.random() * 100 + 50))
  }

  status.value = 'ready'
}

function addUserMessage(content: string) {
  if (isBusy.value)
    return

  status.value = 'submitted'
  requestError.value = ''
  const timestamp = Date.now()
  const userMessage: MessageType = {
    key: `user-${timestamp}`,
    from: 'user',
    versions: [
      {
        id: `user-${timestamp}`,
        content,
      },
    ],
  }

  messages.value = [...messages.value, userMessage]

  setTimeout(async () => {
    const assistantVersionId = `assistant-${Date.now()}`
    const assistantMessage: MessageType = {
      key: `assistant-${Date.now()}`,
      from: 'assistant',
      versions: [
        {
          id: assistantVersionId,
          content: '',
        },
      ],
    }

    messages.value = [...messages.value, assistantMessage]
    try {
      const realResponse = await apiInstance.post("/agent/chat", {
        prompt: content,
      })
      await streamResponse(assistantVersionId, realResponse.data)
    }
    catch {
      status.value = 'error'
      requestError.value = '回覆失敗，請稍後再試。'
    }
  }, 500)
}

function handleSubmit(message: PromptInputMessage) {
  if (isBusy.value)
    return

  const text = message.text.trim()
  const hasText = text.length > 0
  const hasAttachments = message.files.length > 0

  if (!hasText && !hasAttachments)
    return

  addUserMessage(hasText ? text : 'Sent with attachments')
}

function handleSuggestionClick(suggestion: string) {
  addUserMessage(suggestion)
}

</script>

<template>
  <div class="relative flex size-full flex-col divide-y overflow-hidden">
    <Conversation>
      <ConversationContent>
        <MessageBranch
          v-for="message in messages"
          :key="message.key"
          :default-branch="0"
        >
          <MessageBranchContent>
            <Message
              v-for="version in message.versions"
              :key="`${message.key}-${version.id}`"
              :from="message.from"
            >
              <div>
                <Sources v-if="message.sources?.length">
                  <SourcesTrigger :count="message.sources.length" />
                  <SourcesContent>
                    <Source
                      v-for="source in message.sources"
                      :key="source.href"
                      :href="source.href"
                      :title="source.title"
                    />
                  </SourcesContent>
                </Sources>

                <Reasoning
                  v-if="message.reasoning"
                  :duration="message.reasoning.duration"
                >
                  <ReasoningTrigger />
                  <ReasoningContent :content="message.reasoning.content" />
                </Reasoning>

                <MessageContent>
                  <MessageResponse
                    :content="version.content"
                  />
                </MessageContent>
              </div>
            </Message>
          </MessageBranchContent>

          <MessageBranchSelector
            v-if="message.versions.length > 1"
            :from="message.from"
          >
            <MessageBranchPrevious />
            <MessageBranchPage />
            <MessageBranchNext />
          </MessageBranchSelector>
        </MessageBranch>
      </ConversationContent>
      <ConversationScrollButton />
    </Conversation>

    <div class="grid shrink-0 gap-4 pt-4">
      <Suggestions class="px-4">
        <Suggestion
          v-for="suggestion in suggestions"
          :key="suggestion"
          :suggestion="suggestion"
          :disabled="isBusy"
          @click="handleSuggestionClick"
        />
      </Suggestions>

      <div class="w-full px-4 pb-4">
        <p v-if="requestError" role="alert" class="mb-2 text-sm text-destructive">
          {{ requestError }}
        </p>
        <PromptInput
          class="w-full"
          :disabled="isBusy"
          multiple
          global-drop
          @submit="handleSubmit"
        >
          <PromptInputHeader>
            <PromptInputAttachmentsDisplay />
          </PromptInputHeader>

          <PromptInputBody>
            <PromptInputTextarea :disabled="isBusy" />
          </PromptInputBody>

          <PromptInputFooter class="flex-wrap">
            <PromptInputTools class="min-w-0 flex-wrap">
              <PromptInputActionMenu>
                <PromptInputActionMenuTrigger :disabled="isBusy" />
                <PromptInputActionMenuContent>
                  <PromptInputActionAddAttachments :disabled="isBusy" />
                </PromptInputActionMenuContent>
              </PromptInputActionMenu>

              <PromptInputSpeechButton :disabled="isBusy" />
            </PromptInputTools>

            <PromptInputSubmit
              :disabled="isBusy"
              :status="status"
            />
          </PromptInputFooter>
        </PromptInput>
      </div>
    </div>
  </div>
</template>
