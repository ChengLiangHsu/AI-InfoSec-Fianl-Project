<script setup lang="ts">
import type { ProgressRootProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { cn } from "cn"
import {
  ProgressIndicator,
  ProgressRoot,
} from "reka-ui"

const props = withDefaults(
  defineProps<ProgressRootProps & { class?: HTMLAttributes["class"] }>(),
  {
    modelValue: 0,
  },
)

const delegatedProps = reactiveOmit(props, "class")
</script>

<template>
  <ProgressRoot data-slot="progress" v-bind="delegatedProps" :class="cn(
    'relative h-2 w-full overflow-hidden rounded-full border border-gray-300',
    props.class,
  )
    ">
    <ProgressIndicator data-slot="progress-indicator" class="h-full w-full flex-1 transition-all"
      :class="props.modelValue === 100 ? 'bg-green-800' : 'bg-blue-600'" :style="`transform: translateX(-${100 -
        (props.modelValue ?? 0)}%);`" />
  </ProgressRoot>
</template>
