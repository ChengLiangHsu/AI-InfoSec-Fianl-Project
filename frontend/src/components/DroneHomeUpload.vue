<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  UploadCloud,
  Sparkles,
  Bot,
  ImageIcon,
  CheckCircle2,
  AlertTriangle,
  X,
  Trash2,
  Camera,
  Layers,
  MapPin,
  Compass,
} from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import exifr from 'exifr'

interface Project {
  id: string
  name: string
  images?: number
  progress?: number
}

interface UploadFileItem {
  file: File
  name: string
  sizeStr: string
  latitude?: number
  longitude?: number
  hasGps: boolean
}

const emit = defineEmits<{
  (e: 'projectCreated', project: Project): void
}>()

const isDragging = ref(false)
const isParsingExif = ref(false)
const isUploading = ref(false)
const selectedFiles = ref<UploadFileItem[]>([])
const projectName = ref('')
const fileInputRef = ref<HTMLInputElement | null>(null)

const totalFileSizeStr = computed(() => {
  const bytes = selectedFiles.value.reduce((acc, f) => acc + f.file.size, 0)
  return (bytes / 1024 / 1024).toFixed(2) + ' MB'
})

const gpsValidCount = computed(() => {
  return selectedFiles.value.filter((f) => f.hasGps).length
})

const allHaveGps = computed(() => {
  return (
    selectedFiles.value.length > 0 &&
    gpsValidCount.value === selectedFiles.value.length
  )
})

function triggerFileInput() {
  fileInputRef.value?.click()
}

function generateDefaultProjectName(): string {
  const now = new Date()
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  const hh = String(now.getHours()).padStart(2, '0')
  const min = String(now.getMinutes()).padStart(2, '0')
  return `田間航拍_${mm}${dd}_${hh}${min}`
}

async function processIncomingFiles(files: File[]) {
  if (files.length === 0) return

  isParsingExif.value = true
  try {
    for (const file of files) {
      let lat: number | undefined
      let lng: number | undefined
      let hasGps = false

      try {
        const gps = await exifr.gps(file)
        if (gps && typeof gps.latitude === 'number' && typeof gps.longitude === 'number') {
          lat = Number(gps.latitude.toFixed(6))
          lng = Number(gps.longitude.toFixed(6))
          hasGps = true
        }
      } catch (err) {
        console.warn('GPS extraction failed for', file.name, err)
      }

      selectedFiles.value.push({
        file,
        name: file.name,
        sizeStr: (file.size / 1024 / 1024).toFixed(2) + ' MB',
        latitude: lat,
        longitude: lng,
        hasGps,
      })
    }

    if (!projectName.value) {
      projectName.value = generateDefaultProjectName()
    }
  } finally {
    isParsingExif.value = false
  }
}

function onFilesSelected(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return
  processIncomingFiles(Array.from(input.files))
  input.value = ''
}

function onDragOver() {
  isDragging.value = true
}

function onDragLeave(event: DragEvent) {
  // Prevent flickering when hovering over child elements
  const currentTarget = event.currentTarget as HTMLElement
  const relatedTarget = event.relatedTarget as Node | null
  if (!currentTarget.contains(relatedTarget)) {
    isDragging.value = false
  }
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  if (!event.dataTransfer?.files || event.dataTransfer.files.length === 0) return

  const files = Array.from(event.dataTransfer.files).filter((file) => {
    const ext = file.name.toLowerCase()
    return ext.endsWith('.jpg') || ext.endsWith('.jpeg') || ext.endsWith('.png')
  })

  if (files.length === 0) {
    alert('請上傳 JPG 或 PNG 格式之無人機空拍照片')
    return
  }

  processIncomingFiles(files)
}

function removeFile(index: number) {
  selectedFiles.value.splice(index, 1)
  if (selectedFiles.value.length === 0) {
    projectName.value = ''
  }
}

function clearFiles() {
  selectedFiles.value = []
  projectName.value = ''
}

