<script lang="ts">
export const description = "Collapsible nested sidebars."
export const iframeHeight = "800px"
</script>
<script setup lang="ts">
import { MessageCircleIcon, MinusIcon, FileCodeIcon, XIcon, Plus, Upload, ImageIcon, Clock, Images, CheckCircle2, Layers, Trash2, Sparkles } from '@lucide/vue'
import AppSidebar from "@/components/AppSidebar.vue"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  Attachment,
  AttachmentContent,
  AttachmentDescription,
  AttachmentGroup,
  AttachmentMedia,
  AttachmentTitle,
} from '@/components/ui/attachment'
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { computed, onMounted, ref, watch } from 'vue'
import AskAgent from './components/AskAgent.vue'
import GeminiHomeChat from './components/GeminiHomeChat.vue'
import { useChatAgent } from './lib/useChatAgent'
import exifr from 'exifr'

const { clearChat } = useChatAgent()

async function handleGoHome() {
  selectedProject.value = null
  await clearChat('home')
}

async function handleClearAgentChat() {
  if (selectedProject.value?.id) {
    await clearChat(selectedProject.value.id)
  }
}

interface Formula {
  id: string
  expr: string
  help?: string
  range?: [number, number]
}

interface UploadItem {
  name: string
  size: string
  state: 'idle' | 'uploading' | 'done' | 'error'
  latitude: number
  longitude: number
}

interface Project {
  id: string
  name: string
  images?: number
  progress?: number
}

const projects = ref<Project[]>([])
const selectedProject = ref<Project | null>(null)
const processingProject = ref<Project | null>(null)
const uploadList = ref<UploadItem[]>([])
const isCreatingProject = ref(false)
const isAgentOpen = ref(true)
const formulas = ref<Formula[]>([])
const selectedFormula = ref<string>('rgb')
const isImageLoading = ref(false)

const currentImageUrl = computed(() => {
  if (!selectedProject.value) return ''
  if (selectedFormula.value === 'rgb') {
    return `/api/odm-task-orthophoto/${selectedProject.value.id}`
  }
  return `/api/odm-task-spectral/${selectedProject.value.id}?formula=${selectedFormula.value}`
})

watch(selectedFormula, () => {
  isImageLoading.value = true
})
async function handleFileUpload(event: Event) {
  uploadList.value = []
  if (event) {
    const fileList = event.target?.files;
    for (const file of fileList) {
      const gps = await exifr.gps(file)
      if (!gps) {
        alert(`${file.name} 沒有GPS資訊`)
        event.target.value = '';
        break;
      }
      uploadList.value.push({
        name: file.name,
        size: (file.size / 1024 / 1024).toFixed(2) + 'MB',
        state: 'idle',
        latitude: gps.latitude,
        longitude: gps.longitude
      })
    }
  }
}
async function hadleCreateProject(event: Event) {
  if (uploadList.value.length === 0) {
    alert("請先上傳檔案")
    return
  }
  const formData = new FormData(event.target)
  isCreatingProject.value = true
  const response = await fetch("/api/odm-task", {
    method: "POST",
    body: formData,
  });
  const data = await response.json();
  if (!response.ok) {
    alert("建立專案失敗")
    isCreatingProject.value = false
    return
  }
  projects.value = await fetch("/api/odm-task-list").then((res) => res.json()).then((res) => res.data)
  selectedProject.value = projects.value.find((project) => project.id === data.data["id"])
  processingProject.value = selectedProject.value || null
  const timer = setInterval(async () => {
    const res = await fetch(`/api/odm-task-info/${data.data["id"]}`)
    const resData = await res.json()
    processingProject.value.progress = resData.data.progress
    if (resData.data.progress === 100) {
      clearInterval(timer)
      isCreatingProject.value = false
    }
  }, 2000)
}

