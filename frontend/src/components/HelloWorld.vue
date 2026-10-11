<script setup lang="ts">
import type { PromptInputMessage } from '@/components/ai-elements/prompt-input'
import type { ChatStatus, ToolUIPart } from 'ai'
import { CheckIcon, GlobeIcon } from '@lucide/vue'
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
  ModelSelector,
  ModelSelectorContent,
  ModelSelectorEmpty,
  ModelSelectorGroup,
  ModelSelectorInput,
  ModelSelectorItem,
  ModelSelectorList,
  ModelSelectorLogo,
  ModelSelectorLogoGroup,
  ModelSelectorName,
  ModelSelectorTrigger,
} from '@/components/ai-elements/model-selector'
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
// import PromptInputAttachmentsDisplay from './prompt-input-attachments-display.vue'

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

const models = [
  {
    id: 'gpt-4o',
    name: 'GPT-4o',
    chef: 'OpenAI',
    chefSlug: 'openai',
    providers: ['openai', 'azure'],
  },
  {
    id: 'gpt-4o-mini',
    name: 'GPT-4o Mini',
    chef: 'OpenAI',
    chefSlug: 'openai',
    providers: ['openai', 'azure'],
  },
  {
    id: 'claude-opus-4-20250514',
    name: 'Claude 4 Opus',
    chef: 'Anthropic',
    chefSlug: 'anthropic',
    providers: ['anthropic', 'azure', 'google', 'amazon-bedrock'],
  },
  {
    id: 'claude-sonnet-4-20250514',
    name: 'Claude 4 Sonnet',
    chef: 'Anthropic',
    chefSlug: 'anthropic',
    providers: ['anthropic', 'azure', 'google', 'amazon-bedrock'],
  },
  {
    id: 'gemini-2.0-flash-exp',
    name: 'Gemini 2.0 Flash',
    chef: 'Google',
    chefSlug: 'google',
    providers: ['google'],
  },
]

const suggestions = [
  'Explain the Vue 3 Composition API with examples.',
  'What is the difference between ref() and reactive() in Vue 3?',
  'How does Vue\'s reactivity system work under the hood?',
  'Show me how to migrate an Options API component to the Composition API.',
  'How do computed properties work in Vue 3?',
  'When should I use watch() vs watchEffect() in Vue 3?',
  'How do I organize logic using composables in a large Vue 3 app?',
  'Explain the lifecycle of a Vue 3 component using setup().',
]

const modelId = ref<string>(models[0].id)
const modelSelectorOpen = ref(false)
const useWebSearch = ref(false)
const status = ref<ChatStatus>('ready')
const messages = ref<MessageType[]>([])

const selectedModelData = computed(() => models.find(m => m.id === modelId.value))

function addUserMessage(content: string) {
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

  askAgent(userMessage)
}

async function askAgent(userMessage: MessageType) {
  try {
    const response = await fetch('http://127.0.0.1:8000/agent/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userMessage),
    })
    if (!response.ok)
      throw new Error(`HTTP ${response.status}`)
    const body = await response.json()
    if (!body.result)
      throw new Error('result is false')
    messages.value = [...messages.value, body.data.message as MessageType]
  }
  catch (error) {
    console.error('askAgent failed:', error)
  }
  finally {
    status.value = 'ready'
  }
}

function handleSubmit(message: PromptInputMessage) {
  const text = message.text.trim()
  const hasText = text.length > 0
  const hasAttachments = message.files.length > 0

  if (!hasText && !hasAttachments)
    return

  status.value = 'submitted'

  addUserMessage(hasText ? text : 'Sent with attachments')
}

function handleSuggestionClick(suggestion: string) {
  status.value = 'submitted'
  addUserMessage(suggestion)
}

function handleModelSelect(id: string) {
  modelId.value = id
  modelSelectorOpen.value = false
}

function toggleWebSearch() {
  useWebSearch.value = !useWebSearch.value
}
</script>

