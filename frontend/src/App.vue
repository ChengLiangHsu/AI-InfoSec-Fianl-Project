<script setup lang="ts">
import { MessageCircleIcon, MinusIcon } from '@lucide/vue'
import { ref } from 'vue'
import AskAgent from './components/AskAgent.vue'

const isAgentOpen = ref(true)
</script>

<template>
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