async function onProjectCreated(newProj: Project) {
  try {
    const listRes = await fetch("/api/odm-task-list")
    const listData = await listRes.json()
    if (listRes.ok && listData.data) {
      projects.value = listData.data
    }
  } catch (err) {
    console.error("無法更新專案清單", err)
  }

  const found = projects.value.find((p) => p.id === newProj.id) || newProj
  selectedProject.value = found
  processingProject.value = found

  const timer = setInterval(async () => {
    try {
      const res = await fetch(`/api/odm-task-info/${newProj.id}`)
      const resData = await res.json()
      if (resData.data) {
        if (selectedProject.value?.id === newProj.id) {
          selectedProject.value.progress = resData.data.progress
        }
        if (processingProject.value?.id === newProj.id) {
          processingProject.value.progress = resData.data.progress
        }
        if (resData.data.progress === 100) {
          clearInterval(timer)
        }
      }
    } catch {
      clearInterval(timer)
    }
  }, 2000)
}


async function handleDeleteProject(id: string) {
  if (!confirm("確定要刪除此專案嗎？")) return
  const response = await fetch(`/api/odm-task/${id}`, {
    method: "DELETE",
  })
  if (!response.ok) {
    alert("刪除專案失敗")
    return
  }
  projects.value = projects.value.filter((p) => p.id !== id)
  if (selectedProject.value?.id === id) {
    await handleGoHome()
  }
}

onMounted(async () => {
  try {
    const formulasRes = await fetch("/api/odm-task-formulas")
    const formulasData = await formulasRes.json()
    if (formulasRes.ok && formulasData.data) {
      formulas.value = formulasData.data
    }
  } catch (err) {
    console.error("無法取得光譜演算法清單", err)
  }

  const response = await fetch("/api/odm-task-list")
  const data = await response.json()
  if (!response.ok) {
    return
  }
  projects.value = data.data
  processingProject.value = projects.value.find((p) => p.progress !== 100) || null
  if (processingProject.value) {
    const timer = setInterval(async () => {
      const res = await fetch(`/api/odm-task-info/${processingProject.value?.id}`)
      const resData = await res.json()
      processingProject.value.progress = resData.data.progress
      if (resData.data.progress === 100) {
        clearInterval(timer)
      }
    }, 2000)
  }
})

watch(selectedProject, () => {
  uploadList.value = []
  selectedFormula.value = 'rgb'
  isImageLoading.value = true
})

</script>

