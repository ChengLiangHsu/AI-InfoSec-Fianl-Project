<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { Sparkles, ImageIcon, ArrowUp, X, CheckCircle2, Clock, Upload, HelpCircle, FileText, Trash2 } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import { Input } from '@/components/ui/input'
import {
  Message,
  MessageBranch,
  MessageBranchContent,
  MessageContent,
  MessageResponse,
} from '@/components/ai-elements/message'
import { Conversation, ConversationContent, ConversationScrollButton } from '@/components/ai-elements/conversation'
import { useChatAgent } from '@/lib/useChatAgent'
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
}

const emit = defineEmits<{
  (e: 'projectCreated', project: Project): void
}>()

const { status, messages, loadInitialMessages, sendPrompt, clearChat, migrateChat } = useChatAgent(() => 'home')

const inputPrompt = ref('')
const projectName = ref('')
const selectedFiles = ref<UploadFileItem[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)
const isUploadingOdm = ref(false)

const quickChips = [
  '🌾 VARI 植生指標是什麼？',
  '🌿 查詢 GLI 與 RGB 指標公式',
  '🧪 水稻田適用哪些植生指標？',
  '📐 列出適合無人機空拍鏡頭的植生指標'
]

onMounted(() => {
  loadInitialMessages()
})

const totalFileSizeStr = computed(() => {
  const bytes = selectedFiles.value.reduce((acc, f) => acc + f.file.size, 0)
  return (bytes / 1024 / 1024).toFixed(2) + ' MB'
})

function triggerFileInput() {
  fileInputRef.value?.click()
}

async function onFilesSelected(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return

  for (const file of Array.from(input.files)) {
    let lat: number | undefined
    let lng: number | undefined
    try {
      const gps = await exifr.gps(file)
      if (gps) {
        lat = Number(gps.latitude.toFixed(6))
        lng = Number(gps.longitude.toFixed(6))
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
    })
  }

  // Auto-generate project name if empty
  if (!projectName.value) {
    const now = new Date()
    projectName.value = `田間航拍_${now.getMonth() + 1}${now.getDate()}_${now.getHours()}${now.getMinutes()}`
  }

  input.value = ''
}

function removeFile(index: number) {
  selectedFiles.value.splice(index, 1)
}

function selectQuickChip(chipText: string) {
  inputPrompt.value = chipText
  handleSend()
}

