import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ImageDownloadPanel from '@/components/ImageDownloadPanel.vue'
import { downloadImage, imageExportUrl } from '@/lib/imageDownload'

const props = {
  projectId: 'field-1', projectName: '試驗田', progress: 100,
  formulas: [{ id: 'VARI' }, { id: 'vNDVI' }], currentFormula: 'rgb',
}
let click: ReturnType<typeof vi.spyOn>
beforeEach(() => {
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test-image')
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
  click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
})

async function openPanel(overrides = {}) {
  const wrapper = mount(ImageDownloadPanel, { props: { ...props, ...overrides }, attachTo: document.body })
  await wrapper.get('button[aria-label="下載影像"]').trigger('click')
  await flushPromises()
  return wrapper
}

async function submit() {
  document.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  await flushPromises()
}

function response() {
  return new Response('image bytes', {
    headers: { 'content-disposition': "attachment; filename*=utf-8''%E8%A9%A6%E9%A9%97%E7%94%B0_VARI.jpg" },
  })
}

describe('image downloads', () => {
  it('escapes query parameters and uses the server attachment filename', async () => {
    const fetch = vi.fn().mockResolvedValue(response())
    vi.stubGlobal('fetch', fetch)
    await downloadImage('field-1', 'VARI', 'jpg', new AbortController().signal)
    expect(fetch.mock.calls[0]![0]).toBe('/api/task/odm-task-export/field-1?formula=VARI&format=jpg')
    expect(click.mock.instances[0].download).toBe('試驗田_VARI.jpg')
    expect(imageExportUrl('a/b', 'a&b', 'pdf')).toContain('a%2Fb?formula=a%26b')
  })

  it('keeps the panel nonmodal and uses a separate export selection', async () => {
    const wrapper = await openPanel({ currentFormula: 'VARI' })
    const select = document.querySelector('select')!
    expect(select.value).toBe('VARI')
    select.value = 'vNDVI'
    select.dispatchEvent(new Event('change', { bubbles: true }))
    await flushPromises()
    expect(wrapper.props('currentFormula')).toBe('VARI')
    expect(wrapper.emitted('update:currentFormula')).toBeUndefined()
    expect(document.querySelector('[role="dialog"]')!.getAttribute('aria-modal')).not.toBe('true')
    expect(document.body.style.pointerEvents).not.toBe('none')
  })

  it('blocks download until stitching completes, independently of plot count', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response()))
    const wrapper = await openPanel({ progress: 42 })
    expect(document.querySelector<HTMLButtonElement>('button[type="submit"]')!.disabled).toBe(true)
    await submit()
    expect(fetch).not.toHaveBeenCalled()
    await wrapper.setProps({ progress: 100 })
    await submit()
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(document.body.textContent).toContain('已交給瀏覽器下載')
  })

  it('downloads the selected layer and format while preserving the active map', async () => {
    const fetch = vi.fn().mockResolvedValue(response())
    vi.stubGlobal('fetch', fetch)
    const wrapper = await openPanel({ currentFormula: 'VARI' })
    const radio = document.querySelector<HTMLInputElement>('input[value="pdf"]')!
    radio.click()
    await submit()
    expect(fetch.mock.calls[0]![0]).toContain('formula=VARI&format=pdf')
    expect(wrapper.props('currentFormula')).toBe('VARI')
  })

  it('retains an in-progress download when the panel closes and prevents duplicate requests', async () => {
    let resolve!: (value: Response) => void
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(done => { resolve = done })))
    const wrapper = await openPanel()
    await submit()
    await submit()
    expect(fetch).toHaveBeenCalledTimes(1)
    const signal = vi.mocked(fetch).mock.calls[0]![1]!.signal!
    document.querySelector<HTMLButtonElement>('button[aria-label="關閉下載面板"]')!.click()
    await flushPromises()
    expect(signal.aborted).toBe(false)
    resolve(response())
    await flushPromises()
    expect(click).toHaveBeenCalledTimes(1)
    await wrapper.get('button[aria-label="下載影像"]').trigger('click')
    await flushPromises()
    expect(document.querySelector<HTMLButtonElement>('button[type="submit"]')!.disabled).toBe(false)
  })

  it('shows server errors and supports retry', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ message: '來源暫時無法取得' }), { status: 503 }))
      .mockResolvedValueOnce(response()))
    await openPanel()
    await submit()
    expect(document.querySelector('[role="alert"]')!.textContent).toContain('來源暫時無法取得')
    expect(click).not.toHaveBeenCalled()
    await submit()
    expect(click).toHaveBeenCalledTimes(1)
  })

  it('cancels transfer without producing a downloaded file and allows retry', async () => {
    vi.stubGlobal('fetch', vi.fn((_url, options) => new Promise((_resolve, reject) => {
      options.signal.addEventListener('abort', () => reject(new DOMException('cancelled', 'AbortError')))
    })))
    await openPanel()
    await submit()
    const cancel = Array.from(document.querySelectorAll('button')).find(button => button.textContent?.includes('取消下載'))!
    cancel.click()
    await flushPromises()
    expect(document.body.textContent).toContain('已取消下載')
    expect(click).not.toHaveBeenCalled()
    expect(document.querySelector<HTMLButtonElement>('button[type="submit"]')!.disabled).toBe(false)
  })

  it('aborts a pending transfer when the project is left', async () => {
    vi.stubGlobal('fetch', vi.fn((_url, options) => new Promise((_resolve, reject) => {
      options.signal.addEventListener('abort', () => reject(new DOMException('cancelled', 'AbortError')))
    })))
    const wrapper = await openPanel()
    await submit()
    const signal = vi.mocked(fetch).mock.calls[0]![1]!.signal!
    wrapper.unmount()
    await flushPromises()
    expect(signal.aborted).toBe(true)
    expect(click).not.toHaveBeenCalled()
  })

  it('lets the user retry a failed algorithm list while retaining RGB downloads', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce(new Response(JSON.stringify({ data: [{ id: 'VARI' }] }))))
    await openPanel({ formulas: [] })
    expect(document.body.textContent).toContain('仍可下載正射圖')
    Array.from(document.querySelectorAll('button')).find(button => button.textContent?.includes('重試'))!.click()
    await flushPromises()
    expect(document.querySelector('option[value="VARI"]')).not.toBeNull()
  })
})
