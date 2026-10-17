<script lang="ts">
export const description = "Collapsible nested sidebars."
export const iframeHeight = "800px"
</script>

<script setup lang="ts">
import { MessageCircleIcon, MinusIcon, FileCodeIcon, XIcon, Plus, Upload, ImageIcon } from '@lucide/vue'
import AppSidebar from "@/components/AppSidebar.vue"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import {
  Attachment,
  AttachmentContent,
  AttachmentDescription,
  AttachmentGroup,
  AttachmentMedia,
  AttachmentTitle,
} from '@/components/ui/attachment'
import { Separator } from "@/components/ui/separator"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ref, watch } from 'vue'
import AskAgent from './components/AskAgent.vue'
import exifr from 'exifr'
interface UploadItem {
  name: string
  size: string
  state: 'idle' | 'uploading' | 'done' | 'error'
  latitude: number
  longitude: number
}
const uploadList = ref<UploadItem[]>([])
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
const isAgentOpen = ref(true)
const selectedProject = ref()

watch(selectedProject, () => {
  uploadList.value = []
})

</script>

<template>
  <SidebarProvider :style="{
    '--sidebar-width': '350px',
  }">
    <AppSidebar v-model="selectedProject" />
    <SidebarInset v-if="selectedProject">
      <header class="bg-background sticky top-0 flex shrink-0 items-center gap-2 border-b p-4">
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
              <BreadcrumbLink href="#">
                {{ selectedProject }}
              </BreadcrumbLink>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </header>
      <div class="mx-auto flex w-full max-w-sm flex-col gap-3 py-12">
        {{ selectedProject }}
      </div>
    </SidebarInset>
    <div v-else class="mx-auto flex w-full max-w-sm flex-col gap-3 py-12">
      <Label for="picture">Picture</Label>
      <Input ref="pictureInput" type="file" multiple accept=".jpg, .jpeg, .png" @change="handleFileUpload" />
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
