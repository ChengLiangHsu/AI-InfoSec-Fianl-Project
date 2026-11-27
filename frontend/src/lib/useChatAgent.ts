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

export type ChatMode = 'default' | 'scenario'

export interface SendPromptOptions {
  mode?: ChatMode
  onScenarioUpdated?: (scenario: ScenarioData) => void
}

// Global cache: project_id -> MessageType[]
const conversations = ref<Record<string, MessageType[]>>({})
const statusMap = ref<Record<string, 'submitted' | 'streaming' | 'ready' | 'error'>>({})

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
        conversations.value[targetId] = lines.map(line => JSON.parse(line))
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
    onScenarioUpdated?: (scenario: ScenarioData) => void
  ) {
    const trimmed = line.trim()
    if (!trimmed) return
    try {
      const parsed = JSON.parse(trimmed)
      if (parsed && parsed.type === 'scenario_updated' && parsed.scenario) {
        onScenarioUpdated?.(parsed.scenario as ScenarioData)
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
    onScenarioUpdated?: (scenario: ScenarioData) => void
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
          handleStreamLine(line, targetId, onScenarioUpdated)
        }
      }
      buffer += decoder.decode()
      if (buffer.trim()) {
        handleStreamLine(buffer, targetId, onScenarioUpdated)
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
      await onFetchResponse(response, targetId, options?.onScenarioUpdated)
    } catch (err) {
      statusMap.value[targetId] = 'error'
      console.error(`Failed to send prompt to ${targetId}:`, err)
    }
  }

  async function clearChat(pid?: string): Promise<void> {
    const targetId = pid || currentProjectId.value
    conversations.value[targetId] = []
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
    loadInitialMessages,
    sendPrompt,
    injectAssistantMessage,
    hasMessages,
    clearChat,
  }
}

