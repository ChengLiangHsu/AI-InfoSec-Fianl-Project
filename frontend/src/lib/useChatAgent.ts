import { ref, computed } from 'vue'

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
    try {
      const res = await fetch(`/api/chat/?project_id=${encodeURIComponent(targetId)}`)
      if (res.ok) {
        const text = await res.text()
        const lines = text.split('\n').filter(l => l.trim().length > 0)
        conversations.value[targetId] = lines.map(line => JSON.parse(line))
      }
    } catch (e) {
      console.error(`Failed to load chat history for ${targetId}`, e)
    }
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

  async function onFetchResponse(response: Response, targetId: string): Promise<void> {
    statusMap.value[targetId] = 'streaming'
    let text = ''
    const decoder = new TextDecoder()
    if (response.ok) {
      const reader = response.body?.getReader()
      if (!reader) return
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        text += decoder.decode(value)
        const lines = text.split('\n')
        const newMessages: MessageType[] = lines.filter(line => line.length > 1).map(j => JSON.parse(j))
        for (const message of newMessages) {
          updateStreamingContent(message, targetId)
        }
      }
      statusMap.value[targetId] = 'ready'
    } else {
      const errorText = await response.text()
      statusMap.value[targetId] = 'error'
      console.error(`Unexpected response for ${targetId}: ${response.status}`, { response, errorText })
    }
  }

  async function sendPrompt(promptText: string, pid?: string): Promise<void> {
    if (!promptText.trim()) return
    const targetId = pid || currentProjectId.value
    statusMap.value[targetId] = 'submitted'
    try {
      const body = JSON.stringify({
        prompt: promptText,
        project_id: targetId,
      })
      const response = await fetch('/api/chat', {
        method: 'POST',
        body,
        headers: { 'Content-Type': 'application/json' }
      })
      await onFetchResponse(response, targetId)
    } catch (err) {
      statusMap.value[targetId] = 'error'
      console.error(`Failed to send prompt to ${targetId}:`, err)
    }
  }

  return {
    status,
    messages,
    loadInitialMessages,
    sendPrompt,
  }
}