async function handleSend() {
  const text = inputPrompt.value.trim()
  const hasFiles = selectedFiles.value.length > 0

  if (!text && !hasFiles) return
  if (status.value === 'streaming' || isUploadingOdm.value) return

  inputPrompt.value = ''

  // Case 1: Files are attached -> create ODM task first, then notify agent in chat
  if (hasFiles) {
    isUploadingOdm.value = true
    const currentName = projectName.value.trim() || `田間航拍_${Date.now()}`
    const filesToUpload = selectedFiles.value.map(item => item.file)

    const formData = new FormData()
    formData.append('name', currentName)
    for (const f of filesToUpload) {
      formData.append('files', f)
    }

    try {
      const res = await fetch('/api/odm-task', {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      if (res.ok && data.result) {
        const newProj: Project = {
          id: data.data.id,
          name: currentName,
          images: filesToUpload.length,
          progress: 0,
        }

        // 1. 若主畫面有對話紀錄，將其遷移保存至新建的專案中
        await migrateChat('home', newProj.id)

        // 2. 清空主畫面選取之檔案與專案名稱
        selectedFiles.value = []
        projectName.value = ''

        // 3. 通知父層切換至專案
        emit('projectCreated', newProj)

        // 4. 發送專案建立之指引提示給該專案 (project_id: newProj.id)
        const agentPrompt = text
          ? `${text}\n\n（系統附帶通知：我已上傳 ${filesToUpload.length} 張航拍照片並發起專案「${currentName}」（ID: ${newProj.id}），請解說適用此航拍任務的植生指標與後續評估步驟。）`
          : `我已上傳 ${filesToUpload.length} 張航拍正射原始照片，成功發起專案「${currentName}」（ID: ${newProj.id}）。請說明適合此航拍任務的植生指標與後續處理建議。`

        await sendPrompt(agentPrompt, newProj.id)
      } else {
        alert('建立 ODM 專案失敗，請檢查後端日誌')
      }
    } catch (err) {
      console.error('Failed to create ODM task:', err)
      alert('上傳失敗，請確認伺服器與 NodeODM 連線')
    } finally {
      isUploadingOdm.value = false
    }
    return
  }

  // Case 2: Pure chat conversation / function calling
  await sendPrompt(text)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="relative flex h-full w-full flex-col overflow-hidden bg-background">
    <!-- Messages Scrollable Conversation Area -->
    <div class="flex-1 overflow-y-auto">
      <!-- Gemini Landing Hero (Displayed when no messages) -->
      <div v-if="messages.length === 0"
        class="mx-auto flex max-w-2xl flex-col items-center justify-center px-4 pt-16 pb-8 text-center">
        <div
          class="mb-4 inline-flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary shadow-xs">
          <Sparkles class="size-7 animate-pulse" />
        </div>
        <h1
          class="bg-gradient-to-r from-foreground via-foreground/90 to-muted-foreground bg-clip-text text-3xl font-bold tracking-tight text-transparent sm:text-4xl">
          無人機田間試驗智慧評估代理人
        </h1>
        <p class="mt-3 max-w-lg text-sm text-muted-foreground leading-relaxed">
          以高解析度正射空拍影像為輸入，結合植生光譜指標運算與田間試驗藥效評估。您可以直接諮詢植生指標公式，或附帶航拍照片發起新任務。
        </p>

        <!-- Gemini Prompt Suggestion Chips -->
        <div class="mt-8 flex flex-wrap justify-center gap-2">
          <button v-for="(chip, idx) in quickChips" :key="idx" type="button"
            class="inline-flex items-center rounded-full border bg-muted/30 px-3.5 py-1.5 text-xs text-foreground/80 transition-all hover:border-primary/50 hover:bg-muted/80 hover:text-foreground hover:shadow-xs"
            @click="selectQuickChip(chip)">
            {{ chip }}
          </button>
        </div>
      </div>

      <!-- Conversation Messages -->
      <div v-else class="mx-auto w-full max-w-3xl px-4 py-6">
        <div class="mb-4 flex items-center justify-between border-b pb-2">
          <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Sparkles class="size-3.5 text-primary" />
            <span>主畫面臨時對話（建立專案時將自動保留至專案）</span>
          </div>
          <Button variant="ghost" size="sm" class="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
            @click="clearChat('home')">
            <Trash2 class="mr-1 size-3.5" />
            清空對話
          </Button>
        </div>
        <Conversation>
          <ConversationContent class="space-y-6">
            <MessageBranch v-for="message in messages" :key="message.key" :default-branch="0">
              <MessageBranchContent>
                <Message v-for="version in message.versions" :key="`${message.key}-${version.id}`" :from="message.role">
                  <MessageContent>
                    <MessageResponse :content="version.content" />
                  </MessageContent>
                </Message>
              </MessageBranchContent>
            </MessageBranch>
          </ConversationContent>
          <ConversationScrollButton />
        </Conversation>
      </div>
    </div>

    <!-- Gemini Floating Centralized Input Box -->
    <div class="shrink-0 p-4 pb-6">
      <div class="mx-auto w-full max-w-3xl">
        <!-- Selected Photos Attachment Preview Bar -->
        <div v-if="selectedFiles.length > 0" class="mb-3 rounded-2xl border bg-card/80 p-3 shadow-sm backdrop-blur-xs">
          <div class="flex items-center justify-between pb-2 text-xs text-muted-foreground border-b">
            <div class="flex items-center gap-2">
              <ImageIcon class="size-4 text-primary" />
              <span>已選取 <strong class="text-foreground">{{ selectedFiles.length }}</strong> 張空拍圖片（{{ totalFileSizeStr
                }}）</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="inline-flex items-center gap-1 text-[11px] text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 class="size-3.5" /> GPS EXIF 正常
              </span>
              <button type="button" class="text-xs text-muted-foreground hover:text-destructive"
                @click="selectedFiles = []">
                清空全部
              </button>
            </div>
          </div>

          <!-- Horizontal Scroll of Thumbnails -->
          <div class="flex gap-2 overflow-x-auto py-2">
            <div v-for="(item, idx) in selectedFiles" :key="item.name"
              class="relative flex shrink-0 items-center gap-2 rounded-lg border bg-muted/30 px-2.5 py-1.5 text-xs">
              <ImageIcon class="size-3.5 text-muted-foreground" />
              <div class="flex flex-col">
                <span class="max-w-[140px] truncate font-medium">{{ item.name }}</span>
                <span class="text-[10px] text-muted-foreground">
                  {{ item.latitude ? `${item.latitude.toFixed(4)}, ${item.longitude?.toFixed(4)}` : item.sizeStr }}
                </span>
              </div>
              <button type="button"
                class="ml-1 inline-flex size-4 items-center justify-center rounded-full hover:bg-muted text-muted-foreground hover:text-foreground"
                @click="removeFile(idx)">
                <X class="size-3" />
              </button>
            </div>
          </div>

          <!-- Project Name Input Field -->
          <div class="mt-2 flex items-center gap-2 pt-2 border-t">
            <span class="text-xs text-muted-foreground shrink-0 font-medium">專案名稱：</span>
            <Input v-model="projectName" type="text" placeholder="輸入專案名稱（例如：1024水稻試驗區）" class="h-8 text-xs"
              :disabled="isUploadingOdm" />
          </div>
        </div>

        <!-- Main Input Container -->
        <div
          class="relative flex flex-col rounded-3xl border bg-card/95 shadow-md transition-shadow focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary/50">
          <textarea v-model="inputPrompt" rows="2" placeholder="詢問植生指標公式（如 VARI, GLI, NDVI）、田間藥效評估，或附帶航拍照片發起縫合..."
            class="w-full resize-none bg-transparent px-4 pt-3.5 pb-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
            :disabled="status === 'streaming' || isUploadingOdm" @keydown="onKeydown"></textarea>

          <!-- Input Footer Toolbar -->
          <div class="flex items-center justify-between px-3 pb-2.5 pt-1">
            <div class="flex items-center gap-1.5">
              <!-- Hidden File Input -->
              <input ref="fileInputRef" type="file" multiple accept=".jpg,.jpeg,.png" class="hidden"
                @change="onFilesSelected" />
              <Button type="button" variant="ghost" size="sm"
                class="h-8 rounded-full px-2.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted"
                :disabled="status === 'streaming' || isUploadingOdm" @click="triggerFileInput">
                <Upload class="mr-1.5 size-3.5" />
                上傳航拍影像
              </Button>

              <Badge v-if="selectedFiles.length > 0" variant="secondary" class="h-6 text-[11px]">
                {{ selectedFiles.length }} 張圖片待處理
              </Badge>
            </div>

            <div class="flex items-center gap-2">
              <span v-if="isUploadingOdm" class="text-xs text-muted-foreground flex items-center gap-1">
                <Spinner class="size-3 animate-spin" /> 上傳縫合中...
              </span>
              <span v-else-if="status === 'streaming'" class="text-xs text-muted-foreground flex items-center gap-1">
                <Spinner class="size-3 animate-spin" /> 回覆生成中...
              </span>

              <Button type="button" size="sm" class="size-8 rounded-full p-0 shadow-xs"
                :disabled="(!inputPrompt.trim() && selectedFiles.length === 0) || status === 'streaming' || isUploadingOdm"
                @click="handleSend">
                <ArrowUp class="size-4" />
              </Button>
            </div>
          </div>
        </div>

        <p class="mt-2 text-center text-[11px] text-muted-foreground">
          AI 代理人可透過 Function Calling 自動查詢植生指標公式與波段規範。
        </p>
      </div>
    </div>
  </div>
</template>