<template>
  <div class="relative flex h-dvh w-full flex-col divide-y overflow-hidden">
    <Conversation class="min-h-0">
      <ConversationContent>
        <MessageBranch v-for="message in messages" :key="message.key" :default-branch="0">
          <MessageBranchContent>
            <Message v-for="version in message.versions" :key="`${message.key}-${version.id}`" :from="message.from">
              <div>
                <Sources v-if="message.sources?.length">
                  <SourcesTrigger :count="message.sources.length" />
                  <SourcesContent>
                    <Source v-for="source in message.sources" :key="source.href" :href="source.href"
                      :title="source.title" />
                  </SourcesContent>
                </Sources>

                <Reasoning v-if="message.reasoning" :duration="message.reasoning.duration">
                  <ReasoningTrigger />
                  <ReasoningContent :content="message.reasoning.content" />
                </Reasoning>

                <MessageContent>
                  <MessageResponse :content="version.content" :shiki-options="{
                    langs: ['ts', 'vue'],
                  }" />
                </MessageContent>
              </div>
            </Message>
          </MessageBranchContent>

          <MessageBranchSelector v-if="message.versions.length > 1" :from="message.from">
            <MessageBranchPrevious />
            <MessageBranchPage />
            <MessageBranchNext />
          </MessageBranchSelector>
        </MessageBranch>
      </ConversationContent>
      <ConversationScrollButton />
    </Conversation>

    <div class="grid shrink-0 gap-4 pt-4">
      <Suggestions class="max-h-24 overflow-y-auto px-4">
        <Suggestion v-for="suggestion in suggestions" :key="suggestion" :suggestion="suggestion"
          @click="handleSuggestionClick" />
      </Suggestions>

      <div class="w-full px-4 pb-4">
        <PromptInput class="w-full" multiple global-drop @submit="handleSubmit">
          <PromptInputHeader>
            <PromptInputAttachmentsDisplay />
          </PromptInputHeader>

          <PromptInputBody>
            <PromptInputTextarea />
          </PromptInputBody>

          <PromptInputFooter>
            <PromptInputTools>

              <PromptInputSpeechButton />

              <ModelSelector v-model:open="modelSelectorOpen">
                <ModelSelectorTrigger as-child>
                  <PromptInputButton>
                    <ModelSelectorLogo v-if="selectedModelData?.chefSlug" :provider="selectedModelData.chefSlug" />
                    <ModelSelectorName v-if="selectedModelData?.name">
                      {{ selectedModelData.name }}
                    </ModelSelectorName>
                  </PromptInputButton>
                </ModelSelectorTrigger>

                <ModelSelectorContent>
                  <ModelSelectorInput placeholder="Search models..." />
                  <ModelSelectorList>
                    <ModelSelectorEmpty>No models found.</ModelSelectorEmpty>

                    <ModelSelectorGroup v-for="chef in ['OpenAI', 'Anthropic', 'Google']" :key="chef" :heading="chef">
                      <ModelSelectorItem v-for="m in models.filter(model => model.chef === chef)" :key="m.id"
                        :value="m.id" @select="() => handleModelSelect(m.id)">
                        <ModelSelectorLogo :provider="m.chefSlug" />
                        <ModelSelectorName>{{ m.name }}</ModelSelectorName>
                        <ModelSelectorLogoGroup>
                          <ModelSelectorLogo v-for="provider in m.providers" :key="provider" :provider="provider" />
                        </ModelSelectorLogoGroup>
                        <CheckIcon v-if="modelId === m.id" class="ml-auto size-4" />
                        <div v-else class="ml-auto size-4" />
                      </ModelSelectorItem>
                    </ModelSelectorGroup>
                  </ModelSelectorList>
                </ModelSelectorContent>
              </ModelSelector>
            </PromptInputTools>

            <PromptInputSubmit :disabled="status === 'streaming'" :status="status" />
          </PromptInputFooter>
        </PromptInput>
      </div>
    </div>
  </div>
</template>
