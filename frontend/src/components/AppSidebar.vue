<script setup lang="ts">
import type { SidebarProps } from "@/components/ui/sidebar"
import { Clock, Command, Images, Plus } from "@lucide/vue"
import { computed, defineModel, ref } from "vue"
import NavUser from "@/components/NavUser.vue"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarInput,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { useChatAgent } from "@/lib/useChatAgent"

const props = withDefaults(defineProps<SidebarProps>(), {
  collapsible: "icon",
})

const isCreatingProject = defineModel("isCreatingProject")
const processingProject = defineModel("processingProject")
const selectedProject = defineModel("selectedProject")
const projects = defineModel<any[]>("projects")

const { clearChat } = useChatAgent()

async function handleGoHome() {
  selectedProject.value = null
  await clearChat('home')
}

const searchQuery = ref("")

const filteredProjects = computed(() => {
  const list = (projects.value as any[]) || []
  if (!searchQuery.value.trim()) return list
  const query = searchQuery.value.toLowerCase().trim()
  return list.filter(
    (p: any) =>
      p.name?.toLowerCase().includes(query) ||
      p.id?.toLowerCase().includes(query)
  )
})

const data = {
  user: {
    name: "shadcn",
    email: "m@example.com",
    avatar: "/avatars/shadcn.jpg",
  },
}
</script>

<template>
  <Sidebar v-bind="props">
    <SidebarHeader class="gap-3.5 border-b p-4">
      <div class="flex items-center justify-between">
        <SidebarMenu class="flex-1">
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" as-child class="h-9 p-1">
              <a href="#" @click.prevent="handleGoHome" class="flex items-center gap-2">
                <div
                  class="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                  <Command class="size-4" />
                </div>
                <div class="grid flex-1 text-left text-sm leading-tight">
                  <span class="truncate font-semibold">Acme Inc</span>
                  <span class="truncate text-xs text-muted-foreground">航拍影像分析平台</span>
                </div>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
        <Button
          type="button"
          size="icon"
          variant="ghost"
          class="size-8 shrink-0 text-muted-foreground hover:text-foreground"
          title="回到主畫面並清空對話"
          @click="handleGoHome"
        >
          <Plus class="size-4" />
        </Button>
      </div>
      <SidebarInput v-model="searchQuery" placeholder="Type to search..." />
    </SidebarHeader>

    <SidebarContent>
      <SidebarGroup class="px-0">
        <SidebarGroupContent>
          <a
            v-for="project in filteredProjects"
            :key="project.id"
            @click="selectedProject = project"
            :disabled="isCreatingProject === true"
            class="cursor-pointer flex flex-col gap-1.5 border-b border-l-2 p-3 text-sm transition-colors last:border-b-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            :class="selectedProject?.id === project.id
              ? 'bg-sidebar-accent text-sidebar-accent-foreground border-l-primary'
              : 'border-l-transparent text-muted-foreground'"
          >
            <div class="flex w-full items-center justify-between gap-2">
              <span class="font-medium text-foreground truncate">{{ project.name }}</span>
              <Badge v-if="project.status" variant="secondary" class="text-[10px] px-1.5 py-0 h-4 shrink-0">
                {{ project.status }}
              </Badge>
            </div>
            <div class="text-xs text-muted-foreground font-mono truncate w-full">
              ID: {{ project.id }}
            </div>
            <div class="flex w-full items-center justify-between text-xs text-muted-foreground pt-0.5">
              <span class="flex items-center gap-1">
                <Images class="size-3.5" />
                {{ project.images ?? 0 }} 張
              </span>
              <span v-if="project.timeElapsed" class="flex items-center gap-1">
                <Clock class="size-3.5" />
                {{ project.timeElapsed }}
              </span>
            </div>
          </a>
          <div v-if="filteredProjects.length === 0" class="p-6 text-center text-xs text-muted-foreground">
            尚無專案
          </div>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>

    <SidebarFooter class="border-t p-2">
      <NavUser :user="data.user" />
    </SidebarFooter>
  </Sidebar>
</template>
