<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { Download, FileImage, LoaderCircle, X } from '@lucide/vue'
import {
  DialogRoot, DialogTrigger, DialogPortal, DialogContent,
  DialogTitle, DialogDescription, DialogClose,
} from 'reka-ui'
import { Button } from '@/components/ui/button'
import { downloadImage, type ImageExportFormat } from '@/lib/imageDownload'

interface FormulaOption { id: string; help?: string }
const props = defineProps<{
  projectId: string
  projectName: string
  progress?: number
  formulas: FormulaOption[]
  currentFormula: string
}>()
const open = ref(false)
const formulaSelect = ref<HTMLSelectElement | null>(null)
const formula = ref('rgb')
const format = ref<ImageExportFormat>('tiff')
const pending = ref(false)
const error = ref('')
const status = ref('')
const options = ref<FormulaOption[]>(props.formulas)
const loadingFormulas = ref(false)
const formulaError = ref('')
let controller: AbortController | undefined

const ready = computed(() => props.progress === 100)
const layerName = computed(() => formula.value === 'rgb' ? '原始正射圖（RGB）' : `${formula.value} 光譜圖`)
const formats: { id: ImageExportFormat; label: string; hint: string }[] = [
  { id: 'tiff', label: 'TIFF', hint: '保留影像細節' },
  { id: 'jpg', label: 'JPG', hint: '輕巧分享' },
  { id: 'pdf', label: 'PDF', hint: '單頁影像文件' },
]
const formatDescription = computed(() => {
  if (format.value === 'tiff') return formula.value === 'rgb'
    ? '下載原始正射 TIFF，保留來源的地理定位資訊。'
    : '下載無損著色光譜 TIFF，沿用來源的地理定位資訊；內容為彩色影像，非原始指數矩陣。'
  if (format.value === 'jpg') return '下載完整尺寸 JPG；透明區域以白底呈現，不含地理定位資訊。'
  return '下載單頁 PDF，保留完整影像比例；透明區域以白底呈現，不含地理定位資訊。'
})

watch(() => props.formulas, value => { options.value = value })
watch(open, async value => {
  if (!value) return
  if (!pending.value) {
    formula.value = props.currentFormula
    error.value = ''
    status.value = ''
  }
  if (!options.value.length) await loadFormulas()
})

async function loadFormulas() {
  if (loadingFormulas.value) return
  loadingFormulas.value = true
  formulaError.value = ''
  try {
    const response = await fetch('/api/task/odm-task-formulas')
    if (!response.ok) throw new Error()
    const payload = await response.json()
    if (!Array.isArray(payload.data)) throw new Error()
    options.value = payload.data
  } catch {
    formulaError.value = '無法載入演算法清單；仍可下載正射圖。'
  } finally {
    loadingFormulas.value = false
  }
}

async function startDownload() {
  if (!ready.value || pending.value) return
  controller = new AbortController()
  pending.value = true
  error.value = ''
  status.value = ''
  try {
    await downloadImage(props.projectId, formula.value, format.value, controller.signal)
    status.value = '已交給瀏覽器下載。'
  } catch (cause) {
    if (controller.signal.aborted) status.value = '已取消下載。'
    else error.value = cause instanceof Error ? cause.message : '下載失敗，請重試。'
  } finally {
    pending.value = false
  }
}

onUnmounted(() => controller?.abort())
</script>

