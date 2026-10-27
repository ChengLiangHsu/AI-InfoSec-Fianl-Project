import { onUnmounted, ref } from 'vue'

export interface Project {
  id: string
  name: string
  images?: number
  progress?: number
  status?: number
}

export interface ProgressCallbacks {
  onUpdate?: (project: Project) => void
  onComplete?: (project: Project) => void
  onError?: (error: unknown) => void
}

export function useOdmProgress() {
  const activeTaskId = ref<string | null>(null)
  const currentProgress = ref<number>(0)
  const isListening = ref<boolean>(false)
  let eventSource: EventSource | null = null

  function closeStream() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    isListening.value = false
    activeTaskId.value = null
  }

  function listenProgress(
    taskId: string,
    callbacks?: ProgressCallbacks
  ) {
    closeStream()

    if (!taskId) return

    activeTaskId.value = taskId
    isListening.value = true

    const es = new EventSource(`/api/odm-task-stream/${encodeURIComponent(taskId)}`)
    eventSource = es

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.error) {
          callbacks?.onError?.(new Error(data.error))
          closeStream()
          return
        }

        const project = data as Project
        if (typeof project.progress === 'number') {
          currentProgress.value = project.progress
        }

        callbacks?.onUpdate?.(project)

        if (typeof project.progress === 'number' && project.progress >= 100) {
          callbacks?.onComplete?.(project)
          closeStream()
        }
      } catch (err) {
        console.error('Failed to parse SSE event data:', err)
      }
    }

    es.onerror = (err) => {
      callbacks?.onError?.(err)
      closeStream()
    }
  }

  onUnmounted(() => {
    closeStream()
  })

  return {
    activeTaskId,
    currentProgress,
    isListening,
    listenProgress,
    closeStream,
  }
}