<template>
  <SidebarProvider :style="{
    '--sidebar-width': '350px',
  }">
    <AppSidebar v-model:is-creating-project="isCreatingProject" v-model:selected-project="selectedProject"
      v-model:projects="projects" />
    <SidebarInset>
      <header v-if="selectedProject" class="bg-background sticky top-0 flex shrink-0 items-center gap-2 border-b p-4">
        <SidebarTrigger class="-ml-1" />
        <Separator orientation="vertical" class="mr-2 data-[orientation=vertical]:h-4" />
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem class="hidden md:block">
              <BreadcrumbLink href="#" class="cursor-pointer" @click.prevent="handleGoHome">
                主畫面
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator class="hidden md:block" />
            <BreadcrumbItem>
              <BreadcrumbLink>
                {{ selectedProject.name }}
              </BreadcrumbLink>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
        <Button variant="destructive" size="sm" class="ml-auto" @click="handleDeleteProject(selectedProject.id)">
          刪除專案
        </Button>
      </header>
      <div v-if="selectedProject" class="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
        <!-- 專案資訊卡片 -->
        <Card>
          <CardHeader class="pb-3">
            <div class="flex items-start justify-between gap-4">
              <div class="space-y-1">
                <CardTitle class="text-xl font-bold">{{ selectedProject.name }}</CardTitle>
                <CardDescription class="font-mono text-xs text-muted-foreground">
                  ID: {{ selectedProject.id }}
                </CardDescription>
              </div>
              <Badge :variant="selectedProject.progress === 100 ? 'default' : 'secondary'">
                <CheckCircle2 v-if="selectedProject.progress === 100" class="size-3.5 mr-1" />
                <Spinner v-else class="size-3.5 mr-1 animate-spin" />
                {{ selectedProject.progress === 100 ? '已完成' : `處理中 (${selectedProject.progress ?? 0}%)` }}
              </Badge>
            </div>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex flex-wrap items-center gap-6 text-sm text-muted-foreground">
              <div class="flex items-center gap-2">
                <Images class="size-4" />
                <span>圖片數量：<strong class="text-foreground">{{ selectedProject.images ?? 0 }}</strong> 張</span>
              </div>
              <div class="flex items-center gap-2">
                <Clock class="size-4" />
                <span>運算進度：<strong class="text-foreground">{{ selectedProject.progress ?? 0 }}%</strong></span>
              </div>
            </div>

            <!-- 處理中進度條 -->
            <div v-if="selectedProject.progress !== 100" class="space-y-2 pt-2">
              <Progress :model-value="selectedProject.progress ?? 0" />
              <p class="text-xs text-muted-foreground">正在進行航拍正射影像運算，請稍候...</p>
            </div>
          </CardContent>
        </Card>

        <!-- 正射影像成果卡片 -->
        <Card v-if="selectedProject.progress === 100">
          <CardHeader class="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle class="text-lg">正射影像成果 (Orthophoto)</CardTitle>
              <CardDescription>拼接完成的空拍高解析度影像與植生指標運算</CardDescription>
            </div>
            <div class="flex items-center gap-2">
              <Badge variant="outline" class="font-mono text-xs">
                目前顯示：{{ selectedFormula === 'rgb' ? '原始正射影像 (RGB)' : selectedFormula }}
              </Badge>
            </div>
          </CardHeader>
          <CardContent class="p-4">
            <div
              class="relative flex min-h-[360px] w-full items-center justify-center overflow-hidden rounded-lg border bg-muted/20 p-2">
              
              <!-- 懸浮公式快速切換按鈕群 (Floating Formula Switcher) -->
              <div
                class="absolute top-3 right-3 z-20 flex flex-col gap-1.5 rounded-xl border border-border/80 bg-background/85 p-1.5 shadow-lg backdrop-blur-md">
                <div class="flex items-center gap-1.5 px-2 py-1 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                  <Layers class="size-3.5" />
                  <span>光譜演算法</span>
                </div>
                <div class="flex flex-col gap-1 max-h-[320px] overflow-y-auto pr-0.5">
                  <TooltipProvider :delay-duration="150">
                    <Tooltip>
                      <TooltipTrigger as-child>
                        <Button
                          size="sm"
                          :variant="selectedFormula === 'rgb' ? 'default' : 'outline'"
                          class="h-8 justify-start gap-2 px-3 text-xs font-medium shadow-xs transition-all"
                          @click="selectedFormula = 'rgb'"
                        >
                          <span
                            class="size-2 rounded-full"
                            :class="selectedFormula === 'rgb' ? 'bg-primary-foreground' : 'bg-emerald-500'"
                          />
                          <span>RGB 原始</span>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="left" class="max-w-xs space-y-1 p-2 text-xs">
                        <p class="font-bold text-foreground">原始正射影像 (RGB)</p>
                        <p class="text-muted-foreground leading-relaxed">未經光譜指數計算之原始拼接正射影像。</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>

                  <div class="my-0.5 h-px bg-border/60" />

                  <TooltipProvider
                    v-for="f in formulas"
                    :key="f.id"
                    :delay-duration="150"
                  >
                    <Tooltip>
                      <TooltipTrigger as-child>
                        <Button
                          size="sm"
                          :variant="selectedFormula === f.id ? 'default' : 'outline'"
                          class="h-8 justify-between gap-3 px-3 text-xs font-medium shadow-xs transition-all"
                          @click="selectedFormula = f.id"
                        >
                          <span class="font-semibold">{{ f.id }}</span>
                          <span
                            v-if="selectedFormula === f.id"
                            class="size-1.5 rounded-full bg-primary-foreground animate-pulse"
                          />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="left" class="max-w-xs space-y-1 p-2 text-xs">
                        <p class="font-bold text-foreground">{{ f.id }}</p>
                        <p v-if="f.help" class="text-muted-foreground leading-relaxed">{{ f.help }}</p>
                        <p v-if="f.expr" class="font-mono text-[10px] text-muted-foreground/80 bg-muted/60 px-1.5 py-0.5 rounded">
                          公式: {{ f.expr }}
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </div>

              <!-- 影像載入中遮罩 -->
              <div v-if="isImageLoading"
                class="absolute inset-0 z-10 flex flex-col items-center justify-center bg-background/60 backdrop-blur-xs">
                <Spinner class="size-8 animate-spin text-primary" />
                <span class="mt-2 text-xs font-medium text-muted-foreground">影像載入中...</span>
              </div>
              <img
                class="max-h-[65vh] w-auto max-w-full object-contain rounded shadow-sm transition-opacity duration-200"
                :class="{ 'opacity-40': isImageLoading }" :src="currentImageUrl" :alt="selectedProject.name"
                @load="isImageLoading = false" @error="isImageLoading = false">
            </div>
          </CardContent>
        </Card>

        <!-- 運算中提示 -->
        <Card v-else class="border-dashed p-8 text-center text-muted-foreground">
          <div class="flex flex-col items-center justify-center gap-3">
            <Spinner class="size-8 animate-spin text-primary" />
            <div class="text-sm font-medium text-foreground">正射影像生成中...</div>
            <p class="text-xs text-muted-foreground">任務完成後將在此自動顯示拼接成果影像</p>
          </div>
        </Card>
      </div>
      <div v-if="!selectedProject" class="h-[calc(100vh-1rem)] w-full">
        <GeminiHomeChat @project-created="onProjectCreated" />
      </div>
    </SidebarInset>
  </SidebarProvider>
  <section v-if="selectedProject" v-show="isAgentOpen" id="ask-agent-window" aria-labelledby="ask-agent-title"
    class="fixed bottom-4 right-4 z-40 flex h-[600px] max-h-[calc(100dvh-2rem)] w-[420px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border bg-background text-foreground shadow-xl">
    <header class="flex shrink-0 items-center justify-between border-b px-3.5 py-2.5 bg-muted/20">
      <div class="flex items-center gap-2 min-w-0">
        <Sparkles class="size-4 text-primary shrink-0" />
        <h2 id="ask-agent-title" class="font-semibold text-sm truncate">AskAgent ({{ selectedProject?.name }})</h2>
      </div>
      <div class="flex items-center gap-1 shrink-0">
        <TooltipProvider :delay-duration="150">
          <Tooltip>
            <TooltipTrigger as-child>
              <button
                type="button"
                aria-label="清除對話紀錄"
                class="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-destructive focus-visible:outline-2 focus-visible:outline-ring cursor-pointer transition-colors"
                @click="handleClearAgentChat"
              >
                <Trash2 class="size-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" class="text-xs">
              清除對話紀錄
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <TooltipProvider :delay-duration="150">
          <Tooltip>
            <TooltipTrigger as-child>
              <button
                type="button"
                aria-label="收合 AskAgent"
                aria-controls="ask-agent-window"
                :aria-expanded="isAgentOpen"
                class="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring cursor-pointer transition-colors"
                @click="isAgentOpen = false"
              >
                <MinusIcon class="size-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" class="text-xs">
              收合小視窗
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </header>
    <AskAgent
      :project-id="selectedProject?.id"
      :project-name="selectedProject?.name"
      :selected-formula="selectedFormula"
    />
  </section>

  <button v-if="selectedProject && !isAgentOpen" type="button" aria-label="開啟 AskAgent" aria-controls="ask-agent-window"
    :aria-expanded="isAgentOpen"
    class="fixed bottom-4 right-4 z-40 inline-flex size-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg hover:opacity-90 focus-visible:outline-2 focus-visible:outline-ring"
    @click="isAgentOpen = true">
    <MessageCircleIcon class="size-6" />
  </button>
</template>
