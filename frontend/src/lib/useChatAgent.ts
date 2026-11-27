import { ref, computed } from 'vue'
import type { ScenarioData } from './scenarioSchema'

export interface Version {
  id: string
  content: string
}

export interface MessageType {
  key: string
  role: 'user' | 'assistant'
  versions?: Version[]
  content?: string
}

export interface InterviewQuestionOption {
  label: string
  description?: string
  recommended?: boolean
}

export interface InterviewQuestion {
  id: string
  question: string
  options: InterviewQuestionOption[]
  is_multi_select?: boolean
  allow_custom?: boolean
  step_label?: string
  can_generate_now?: boolean
}

export type ChatMode = 'default' | 'scenario' | 'spectral'
export type ChatChannel = 'default' | 'spectral'

export interface SendPromptOptions {
  mode?: ChatMode
  selectedPlotNumbers?: number[]
  currentFormula?: string
  onScenarioUpdated?: (scenario: ScenarioData) => void
  onQuestionReceived?: (question: InterviewQuestion) => void
}

export interface UseChatAgentOptions {
  channel?: ChatChannel
}

// Global cache: cacheKey (`projectId` for default, `${projectId}::spectral` for spectral) -> state
const conversations = ref<Record<string, MessageType[]>>({})
const statusMap = ref<Record<string, 'submitted' | 'streaming' | 'ready' | 'error'>>({})
const activeQuestions = ref<Record<string, InterviewQuestion | null>>({})

function buildCacheKey(projectId: string, channel: ChatChannel): string {
  return channel === 'spectral' ? `${projectId}::spectral` : projectId
}

