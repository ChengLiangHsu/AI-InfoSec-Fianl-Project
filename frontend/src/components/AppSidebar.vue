<script setup lang="ts">
import type { SidebarProps } from "@/components/ui/sidebar"
import { Command, FolderKanban, Plus } from "@lucide/vue"
import { h, ref, defineModel } from "vue"
import NavUser from "@/components/NavUser.vue"
import { Button } from "@/components/ui/button"
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

const selectedProject = defineModel()

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
  projects: [
    {
      name: "20261017",
      email: "williamsmith@example.com",
      subject: "Meeting Tomorrow",
      date: "09:34 AM",
      teaser:
        "Hi team, just a reminder about our meeting tomorrow at 10 AM.\nPlease come prepared with your project updates.",
    },
    {
      name: "Alice Smith",
      email: "alicesmith@example.com",
      subject: "Re: Project Update",
      date: "Yesterday",
      teaser:
        "Thanks for the update. The progress looks great so far.\nLet's schedule a call to discuss the next steps.",
    }
  ],
}

const activeItem = ref(data.navMain[0]!)
const projects = ref(data.projects)
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

                    const project = data.projects.sort(() => Math.random() - 0.5)
                    projects = project.slice(0, Math.max(5, Math.floor(Math.random() * 10) + 1))
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
            <a v-for="project in projects" :key="project.email" @click="selectedProject = project.name"
              class="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground flex flex-col items-start gap-2 border-b p-4 text-sm leading-tight whitespace-nowrap last:border-b-0">
              <div class="flex w-full items-center gap-2">
                <span>{{ project.name }}</span>
                <span class="ml-auto text-xs">{{ project.date }}</span>
              </div>
              <span class="font-medium">{{ project.subject }}</span>
              <span class="line-clamp-2 w-[260px] whitespace-break-spaces text-xs">
                {{ project.teaser }}
              </span>
            </a>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  </Sidebar>
</template>
