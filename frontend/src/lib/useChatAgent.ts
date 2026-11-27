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

export type ChatMode = 'default' | 'scenario'

export interface SendPromptOptions {
  mode?: ChatMode
  onScenarioUpdated?: (scenario: ScenarioData) => void
  onQuestionReceived?: (question: InterviewQuestion) => void
}

// Global cache: project_id -> MessageType[]
const conversations = ref<Record<string, MessageType[]>>({})
const statusMap = ref<Record<string, 'submitted' | 'streaming' | 'ready' | 'error'>>({})
const activeQuestions = ref<Record<string, InterviewQuestion | null>>({})

export function useChatAgent(projectIdRef?: () => string | undefined) {
  const currentProjectId = computed(() => {
    const pid = projectIdRef ? projectIdRef() : 'home'
    return pid || 'home'
  })

  const status = computed<'submitted' | 'streaming' | 'ready' | 'error'>({
    get: () => statusMap.value[currentProjectId.value] || 'ready',
    set: (val) => {
      statusMap.value[currentProjectId.value] = val
    }
  })

  const messages = computed<MessageType[]>({
    get: () => conversations.value[currentProjectId.value] || [],
    set: (msgs) => {
      conversations.value[currentProjectId.value] = msgs
    }
  })

  const activeQuestion = computed<InterviewQuestion | null>({
    get: () => activeQuestions.value[currentProjectId.value] ?? null,
    set: (q) => {
      activeQuestions.value[currentProjectId.value] = q
    }
  })

  function setActiveQuestion(question: InterviewQuestion | null, pid?: string) {
    const targetId = pid || currentProjectId.value
    activeQuestions.value[targetId] = question
  }

  async function loadInitialMessages(pid?: string) {
    const targetId = pid || currentProjectId.value
    if (conversations.value[targetId] && conversations.value[targetId].length > 0) {
      return
    }
    if (targetId === 'home') {
      if (!conversations.value['home']) {
        conversations.value['home'] = []
      }
      return
    }
    try {
      const res = await fetch(`/api/task/chat/?project_id=${encodeURIComponent(targetId)}`)
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
        conversations.value[targetId] = loadedMessages
        if (pendingQuestion) {
          activeQuestions.value[targetId] = pendingQuestion
        }
      }
    } catch (e) {
      console.error(`Failed to load chat history for ${targetId}`, e)
    }
  }

  function injectAssistantMessage(content: string, pid?: string) {
    const targetId = pid || currentProjectId.value
    if (!conversations.value[targetId]) {
      conversations.value[targetId] = []
    }
    const key = `proactive-${Date.now()}`
    conversations.value[targetId] = [
      ...conversations.value[targetId],
      {
        key,
        role: 'assistant',
        content,
        versions: [{ id: `v-${Date.now()}`, content }]
      }
    ]
  }

  function hasMessages(pid?: string): boolean {
    const targetId = pid || currentProjectId.value
    return (conversations.value[targetId]?.length || 0) > 0
  }

  function updateStreamingContent(message: MessageType, targetId: string) {
    const { key, versions } = message
    if (!versions || versions.length === 0) return
    const versionId = versions[0].id
    const content = versions[0].content

    if (!conversations.value[targetId]) {
      conversations.value[targetId] = []
    }
    const currentList = conversations.value[targetId]
    const target = currentList.find(msg => msg.key === key)
    if (!target) {
      currentList.push(message)
    } else {
      const version = target.versions?.find(v => v.id === versionId)
      if (version) {
        version.content = content
      }
    }
    conversations.value[targetId] = [...currentList]
  }

  function handleStreamLine(
    line: string,
    targetId: string,
    onScenarioUpdated?: (scenario: ScenarioData) => void,
    onQuestionReceived?: (question: InterviewQuestion) => void
  ) {
    const trimmed = line.trim()
    if (!trimmed) return
    try {
      const parsed = JSON.parse(trimmed)
      if (parsed && parsed.type === 'scenario_updated' && parsed.scenario) {
        activeQuestions.value[targetId] = null
        onScenarioUpdated?.(parsed.scenario as ScenarioData)
        return
      }
      if (parsed && parsed.type === 'interview_question' && parsed.question) {
        const q = parsed.question as InterviewQuestion
        activeQuestions.value[targetId] = q
        onQuestionReceived?.(q)
        return
      }
      updateStreamingContent(parsed as MessageType, targetId)
    } catch (e) {
      console.error('Failed to parse chat stream line:', trimmed, e)
    }
  }

  async function onFetchResponse(
    response: Response,
    targetId: string,
    onScenarioUpdated?: (scenario: ScenarioData) => void,
    onQuestionReceived?: (question: InterviewQuestion) => void
  ): Promise<void> {
    statusMap.value[targetId] = 'streaming'
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
          handleStreamLine(line, targetId, onScenarioUpdated, onQuestionReceived)
        }
      }
      buffer += decoder.decode()
      if (buffer.trim()) {
        handleStreamLine(buffer, targetId, onScenarioUpdated, onQuestionReceived)
      }
      statusMap.value[targetId] = 'ready'
    } else {
      const errorText = await response.text()
      statusMap.value[targetId] = 'error'
      console.error(`Unexpected response for ${targetId}: ${response.status}`, { response, errorText })
    }
  }

  async function sendPrompt(
    promptText: string,
    pid?: string,
    options?: SendPromptOptions
  ): Promise<void> {
    if (!promptText.trim()) return
    const targetId = pid || currentProjectId.value
    activeQuestions.value[targetId] = null
    statusMap.value[targetId] = 'submitted'
    try {
      const body = JSON.stringify({
        prompt: promptText,
        project_id: targetId,
        mode: options?.mode || 'default',
      })
      const response = await fetch('/api/task/chat', {
        method: 'POST',
        body,
        headers: { 'Content-Type': 'application/json' }
      })
      await onFetchResponse(response, targetId, options?.onScenarioUpdated, options?.onQuestionReceived)
    } catch (err) {
      statusMap.value[targetId] = 'error'
      console.error(`Failed to send prompt to ${targetId}:`, err)
    }
  }

  async function clearChat(pid?: string): Promise<void> {
    const targetId = pid || currentProjectId.value
    conversations.value[targetId] = []
    activeQuestions.value[targetId] = null
    statusMap.value[targetId] = 'ready'
    if (targetId === 'home') return
    try {
      await fetch(`/api/task/chat/?project_id=${encodeURIComponent(targetId)}`, {
        method: 'DELETE',
      })
    } catch (e) {
      console.error(`Failed to clear chat for ${targetId}`, e)
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

