<script setup lang="ts">
import type { SidebarProps } from "@/components/ui/sidebar"
import { Clock, Command, FolderKanban, Images, Plus } from "@lucide/vue"
import { h, ref, defineModel } from "vue"
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
  useSidebar,
} from "@/components/ui/sidebar"

const props = withDefaults(defineProps<SidebarProps>(), {
  collapsible: "icon",
})

const selectedProject = defineModel("selectedProject")
const projects = defineModel("projects")

const data = {
  user: {
    name: "shadcn",
    email: "m@example.com",
    avatar: "/avatars/shadcn.jpg",
  },
  navMain: [
    {
      title: "專案",
      url: "#",
      icon: FolderKanban,
      isActive: true,
    }
  ],
}

const activeItem = ref(data.navMain[0]!)
const { setOpen } = useSidebar()
</script>

<template>
  <Sidebar class="overflow-hidden *:data-[sidebar=sidebar]:flex-row" v-bind="props">
    <Sidebar collapsible="none" class="w-[calc(var(--sidebar-width-icon)+1px)]! border-r">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" as-child class="md:h-8 md:p-0">
              <a href="#">
                <div
                  class="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                  <Command class="size-4" />
                </div>
                <div class="grid flex-1 text-left text-sm leading-tight">
                  <span class="truncate font-medium">Acme Inc</span>
                  <span class="truncate text-xs">Enterprise</span>
                </div>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent class="px-1.5 md:px-0">
            <SidebarMenu>
              <SidebarMenuItem v-for="item in data.navMain" :key="item.title">
                <SidebarMenuButton :tooltip="h('div', { hidden: false }, item.title)"
                  :is-active="activeItem.title === item.title" class="px-2.5 md:px-2" @click="() => {
                    activeItem = item
                    setOpen(true)
                  }">
                  <component :is="item.icon" />
                  <span>{{ item.title }}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <NavUser :user="data.user" />
      </SidebarFooter>
    </Sidebar>
    <Sidebar collapsible="none" class="hidden flex-1 md:flex">
      <SidebarHeader class="gap-3.5 border-b p-4">
        <div class="flex w-full items-center justify-between">
          <div class="text-base font-medium text-foreground">
            {{ activeItem.title }}
          </div>
          <Button type="button" size="sm" @click="selectedProject = ''">
            <Plus />
          </Button>
        </div>
        <SidebarInput placeholder="Type to search..." />
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup class="px-0">
          <SidebarGroupContent>
            <a v-for="project in projects" :key="project.id" @click="selectedProject = project"
              class="cursor-pointer flex flex-col gap-1.5 border-b border-l-2 p-3 text-sm transition-colors last:border-b-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              :class="selectedProject?.id === project.id
                ? 'bg-sidebar-accent text-sidebar-accent-foreground border-l-primary'
                : 'border-l-transparent text-muted-foreground'">
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
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  </Sidebar>
</template>
