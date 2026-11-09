<script setup lang="ts">
import type { ChatStatus } from 'ai'
import type { HTMLAttributes } from 'vue'
import { CornerDownLeftIcon, Loader2Icon, XIcon } from '@lucide/vue'
import { InputGroupButton } from '@/components/ui/input-group'
import { cn } from '@/lib/utils'
import { computed } from 'vue'

type InputGroupButtonProps = InstanceType<typeof InputGroupButton>['$props']

interface Props extends /* @vue-ignore */ InputGroupButtonProps {
  class?: HTMLAttributes['class']
  status?: ChatStatus
  variant?: InputGroupButtonProps['variant']
  size?: InputGroupButtonProps['size']
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  size: 'icon-sm',
  disabled: false,
})

const isThinking = computed(() => props.status === 'submitted' || props.status === 'streaming')
const isDisabled = computed(() => props.disabled || isThinking.value)

const icon = computed(() => {
  if (isThinking.value) {
    return Loader2Icon
  }
  else if (props.status === 'error') {
    return XIcon
  }
  return CornerDownLeftIcon
})

const iconClass = computed(() => {
  if (isThinking.value) {
    return 'size-4 animate-spin'
  }
  return 'size-4'
})
</script>

<template>
  <InputGroupButton
    aria-label="Submit"
    :class="cn('disabled:cursor-not-allowed', props.class)"
    :size="props.size"
    :variant="props.variant"
    :disabled="isDisabled"
    type="submit"
  >
    <slot>
      <component :is="icon" :class="iconClass" />
    </slot>
  </InputGroupButton>
</template>