async function handleStartOdmTask() {
  if (selectedFiles.value.length === 0) {
    alert('請先拖入或選取空拍照片')
    return
  }

  isUploading.value = true
  const currentName = projectName.value.trim() || generateDefaultProjectName()
  const filesToUpload = selectedFiles.value.map((item) => item.file)

  const formData = new FormData()
  formData.append('name', currentName)
  for (const f of filesToUpload) {
    formData.append('files', f)
  }

  try {
    const res = await fetch('/api/task/odm-task', {
      method: 'POST',
      body: formData,
    })
    const data = await res.json().catch(() => null)
    if (res.ok && data?.result) {
      const newProj: Project = {
        id: data.data.id,
        name: currentName,
        images: filesToUpload.length,
        progress: 0,
      }
      clearFiles()
      emit('projectCreated', newProj)
    } else {
      const errMsg = data?.message || '建立正射拼接任務失敗，請檢查 NodeODM 伺服器狀態'
      alert(errMsg)
    }
  } catch (err) {
    console.error('Failed to submit ODM task:', err)
    alert('上傳連線失敗，請確認後端與 NodeODM 服務狀態')
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <div class="flex h-full w-full flex-col overflow-y-auto bg-background p-6">
    <div class="mx-auto flex w-full max-w-4xl flex-col items-center justify-center gap-6 py-6">



      <!-- 2. 中央上傳拖曳框 (Center Upload Dropzone - 加大字體與焦點感) -->
      <div
        class="group relative flex w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed p-10 sm:p-14 text-center transition-all duration-200 cursor-pointer select-none"
        :class="[
          isDragging
            ? 'border-primary bg-primary/5 scale-[1.01] shadow-lg ring-2 ring-primary/30'
            : 'border-border/80 bg-card/40 hover:border-primary/60 hover:bg-muted/30 hover:shadow-sm',
        ]"
        @dragover.prevent="onDragOver"
        @dragleave.prevent="onDragLeave"
        @drop.prevent="onDrop"
        @click="triggerFileInput"
      >
        <input
          ref="fileInputRef"
          type="file"
          multiple
          accept=".jpg,.jpeg,.png"
          class="hidden"
          @change="onFilesSelected"
        />

        <div class="flex size-20 items-center justify-center rounded-full bg-primary/10 text-primary transition-transform duration-200 group-hover:scale-110 shadow-xs">
          <UploadCloud class="size-10" />
        </div>

        <h3 class="mt-5 text-lg font-bold text-foreground sm:text-2xl">
          拖曳無人機空拍照片至此處，或點擊瀏覽選取
        </h3>
        <p class="mt-2 text-sm text-muted-foreground sm:text-base">
          支援批次拖入多張高解析度航拍影像（.jpg、.jpeg、.png）
        </p>

        <div class="mt-6">
          <Button
            type="button"
            variant="default"
            size="lg"
            class="h-11 gap-2.5 rounded-full px-7 text-sm sm:text-base font-semibold shadow-sm pointer-events-none"
          >
            <Camera class="size-4" />
            瀏覽選取檔案
          </Button>
        </div>
      </div>

      <!-- 3. 即時預檢與確認面板 (Pre-check Summary Panel) -->
      <div
        v-if="selectedFiles.length > 0 || isParsingExif"
        class="w-full space-y-4 rounded-2xl border bg-card p-5 sm:p-6 shadow-sm transition-all"
      >
        <!-- 狀態資訊列 -->
        <div class="flex flex-wrap items-center justify-between gap-3 border-b pb-4">
          <div class="flex items-center gap-2 text-sm sm:text-base font-bold text-foreground">
            <ImageIcon class="size-5 text-primary" />
            <span>已載入待處理相片：</span>
            <span class="text-primary font-bold text-base sm:text-lg">{{ selectedFiles.length }} 張</span>
            <span class="text-xs sm:text-sm text-muted-foreground font-normal">（總容量 {{ totalFileSizeStr }}）</span>
          </div>

          <div class="flex items-center gap-2.5">
            <!-- EXIF 解析中指示器 -->
            <span v-if="isParsingExif" class="inline-flex items-center gap-1.5 text-xs sm:text-sm text-muted-foreground">
              <Spinner class="size-4 animate-spin text-primary" />
              <span>解析 GPS 資訊中...</span>
            </span>

            <!-- GPS 狀態徽章 -->
            <Badge
              v-else-if="allHaveGps"
              variant="outline"
              class="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 gap-1.5 text-xs sm:text-sm px-3 py-1 font-semibold"
            >
              <CheckCircle2 class="size-4" />
              <span>GPS 完整度 100% ({{ gpsValidCount }}/{{ selectedFiles.length }})</span>
            </Badge>

            <Badge
              v-else
              variant="outline"
              class="border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400 gap-1.5 text-xs sm:text-sm px-3 py-1 font-semibold"
            >
              <AlertTriangle class="size-4" />
              <span>有 {{ selectedFiles.length - gpsValidCount }} 張缺少 GPS 座標</span>
            </Badge>

            <Button
              type="button"
              variant="ghost"
              size="sm"
              class="h-8 px-3 text-xs sm:text-sm text-muted-foreground hover:text-destructive font-medium"
              :disabled="isUploading"
              @click="clearFiles"
            >
              <Trash2 class="mr-1.5 size-4" />
              清空
            </Button>
          </div>
        </div>

        <!-- 照片列表橫向滾動縮圖 -->
        <div class="flex gap-3 overflow-x-auto py-2">
          <div
            v-for="(item, idx) in selectedFiles"
            :key="`${item.name}-${idx}`"
            class="relative flex shrink-0 items-center gap-3 rounded-xl border bg-muted/20 px-3.5 py-2.5 text-xs sm:text-sm transition-colors hover:bg-muted/40"
          >
            <div class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-background text-muted-foreground border">
              <ImageIcon class="size-4" />
            </div>

            <div class="flex flex-col min-w-0 max-w-[160px]">
              <span class="truncate font-semibold text-foreground text-xs sm:text-sm" :title="item.name">
                {{ item.name }}
              </span>
              <span class="text-xs text-muted-foreground truncate">
                {{ item.hasGps ? `${item.latitude}, ${item.longitude}` : '無 GPS' }} · {{ item.sizeStr }}
              </span>
            </div>

            <button
              type="button"
              class="ml-1 inline-flex size-6 shrink-0 items-center justify-center rounded-full text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
              :disabled="isUploading"
              @click="removeFile(idx)"
              title="移除此照片"
            >
              <X class="size-3.5" />
            </button>
          </div>
        </div>

        <!-- 專案設定與提交列 -->
        <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 pt-3 border-t">
          <div class="flex flex-1 items-center gap-3">
            <span class="text-xs sm:text-sm font-semibold text-foreground shrink-0">專案名稱：</span>
            <Input
              v-model="projectName"
              type="text"
              placeholder="輸入專案名稱（例如：田間航拍_水稻試驗）"
              class="h-10 text-xs sm:text-sm"
              :disabled="isUploading"
            />
          </div>

          <Button
            type="button"
            size="default"
            class="h-10 gap-2 px-7 text-sm font-bold shadow-xs"
            :disabled="selectedFiles.length === 0 || isUploading || isParsingExif"
            @click="handleStartOdmTask"
          >
            <Spinner v-if="isUploading" class="size-4 animate-spin" />
            <Sparkles v-else class="size-4" />
            <span>{{ isUploading ? '正在派送拼接任務...' : '開始航拍正射拼接' }}</span>
          </Button>
        </div>
      </div>

    </div>
  </div>
</template>
