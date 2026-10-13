<script lang="ts">
export const description = "Collapsible nested sidebars."
export const iframeHeight = "800px"
</script>

<script setup lang="ts">
import { MessageCircleIcon, MinusIcon } from '@lucide/vue'
import AppSidebar from "@/components/AppSidebar.vue"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Separator } from "@/components/ui/separator"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { onBeforeUnmount, ref } from 'vue'
import AskAgent from './components/AskAgent.vue'

const isAgentOpen = ref(true)
type SelectedImage = {
  file: File
  url: string
  failed: boolean
}

const images = ref<SelectedImage[]>([])
const imageError = ref('')

function clearImages() {
  images.value.forEach(image => URL.revokeObjectURL(image.url))
  images.value = []
  imageError.value = ''
}

function removeImage(url: string) {
  URL.revokeObjectURL(url)
  images.value = images.value.filter(image => image.url !== url)
}

function selectImages(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''
  if (!files.length)
    return

  imageError.value = ''
  let rejected = 0
  for (const file of files) {
    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      rejected += 1
      continue
    }
    if (images.value.some(image =>
      image.file.name === file.name
      && image.file.size === file.size
      && image.file.lastModified === file.lastModified,
    ))
      continue

    images.value.push({ file, url: URL.createObjectURL(file), failed: false })
  }
  if (rejected)
    imageError.value = `已略過 ${rejected} 個不支援的檔案，僅接受 JPG／PNG 圖片。`
}

function handleImageError(image: SelectedImage) {
  image.failed = true
  URL.revokeObjectURL(image.url)
}

onBeforeUnmount(clearImages)
</script>

<template>
    <SidebarProvider
    :style="{
      '--sidebar-width': '350px',
    }"
  >
    <AppSidebar />
    <SidebarInset>
      <header class="bg-background sticky top-0 flex shrink-0 items-center gap-2 border-b p-4">
        <SidebarTrigger class="-ml-1" />
        <Separator
          orientation="vertical"
          class="mr-2 data-[orientation=vertical]:h-4"
        />
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem class="hidden md:block">
              <BreadcrumbLink href="#">
                田間試驗
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator class="hidden md:block" />
            <BreadcrumbItem>
              <BreadcrumbPage>影像預覽</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </header>
      <div class="flex flex-1 flex-col gap-4 p-4">
        <section aria-labelledby="field-image-title" class="min-w-0 rounded-xl border p-4">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 id="field-image-title" class="text-lg font-semibold">田間影像</h1>
              <p id="field-image-help" class="mt-1 text-sm text-muted-foreground">
                可分批加入多張 JPG／PNG 航拍照片，重複選取的照片會略過。目前僅本機預覽，尚未上傳或拼接。
              </p>
            </div>
            <button
              v-if="images.length"
              type="button"
              class="rounded-md border px-3 py-2 text-sm hover:bg-muted"
              @click="clearImages"
            >
              清空照片
            </button>
          </div>
          <label for="field-image-input" class="mt-4 block text-sm font-medium">選擇田間圖片</label>
          <input
            id="field-image-input"
            type="file"
            multiple
            accept="image/jpeg,image/png"
            aria-describedby="field-image-help field-image-error"
            class="mt-2 block w-full min-w-0 text-sm file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-primary file:px-4 file:py-2 file:text-primary-foreground"
            @change="selectImages"
          >
          <p id="field-image-error" role="alert" class="mt-2 text-sm text-destructive">{{ imageError }}</p>
          <p class="mt-2 text-sm text-muted-foreground" role="status">已選取 {{ images.length }} 張照片</p>
          <div v-if="images.length" class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <figure v-for="image in images" :key="image.url" class="min-w-0 overflow-hidden rounded-lg border">
              <p v-if="image.failed" role="alert" class="flex h-40 items-center justify-center bg-muted/30 p-4 text-sm text-destructive">
                無法讀取圖片，請移除後重新選擇完整檔案。
              </p>
              <img
                v-else
                :src="image.url"
                :alt="`田間影像：${image.file.name}`"
                loading="lazy"
                class="h-40 w-full bg-muted/30 object-contain"
                @error="handleImageError(image)"
              >
              <figcaption class="flex items-start justify-between gap-2 p-3">
                <span class="min-w-0 break-all text-sm">{{ image.file.name }}</span>
                <button
                  type="button"
                  :aria-label="`移除 ${image.file.name}`"
                  class="shrink-0 rounded-md border px-2 py-1 text-sm hover:bg-muted"
                  @click="removeImage(image.url)"
                >
                  移除
                </button>
              </figcaption>
            </figure>
          </div>
          <div v-else class="mt-4 flex min-h-64 items-center justify-center rounded-lg border border-dashed bg-muted/30 p-6 text-center text-sm text-muted-foreground">
            尚未選擇照片，請選取同一田區的多張航拍照片。
          </div>
        </section>
      </div>
    </SidebarInset>
  </SidebarProvider>
  <section
    v-show="isAgentOpen"
    id="ask-agent-window"
    aria-labelledby="ask-agent-title"
    class="fixed bottom-4 right-4 z-40 flex h-[600px] max-h-[calc(100dvh-2rem)] w-[420px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border bg-background text-foreground shadow-xl"
  >
    <header class="flex shrink-0 items-center justify-between border-b px-4 py-3">
      <h2 id="ask-agent-title" class="font-semibold">AskAgent</h2>
      <button
        type="button"
        aria-label="收合 AskAgent"
        aria-controls="ask-agent-window"
        :aria-expanded="isAgentOpen"
        class="inline-flex size-8 items-center justify-center rounded-md hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
        @click="isAgentOpen = false"
      >
        <MinusIcon class="size-4" />
      </button>
    </header>
    <div class="min-h-0 flex-1 overflow-auto">
      <AskAgent />
    </div>
  </section>

  <button
    v-if="!isAgentOpen"
    type="button"
    aria-label="開啟 AskAgent"
    aria-controls="ask-agent-window"
    :aria-expanded="isAgentOpen"
    class="fixed bottom-4 right-4 z-40 inline-flex size-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg hover:opacity-90 focus-visible:outline-2 focus-visible:outline-ring"
    @click="isAgentOpen = true"
  >
    <MessageCircleIcon class="size-6" />
  </button>
</template>
