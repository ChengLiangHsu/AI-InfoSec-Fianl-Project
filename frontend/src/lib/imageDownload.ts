export type ImageExportFormat = 'tiff' | 'jpg' | 'pdf'

export function imageExportUrl(taskId: string, formula: string, format: ImageExportFormat): string {
  const query = new URLSearchParams({ formula, format })
  return `/api/task/odm-task-export/${encodeURIComponent(taskId)}?${query}`
}

function attachmentFilename(response: Response, fallback: string): string {
  const disposition = response.headers.get('content-disposition') ?? ''
  const encoded = disposition.match(/filename\*=utf-8''([^;]+)/i)?.[1]
  if (encoded) {
    try { return decodeURIComponent(encoded) } catch { return fallback }
  }
  return disposition.match(/filename="([^"]+)"/i)?.[1] ?? fallback
}

async function downloadError(response: Response): Promise<string> {
  try {
    const payload = await response.json()
    return payload.message || '影像下載失敗，請稍後重試。'
  } catch {
    return `影像下載失敗（${response.status}），請稍後重試。`
  }
}

function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.append(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

export async function downloadImage(
  taskId: string, formula: string, format: ImageExportFormat, signal: AbortSignal,
): Promise<void> {
  const response = await fetch(imageExportUrl(taskId, formula, format), { signal })
  if (!response.ok) throw new Error(await downloadError(response))
  const blob = await response.blob()
  signal.throwIfAborted()
  if (!blob.size) throw new Error('下載的影像為空，請重試。')
  saveBlob(blob, attachmentFilename(response, `${taskId}_${formula}.${format}`))
}