<template>
  <DialogRoot v-model:open="open" :modal="false">
    <DialogTrigger as-child>
      <Button variant="outline" size="sm" class="shrink-0 cursor-pointer gap-1.5" aria-label="下載影像">
        <LoaderCircle v-if="pending" class="size-4 animate-spin" />
        <Download v-else class="size-4" />
        <span class="hidden sm:inline">下載影像</span>
      </Button>
    </DialogTrigger>
    <DialogPortal>
      <DialogContent
        class="fixed right-3 top-16 z-50 flex max-h-[calc(100dvh-10rem)] w-[calc(100vw-1.5rem)] flex-col overflow-hidden rounded-2xl border border-white/15 bg-zinc-950 text-zinc-100 shadow-2xl sm:right-4 sm:w-[380px]"
        @open-auto-focus="formulaSelect?.focus(); $event.preventDefault()"
      >
        <div class="flex items-start justify-between gap-3 border-b border-white/10 p-5">
          <div class="min-w-0">
            <DialogTitle class="flex items-center gap-2 text-base font-semibold">
              <Download class="size-4 text-purple-300" />下載影像
            </DialogTitle>
            <DialogDescription class="mt-1.5 text-xs leading-relaxed text-zinc-400">
              獨立匯出成果，可隨時收起並繼續目前步驟。
            </DialogDescription>
          </div>
          <DialogClose as-child>
            <Button variant="ghost" size="icon" class="size-7 shrink-0 cursor-pointer text-zinc-400 hover:bg-white/10 hover:text-white" aria-label="關閉下載面板">
              <X class="size-4" />
            </Button>
          </DialogClose>
        </div>
        <form class="space-y-5 overflow-y-auto p-5" @submit.prevent="startDownload">
          <div class="flex items-center gap-3 rounded-xl bg-white/5 p-3">
            <FileImage class="size-5 shrink-0 text-purple-300" />
            <div class="min-w-0">
              <p class="truncate text-sm font-medium" :title="projectName">{{ projectName }}</p>
              <p class="mt-0.5 text-xs text-zinc-400">完整影像 · 不包含小區標註與畫布工具</p>
            </div>
          </div>
          <p v-if="!ready" role="status" class="rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-xs leading-relaxed text-amber-200">
            正射影像拼接中（{{ progress ?? 0 }}%），完成後即可下載。
          </p>
          <div class="space-y-2">
            <label for="export-layer" class="text-xs font-medium text-zinc-300">選擇影像</label>
            <select
              id="export-layer" ref="formulaSelect" v-model="formula" :disabled="pending"
              class="h-10 w-full rounded-lg border border-white/20 bg-zinc-900 px-3 text-sm outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400 disabled:opacity-50"
            >
              <option value="rgb">原始正射圖（RGB）</option>
              <optgroup v-if="options.length" label="光譜演算法">
                <option v-for="item in options" :key="item.id" :value="item.id">{{ item.id }} 光譜圖</option>
              </optgroup>
            </select>
            <p v-if="loadingFormulas" class="text-xs text-zinc-400">載入演算法清單中…</p>
            <p v-if="formulaError" role="alert" class="text-xs text-amber-200">
              {{ formulaError }}
              <button type="button" class="ml-1 cursor-pointer underline" @click="loadFormulas">重試</button>
            </p>
          </div>
          <fieldset :disabled="pending" class="space-y-2">
            <legend class="mb-2 text-xs font-medium text-zinc-300">下載格式</legend>
            <div class="grid grid-cols-3 gap-2">
              <label v-for="item in formats" :key="item.id" class="cursor-pointer">
                <input v-model="format" type="radio" name="export-format" :value="item.id" class="peer sr-only" />
                <span class="flex flex-col items-center gap-1 rounded-lg border border-white/15 px-2 py-3 text-zinc-400 transition-colors peer-checked:border-purple-400 peer-checked:bg-purple-400/10 peer-checked:text-purple-200 peer-focus-visible:ring-2 peer-focus-visible:ring-purple-300 peer-disabled:opacity-50">
                  <span class="text-sm font-semibold">{{ item.label }}</span>
                  <span class="text-[11px]">{{ item.hint }}</span>
                </span>
              </label>
            </div>
          </fieldset>
          <p class="min-h-12 text-xs leading-relaxed text-zinc-400">{{ formatDescription }}</p>
          <div class="space-y-3 border-t border-white/10 pt-4">
            <div class="flex items-center justify-between gap-2 text-xs text-zinc-400">
              <span>{{ layerName }}</span><span class="font-mono uppercase">.{{ format }}</span>
            </div>
            <p v-if="error" role="alert" class="text-xs leading-relaxed text-red-300">{{ error }}</p>
            <p v-if="status" role="status" class="text-xs text-emerald-300">{{ status }}</p>
            <p v-if="pending" role="status" class="text-xs leading-relaxed text-purple-200">
              正在準備及傳輸影像，大圖可能需要一些時間。可收起面板繼續操作。
            </p>
            <Button type="submit" :disabled="!ready || pending" class="w-full cursor-pointer gap-2 bg-purple-600 text-white hover:bg-purple-500">
              <LoaderCircle v-if="pending" class="size-4 animate-spin" /><Download v-else class="size-4" />
              {{ pending ? '準備下載中…' : '下載影像' }}
            </Button>
            <Button v-if="pending" type="button" variant="ghost" class="w-full cursor-pointer text-zinc-300 hover:bg-white/10 hover:text-white" @click="controller?.abort()">取消下載</Button>
          </div>
        </form>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