export function useChatAgent(
  projectIdRef?: () => string | undefined,
  agentOptions?: UseChatAgentOptions
) {
  const channel: ChatChannel = agentOptions?.channel ?? 'default'

  const currentProjectId = computed(() => {
    const pid = projectIdRef ? projectIdRef() : 'home'
    return pid || 'home'
  })

  const currentCacheKey = computed(() => buildCacheKey(currentProjectId.value, channel))

  const status = computed<'submitted' | 'streaming' | 'ready' | 'error'>({
    get: () => statusMap.value[currentCacheKey.value] || 'ready',
    set: (val) => {
      statusMap.value[currentCacheKey.value] = val
    }
  })

  const messages = computed<MessageType[]>({
    get: () => conversations.value[currentCacheKey.value] || [],
    set: (msgs) => {
      conversations.value[currentCacheKey.value] = msgs
    }
  })

  const activeQuestion = computed<InterviewQuestion | null>({
    get: () => activeQuestions.value[currentCacheKey.value] ?? null,
    set: (q) => {
      activeQuestions.value[currentCacheKey.value] = q
    }
  })

  function setActiveQuestion(question: InterviewQuestion | null, pid?: string) {
    const targetKey = buildCacheKey(pid || currentProjectId.value, channel)
    activeQuestions.value[targetKey] = question
  }

  async function loadInitialMessages(pid?: string) {
    const targetId = pid || currentProjectId.value
    const targetKey = buildCacheKey(targetId, channel)
    if (conversations.value[targetKey] && conversations.value[targetKey].length > 0) {
      return
    }
    if (targetId === 'home') {
      if (!conversations.value[targetKey]) {
        conversations.value[targetKey] = []
      }
      return
    }
    try {
      const channelParam = channel === 'spectral' ? '&channel=spectral' : ''
      const res = await fetch(`/api/task/chat/?project_id=${encodeURIComponent(targetId)}${channelParam}`)
      if (res.ok) {
        const text = await res.text()
        const lines = text.split('\n').filter(l => l.trim().length > 0)
        const loadedMessages: MessageType[] = []
        let pendingQuestion: InterviewQuestion | null = null
        for (const line of lines) {
          try {
            const parsed = JSON.parse(line)
            if (parsed && parsed.type === 'interview_question' && parsed.question) {
              pendingQuestion = parsed.question as InterviewQuestion
            } else if (parsed && parsed.role) {
              loadedMessages.push(parsed as MessageType)
            }
          } catch {
            // ignore malformed history line
          }
        }
        conversations.value[targetKey] = loadedMessages
        if (pendingQuestion) {
          activeQuestions.value[targetKey] = pendingQuestion
        }
      }
    } catch (e) {
      console.error(`Failed to load chat history for ${targetId} (${channel})`, e)
    }
  }

  function injectAssistantMessage(content: string, pid?: string) {
    const targetKey = buildCacheKey(pid || currentProjectId.value, channel)
    if (!conversations.value[targetKey]) {
      conversations.value[targetKey] = []
    }
    const key = `proactive-${Date.now()}`
    conversations.value[targetKey] = [
      ...conversations.value[targetKey],
      {
        key,
        role: 'assistant',
        content,
        versions: [{ id: `v-${Date.now()}`, content }]
      }
    ]
  }

  function hasMessages(pid?: string): boolean {
    const targetKey = buildCacheKey(pid || currentProjectId.value, channel)
    return (conversations.value[targetKey]?.length || 0) > 0
  }

  function updateStreamingContent(message: MessageType, targetKey: string) {
    const { key, versions } = message
    if (!versions || versions.length === 0) return
    const versionId = versions[0].id
    const content = versions[0].content

    if (!conversations.value[targetKey]) {
      conversations.value[targetKey] = []
    }
    const currentList = conversations.value[targetKey]
    const target = currentList.find(msg => msg.key === key)
    if (!target) {
      currentList.push(message)
    } else {
      const version = target.versions?.find(v => v.id === versionId)
      if (version) {
        version.content = content
      }
    }
    conversations.value[targetKey] = [...currentList]
  }

  function handleStreamLine(
    line: string,
    targetKey: string,
    onScenarioUpdated?: (scenario: ScenarioData) => void,
    onQuestionReceived?: (question: InterviewQuestion) => void
  ) {
    const trimmed = line.trim()
    if (!trimmed) return
    try {
      const parsed = JSON.parse(trimmed)
      if (parsed && parsed.type === 'scenario_updated' && parsed.scenario) {
        activeQuestions.value[targetKey] = null
        onScenarioUpdated?.(parsed.scenario as ScenarioData)
        return
      }
      if (parsed && parsed.type === 'interview_question' && parsed.question) {
        const q = parsed.question as InterviewQuestion
        activeQuestions.value[targetKey] = q
        onQuestionReceived?.(q)
        return
      }
      updateStreamingContent(parsed as MessageType, targetKey)
    } catch (e) {
      console.error('Failed to parse chat stream line:', trimmed, e)
    }
  }

  async function onFetchResponse(
    response: Response,
    targetKey: string,
    onScenarioUpdated?: (scenario: ScenarioData) => void,
    onQuestionReceived?: (question: InterviewQuestion) => void
  ): Promise<void> {
    statusMap.value[targetKey] = 'streaming'
    let buffer = ''
    const decoder = new TextDecoder()
    if (response.ok) {
      const reader = response.body?.getReader()
      if (!reader) return
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
          handleStreamLine(line, targetKey, onScenarioUpdated, onQuestionReceived)
        }
      }
      buffer += decoder.decode()
      if (buffer.trim()) {
        handleStreamLine(buffer, targetKey, onScenarioUpdated, onQuestionReceived)
      }
      statusMap.value[targetKey] = 'ready'
    } else {
      const errorText = await response.text()
      statusMap.value[targetKey] = 'error'
      console.error(`Unexpected response for ${targetKey}: ${response.status}`, { response, errorText })
    }
  }

  async function sendPrompt(
    promptText: string,
    pid?: string,
    options?: SendPromptOptions
  ): Promise<void> {
    if (!promptText.trim()) return
    const targetId = pid || currentProjectId.value
    const effectiveMode: ChatMode = options?.mode || (channel === 'spectral' ? 'spectral' : 'default')
    const targetKey = buildCacheKey(targetId, effectiveMode === 'spectral' ? 'spectral' : channel)
    activeQuestions.value[targetKey] = null
    statusMap.value[targetKey] = 'submitted'
    try {
      const payload: Record<string, unknown> = {
        prompt: promptText,
        project_id: targetId,
        mode: effectiveMode,
      }
      if (options?.selectedPlotNumbers) {
        payload.selected_plot_numbers = options.selectedPlotNumbers
      }
      if (options?.currentFormula) {
        payload.current_formula = options.currentFormula
      }
      const response = await fetch('/api/task/chat', {
        method: 'POST',
        body: JSON.stringify(payload),
        headers: { 'Content-Type': 'application/json' }
      })
      await onFetchResponse(response, targetKey, options?.onScenarioUpdated, options?.onQuestionReceived)
    } catch (err) {
      statusMap.value[targetKey] = 'error'
      console.error(`Failed to send prompt to ${targetId}:`, err)
    }
  }

  async function clearChat(pid?: string): Promise<void> {
    const targetId = pid || currentProjectId.value
    const targetKey = buildCacheKey(targetId, channel)
    conversations.value[targetKey] = []
    activeQuestions.value[targetKey] = null
    statusMap.value[targetKey] = 'ready'
    if (targetId === 'home') return
    try {
      const channelParam = channel === 'spectral' ? '&channel=spectral' : ''
      await fetch(`/api/task/chat/?project_id=${encodeURIComponent(targetId)}${channelParam}`, {
        method: 'DELETE',
      })
    } catch (e) {
      console.error(`Failed to clear chat for ${targetId} (${channel})`, e)
    }
  }

  return {
    status,
    messages,
    activeQuestion,
    loadInitialMessages,
    sendPrompt,
    injectAssistantMessage,
    setActiveQuestion,
    hasMessages,
    clearChat,
  }
}

