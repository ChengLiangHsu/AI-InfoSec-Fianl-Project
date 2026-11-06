export const uploadLimits = {
  images: 100,
  image_bytes: 25 * 1024 * 1024,
  upload_bytes: 1024 * 1024 * 1024,
  active_tasks: 3,
}

export async function initializeVisitor() {
  const response = await fetch('/api/session', { credentials: 'same-origin' })
  if (!response.ok) throw new Error('無法建立訪客工作階段')
  const payload = await response.json()
  Object.assign(uploadLimits, payload.data.limits)
}

export function getUploadError(files: File[]): string | null {
  if (files.length > uploadLimits.images) return `每個任務最多 ${uploadLimits.images} 張照片`
  if (files.some(file => file.size === 0 || file.size > uploadLimits.image_bytes)) {
    return `單張照片不得為空或超過 ${uploadLimits.image_bytes / 1024 / 1024} MiB`
  }
  if (files.reduce((sum, file) => sum + file.size, 0) > uploadLimits.upload_bytes) {
    return `每個任務總量不得超過 ${uploadLimits.upload_bytes / 1024 / 1024} MiB`
  }
  return null
}
