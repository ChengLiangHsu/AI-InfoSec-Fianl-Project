<script lang="ts">
export const description = "Collapsible nested sidebars."
export const iframeHeight = "800px"
</script>

<script setup lang="ts">
import { MessageCircleIcon, MinusIcon, FileCodeIcon, XIcon, Plus, Upload, ImageIcon, Clock, Images, CheckCircle2 } from '@lucide/vue'
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
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { computed, onMounted, ref, watch } from 'vue'
import AskAgent from './components/AskAgent.vue'
import exifr from 'exifr'

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
    selectedProject.value = null
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
              <BreadcrumbLink href="#">
                專案
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
              <CardDescription>拼接完成的空拍高解析度影像</CardDescription>
            </div>
            <div class="flex items-center gap-2">
              <Select v-model="selectedFormula">
                <SelectTrigger class="w-[200px]">
                  <SelectValue placeholder="選擇光譜影像" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="rgb">
                      原始正射影像 (RGB)
                    </SelectItem>
                    <SelectItem v-for="f in formulas" :key="f.id" :value="f.id">
                      {{ f.id }}
                    </SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent class="p-4">
            <div
              class="relative flex min-h-[300px] w-full items-center justify-center overflow-hidden rounded-lg border bg-muted/20 p-2">
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
      <div v-if="!selectedProject" class="mx-auto flex w-full max-w-sm flex-col gap-3 py-12">
        <form @submit.prevent="hadleCreateProject" class="flex flex-col gap-5">
          <FormField name="files">
            <FormItem>
              <FormLabel>上傳圖片</FormLabel>
              <FormControl>
                <Input ref="pictureInput" name="files" type="file" multiple accept=".jpg, .jpeg, .png"
                  @change="handleFileUpload" :disabled="isCreatingProject" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>
          <FormField name="name">
            <FormItem>
              <FormLabel>專案名稱</FormLabel>
              <FormControl>
                <Input name="name" type="text" :disabled="isCreatingProject" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>
          <Button type="submit" size="sm" variant="outline" :disabled="isCreatingProject">
            <Spinner class="animate-spin" v-if="isCreatingProject" />
            創建專案
          </Button>
        </form>
        <AttachmentGroup class="grid grid-cols-3 gap-3 max-h-105 overflow-y-auto p-1">
          <template v-for="image in uploadList" :key="image.name">
            <Attachment orientation="vertical">
              <AttachmentMedia variant="icon">
                <ImageIcon class="size-6 text-muted-foreground" />
              </AttachmentMedia>
              <AttachmentContent>
                <AttachmentTitle>{{ image.name }}</AttachmentTitle>
                <AttachmentDescription>檔案大小：{{ image.size }}</AttachmentDescription>
                <AttachmentDescription>緯度：{{ image.latitude }}</AttachmentDescription>
                <AttachmentDescription>經度：{{ image.longitude }}</AttachmentDescription>
              </AttachmentContent>
            </Attachment>
          </template>
        </AttachmentGroup>
      </div>
    </SidebarInset>
  </SidebarProvider>
  <section v-show="isAgentOpen" id="ask-agent-window" aria-labelledby="ask-agent-title"
    class="fixed bottom-4 right-4 z-40 flex h-[600px] max-h-[calc(100dvh-2rem)] w-[420px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border bg-background text-foreground shadow-xl">
    <header class="flex shrink-0 items-center justify-between border-b px-4 py-3">
      <h2 id="ask-agent-title" class="font-semibold">AskAgent</h2>
      <button type="button" aria-label="收合 AskAgent" aria-controls="ask-agent-window" :aria-expanded="isAgentOpen"
        class="inline-flex size-8 items-center justify-center rounded-md hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
        @click="isAgentOpen = false">
        <MinusIcon class="size-4" />
      </button>
    </header>
    <AskAgent />
  </section>

  <button v-if="!isAgentOpen" type="button" aria-label="開啟 AskAgent" aria-controls="ask-agent-window"
    :aria-expanded="isAgentOpen"
    class="fixed bottom-4 right-4 z-40 inline-flex size-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg hover:opacity-90 focus-visible:outline-2 focus-visible:outline-ring"
    @click="isAgentOpen = true">
    <MessageCircleIcon class="size-6" />
  </button>
</template>
