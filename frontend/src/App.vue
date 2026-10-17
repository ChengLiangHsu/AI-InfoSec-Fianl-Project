<script lang="ts">
export const description = "Collapsible nested sidebars."
export const iframeHeight = "800px"
</script>

<script setup lang="ts">
import { MessageCircleIcon, MinusIcon, FileCodeIcon, XIcon, Plus } from '@lucide/vue'
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
  AttachmentAction,
  AttachmentActions,
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
import { ref } from 'vue'
import AskAgent from './components/AskAgent.vue'
const images = [
  {
    name: 'workspace.png',
    meta: 'PNG · 820 KB',
    src: 'https://images.unsplash.com/photo-1497366754035-f200968a6e72?w=900&auto=format&fit=crop&q=80',
    alt: 'Workspace',
  },
  {
    name: 'desk-reference.jpg',
    meta: 'JPG · 1.1 MB',
    src: 'https://images.unsplash.com/photo-1497215728101-856f4ea42174?w=900&auto=format&fit=crop&q=80',
    alt: 'Desk',
  },
  {
    name: 'office-reference.jpg',
    meta: 'JPG · 940 KB',
    src: 'https://images.unsplash.com/photo-1497366811353-6870744d04b2?w=900&auto=format&fit=crop&q=80',
    alt: 'Office',
  },
]
const isAgentOpen = ref(true)
const selectedProject = ref()
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
      <Input id="picture" type="file" multiple />
      <AttachmentGroup>
        <template v-for="image in images" :key="image.name">
          <Attachment orientation="vertical">
            <AttachmentMedia variant="image">
              <img :src="image.src" :alt="image.alt">
            </AttachmentMedia>
            <AttachmentContent>
              <AttachmentTitle>{{ image.name }}</AttachmentTitle>
              <AttachmentDescription>{{ image.meta }}</AttachmentDescription>
            </AttachmentContent>
          </Attachment>
        </template>
      </AttachmentGroup>
      <Attachment state="uploading" class="w-full">
        <AttachmentMedia>
          <Spinner />
        </AttachmentMedia>
        <AttachmentContent>
          <AttachmentTitle>sales-dashboard.pdf</AttachmentTitle>
          <AttachmentDescription>Uploading · 64%</AttachmentDescription>
        </AttachmentContent>
        <AttachmentActions>
          <AttachmentAction aria-label="Cancel upload">
            <XIcon />
          </AttachmentAction>
        </AttachmentActions>
      </Attachment>
      <Attachment class="w-full">
        <AttachmentMedia>
          <FileCodeIcon />
        </AttachmentMedia>
        <AttachmentContent>
          <AttachmentTitle>message-renderer.vue</AttachmentTitle>
          <AttachmentDescription>TypeScript · 12 KB</AttachmentDescription>
        </AttachmentContent>
        <AttachmentActions>
          <AttachmentAction aria-label="Remove message-renderer.vue">
            <XIcon />
          </AttachmentAction>
        </AttachmentActions>
      </Attachment>
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
