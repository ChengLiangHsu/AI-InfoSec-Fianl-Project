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
  const body = JSON.stringify({
    prompt: messages.text,
  })
  const response = await fetch('/api/chat', { method: 'POST', body, headers: { 'Content-Type': 'application/json' } })
  await onFetchResponse(response)
}
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
    <div class="w-full px-4 pb-4">
      <PromptInputProvider @submit="onSubmit">
        <PromptInput multiple global-drop class="w-full">
          <PromptInputBody>
            <PromptInputTextarea />
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