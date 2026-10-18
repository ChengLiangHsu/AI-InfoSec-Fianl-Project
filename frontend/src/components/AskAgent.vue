<script setup lang="ts">
import { ref } from 'vue'
import type { PromptInputMessage } from '@/components/ai-elements/prompt-input'
<<<<<<< HEAD
import type { ChatStatus, ToolUIPart } from 'ai'
import axios from 'axios'
import { Conversation, ConversationContent, ConversationScrollButton } from '@/components/ai-elements/conversation'
=======
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputProvider,
  PromptInputSubmit,
  PromptInputTextarea,
} from '@/components/ai-elements/prompt-input'
>>>>>>> refs/remotes/origin/main
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
<<<<<<< HEAD
import {
  PromptInput,
  PromptInputActionAddAttachments,
  PromptInputActionMenu,
  PromptInputActionMenuContent,
  PromptInputActionMenuTrigger,
  PromptInputBody,
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
=======
import { Conversation, ConversationContent, ConversationScrollButton } from '@/components/ai-elements/conversation'
import type { AttachmentData } from '@/components/ai-elements/attachments'
>>>>>>> refs/remotes/origin/main

const status = ref<'submitted' | 'streaming' | 'ready' | 'error'>('ready')
const messages = ref<MessageType[]>([])

interface Version {
  id: string
  content: string
}

interface MessageType {
  key: string
  role: 'user' | 'assistant'
  versions?: Version[]
  content?: string
  attachments?: AttachmentData[]
}
<<<<<<< HEAD

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
=======
async function onFetchResponse(response: Response): Promise<void> {
  status.value = 'streaming'
  let text = ''
  let decoder = new TextDecoder()
  if (response.ok) {
    const reader = response.body?.getReader()
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }
      text += decoder.decode(value)
      const lines = text.split('\n')
      const newMessages: MessageType[] = lines.filter(line => line.length > 1).map(j => JSON.parse(j))
      for (const message of newMessages) {
        updateStreamingContent(message)
      }
    }
    status.value = 'ready'
  } else {
    const text = await response.text()
    console.error(`Unexpected response: ${response.status}`, { response, text })
    throw new Error(`Unexpected response: ${response.status}`)
  }
}
function updateStreamingContent(message: MessageType) {
  const { key, versions } = message
  const versionId = versions[0].id
  const content = versions[0].content
  const target = messages.value.find(msg => msg.key === key)
  if (!target) {
    messages.value.push(message)
>>>>>>> refs/remotes/origin/main
    return
  }
  const version = target.versions?.find(v => v.id === versionId)
  version.content = content
  messages.value = [...messages.value]
}

function onError(error: any) {
  console.error(error)
  document.getElementById('error')?.classList.remove('d-none')
}

async function onSubmit(messages: PromptInputMessage[]): Promise<void> {
  status.value = 'submitted'
<<<<<<< HEAD
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

=======
  const body = JSON.stringify({
    prompt: messages.text,
  })
  const response = await fetch('/api/chat', { method: 'POST', body, headers: { 'Content-Type': 'application/json' } })
  await onFetchResponse(response)
}
>>>>>>> refs/remotes/origin/main
</script>

<template>
  <div class="relative flex size-full flex-col divide-y overflow-hidden">
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
<<<<<<< HEAD

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

=======
    <div class="w-full px-4 pb-4">
      <PromptInputProvider @submit="onSubmit">
        <PromptInput multiple global-drop class="w-full">
>>>>>>> refs/remotes/origin/main
          <PromptInputBody>
            <PromptInputTextarea />
          </PromptInputBody>
<<<<<<< HEAD

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
=======
          <PromptInputFooter>
            <PromptInputSubmit :disabled="status === 'streaming'" :status="status" />
>>>>>>> refs/remotes/origin/main
          </PromptInputFooter>
        </PromptInput>
      </PromptInputProvider>
    </div>
  </div>
</template>
<style></style>