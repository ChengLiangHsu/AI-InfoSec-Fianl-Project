<script setup lang="ts">
import { computed } from 'vue'

interface StepMeta {
  num: number
  title: string
  badgeBg: string
  pillBorder: string
  pillBg: string
  pillText: string
}

const STEP_METAS: Record<number, StepMeta> = {
  1: {
    num: 1,
    title: '航拍上傳',
    badgeBg: 'bg-blue-600 text-white',
    pillBorder: 'border-blue-500/40',
    pillBg: 'bg-blue-500/10 dark:bg-blue-950/40',
    pillText: 'text-blue-600 dark:text-blue-400',
  },
  2: {
    num: 2,
    title: '正射拼接',
    badgeBg: 'bg-purple-600 text-white',
    pillBorder: 'border-purple-500/40',
    pillBg: 'bg-purple-500/10 dark:bg-purple-950/40',
    pillText: 'text-purple-600 dark:text-purple-300',
  },
  3: {
    num: 3,
    title: '試驗情境',
    badgeBg: 'bg-amber-600 text-white',
    pillBorder: 'border-amber-500/40',
    pillBg: 'bg-amber-500/10 dark:bg-amber-950/40',
    pillText: 'text-amber-600 dark:text-amber-400',
  },
  4: {
    num: 4,
    title: '植生指標',
    badgeBg: 'bg-cyan-600 text-white',
    pillBorder: 'border-cyan-500/40',
    pillBg: 'bg-cyan-500/10 dark:bg-cyan-950/40',
    pillText: 'text-cyan-600 dark:text-cyan-400',
  },
  5: {
    num: 5,
    title: '小區標註',
    badgeBg: 'bg-emerald-600 text-white',
    pillBorder: 'border-emerald-500/40',
    pillBg: 'bg-emerald-500/10 dark:bg-emerald-950/40',
    pillText: 'text-emerald-600 dark:text-emerald-400',
  },
  6: {
    num: 6,
    title: '處理對照',
    badgeBg: 'bg-rose-600 text-white',
    pillBorder: 'border-rose-500/40',
    pillBg: 'bg-rose-500/10 dark:bg-rose-950/40',
    pillText: 'text-rose-600 dark:text-rose-400',
  },
  7: {
    num: 7,
    title: '藥效評估',
    badgeBg: 'bg-yellow-600 text-white',
    pillBorder: 'border-yellow-500/40',
    pillBg: 'bg-yellow-500/10 dark:bg-yellow-950/40',
    pillText: 'text-yellow-600 dark:text-yellow-400',
  },
}

const props = defineProps<{
  text?: string
}>()

interface TextSegment {
  isStep: boolean
  content: string
  meta?: StepMeta
}

const segments = computed<TextSegment[]>(() => {
  const raw = props.text || ''
  if (!raw) return []

  // 匹配 【步驟 X：名稱】 或 步驟 X：名稱 或 步驟 X
  const regex = /(?:【)?(步驟\s*([1-7])(?:[：:\s/]+([^\n】]+?))?)(?:】)?/g
  const res: TextSegment[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(raw)) !== null) {
    if (match.index > lastIndex) {
      res.push({
        isStep: false,
        content: raw.slice(lastIndex, match.index),
      })
    }

    const stepNum = parseInt(match[2], 10)
    const customTitle = match[3]?.trim()
    const baseMeta = STEP_METAS[stepNum] || STEP_METAS[1]
    const meta: StepMeta = {
      ...baseMeta,
      title: customTitle || baseMeta.title,
    }

    res.push({
      isStep: true,
      content: match[0],
      meta,
    })

    lastIndex = regex.lastIndex
  }

  if (lastIndex < raw.length) {
    res.push({
      isStep: false,
      content: raw.slice(lastIndex),
    })
  }

  return res
})
</script>

<template>
  <span class="inline leading-relaxed">
    <template v-for="(seg, idx) in segments" :key="idx">
      <span
        v-if="seg.isStep && seg.meta"
        class="mx-1 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-bold align-middle shadow-2xs transition-transform hover:scale-105 select-none"
        :class="[seg.meta.pillBg, seg.meta.pillBorder, seg.meta.pillText]"
      >
        <span
          class="flex size-4.5 items-center justify-center rounded-full text-[11px] font-extrabold shrink-0 shadow-xs"
          :class="seg.meta.badgeBg"
        >
          {{ seg.meta.num }}
        </span>
        <span class="tracking-wide">步驟 {{ seg.meta.num }}：{{ seg.meta.title }}</span>
      </span>
      <span v-else class="whitespace-pre-wrap">{{ seg.content }}</span>
    </template>
  </span>
</template>
