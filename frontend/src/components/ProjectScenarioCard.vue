<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  Card,
  CardContent,
  CardHeader,
} from '@/components/ui/card'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import {
  FlaskConical,
  CheckCircle2,
  Plus,
  Trash2,
  ChevronDown,
  ChevronUp,
  Save,
} from '@lucide/vue'

export interface ScenarioCategoryItem {
  treatment?: string
  dose?: string
  name: string
  color: string
  is_control?: boolean
}

export interface ScenarioData {
  type: string
  title: string
  target?: string
  target_label?: string
  categories: ScenarioCategoryItem[]
}

const props = withDefaults(
  defineProps<{
    projectId?: string
    projectName?: string
    initialScenario?: ScenarioData | null
    fileNames?: string[]
    projectProgress?: number
  }>(),
  {
    initialScenario: null,
    fileNames: () => [],
    projectProgress: 0,
  }
)

const emit = defineEmits<{
  (e: 'update:scenario', scenario: ScenarioData): void
  (e: 'saved', scenario: ScenarioData): void
}>()

// 高對比識別調色盤
const PALETTE = [
  '#64748b', // 對照組灰色 (Slate)
  '#10b981', // 翡翠綠 (Emerald)
  '#8b5cf6', // 紫羅蘭 (Violet)
  '#f59e0b', // 琥珀黃 (Amber)
  '#0ea5e9', // 天空藍 (Sky)
  '#ec4899', // 亮粉紅 (Pink)
  '#f97316', // 活力橘 (Orange)
  '#06b6d4', // 湖水青 (Cyan)
  '#84cc16', // 萊姆綠 (Lime)
  '#e11d48', // 玫瑰紅 (Rose)
]

const isOpen = ref(true)
const isSaving = ref(false)
const isSaved = ref(false)
const isDirty = ref(false)

const categories = ref<ScenarioCategoryItem[]>([])

// 初始化預設組別骨架：1 個對照組 (CK) ＋ 1 個空白處理組
function initDefaultCategories() {
  categories.value = [
    { name: '未施藥對照 (CK)', treatment: '', dose: '', color: PALETTE[0], is_control: true },
    { name: '', treatment: '', dose: '', color: PALETTE[1], is_control: false },
  ]
  isDirty.value = false
}

// 新增組別
function addCategory() {
  const nextColorIdx = (categories.value.length % (PALETTE.length - 1)) + 1
  categories.value.push({
    name: '',
    treatment: '',
    dose: '',
    color: PALETTE[nextColorIdx],
    is_control: false,
  })
  isDirty.value = true
}

// 移除組別
function removeCategory(index: number) {
  categories.value.splice(index, 1)
  isDirty.value = true
}

// 切換對照組（互斥單選模式：若點選處理組，將其設為對照組並將既有對照組降級為處理組；對照組不可反轉取消）
function toggleControl(cat: ScenarioCategoryItem) {
  if (cat.is_control) {
    // 已經是對照組，禁止取消，永遠維持 1 個對照組
    return
  }
  // 將其他對照組降級為處理組
  for (const c of categories.value) {
    if (c.is_control) {
      c.is_control = false
      c.name = [c.treatment, c.dose].filter(Boolean).join(' ') || ''
    }
  }
  // 當前組別提升為對照組
  cat.is_control = true
  cat.name = cat.name.trim() || '未施藥對照 (CK)'
  cat.treatment = ''
  cat.dose = ''
  isDirty.value = true
}

// 當編輯藥劑名稱或劑量時同步組名
function onTreatmentChange(cat: ScenarioCategoryItem) {
  const trt = (cat.treatment || '').trim()
  const d = (cat.dose || '').trim()
  cat.name = [trt, d].filter(Boolean).join(' ')
  isDirty.value = true
}

// 載入已存在之情境設定（自動校正確保全域僅有唯一對照組）
function loadFromScenario(data: ScenarioData) {
  if (!data || !Array.isArray(data.categories) || data.categories.length === 0) {
    initDefaultCategories()
    return
  }
  const defaultTarget = (data.target || '').trim()
  let hasControl = false

  categories.value = data.categories.map((c, idx) => {
    let isControl = Boolean(c.is_control)
    if (isControl) {
      if (hasControl) {
        // 多餘的對照組自動降級為處理組
        isControl = false
      } else {
        hasControl = true
      }
    }
    let trt = c.treatment || ''
    let d = c.dose || ''
    let n = c.name || ''

    if (!isControl && !trt && defaultTarget) {
      trt = defaultTarget
    }
    if (!isControl && !d && n && n !== trt) {
      d = n
    }
    if (!n) {
      n = isControl ? '未施藥對照 (CK)' : [trt, d].filter(Boolean).join(' ') || `處理組 ${idx}`
    }

    return {
      name: n,
      treatment: trt,
      dose: d,
      color: c.color || PALETTE[idx % PALETTE.length],
      is_control: isControl,
    }
  })

  // 若完全沒有對照組，自動將第 1 個設為對照組
  if (!hasControl && categories.value.length > 0) {
    categories.value[0].is_control = true
    categories.value[0].name = categories.value[0].name || '未施藥對照 (CK)'
  }

  isDirty.value = false
  isSaved.value = true
}

watch(
  () => props.initialScenario,
  (newScenario) => {
    if (newScenario && typeof newScenario === 'object' && Object.keys(newScenario).length > 0) {
      loadFromScenario(newScenario as ScenarioData)
      if (props.projectProgress === 100) {
        isOpen.value = false
      }
    } else {
      initDefaultCategories()
      isOpen.value = true
    }
  },
  { immediate: true }
)

// 儲存情境特徵
async function handleSave() {
  if (!props.projectId || props.projectId === 'home') return

  const payload: ScenarioData = {
    type: 'custom',
    title: '試驗情境設定',
    target: '',
    target_label: '藥劑/標的',
    categories: categories.value.map((c) => {
      const isControl = c.is_control ?? false
      const trt = (c.treatment || '').trim()
      const d = (c.dose || '').trim()
      let n = (c.name || '').trim()
      if (!n) {
        n = isControl ? '未施藥對照 (CK)' : [trt, d].filter(Boolean).join(' ') || '處理組'
      }
      return {
        name: n,
        treatment: trt,
        dose: d,
        color: c.color,
        is_control: isControl,
      }
    }),
  }

  isSaving.value = true
  try {
    const res = await fetch(`/api/task/scenario/${props.projectId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario: payload }),
    })
    const data = await res.json().catch(() => null)
    if (res.ok && data?.result) {
      isDirty.value = false
      isSaved.value = true
      emit('update:scenario', payload)
      emit('saved', payload)
    } else {
      alert(data?.message || '儲存情境特徵失敗')
    }
  } catch (err) {
    console.error('儲存情境特徵錯誤:', err)
    alert('網路連線失敗，請稍後再試')
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <Card class="border shadow-xs transition-all duration-200">
    <Collapsible v-model:open="isOpen">
      <CardHeader class="py-2.5 px-4">
        <div class="flex items-center justify-between gap-3">
          <div class="flex flex-wrap items-center gap-2">
            <div class="flex items-center gap-1.5 font-semibold text-sm text-foreground">
              <FlaskConical class="size-4 text-primary" />
              <span>專案試驗情境特徵</span>
            </div>

            <!-- 折疊時的摘要預覽徽章 -->
            <template v-if="!isOpen">
              <div class="flex items-center gap-1">
                <Badge
                  v-for="(cat, idx) in categories.slice(0, 5)"
                  :key="idx"
                  variant="outline"
                  class="text-[11px] font-normal py-0 px-1.5 flex items-center gap-1"
                >
                  <span class="size-1.5 rounded-full shrink-0" :style="{ backgroundColor: cat.color }" />
                  {{ cat.name || [cat.treatment, cat.dose].filter(Boolean).join(' ') || (cat.is_control ? '對照組 (CK)' : '處理組') }}
                </Badge>
                <span v-if="categories.length > 5" class="text-[10px] text-muted-foreground">
                  +{{ categories.length - 5 }}
                </span>
              </div>
            </template>

            <!-- 狀態提示 -->
            <Badge v-if="isSaved && !isDirty" variant="outline" class="text-emerald-600 border-emerald-500/30 bg-emerald-50/50 text-[11px] py-0">
              <CheckCircle2 class="size-3 mr-1" />
              已儲存特徵
            </Badge>
            <Badge v-else-if="isDirty" variant="outline" class="text-amber-600 border-amber-500/30 bg-amber-50/50 text-[11px] py-0">
              未儲存變更
            </Badge>
          </div>

          <div class="flex items-center gap-2">
            <!-- 展開 / 收合開關 -->
            <CollapsibleTrigger as-child>
              <Button size="sm" variant="ghost" class="h-7 px-2 text-xs gap-1 text-muted-foreground hover:text-foreground cursor-pointer">
                <span>{{ isOpen ? '收合' : '展開編輯' }}</span>
                <ChevronUp v-if="isOpen" class="size-3.5" />
                <ChevronDown v-else class="size-3.5" />
              </Button>
            </CollapsibleTrigger>
          </div>
        </div>
      </CardHeader>

      <CollapsibleContent>
        <CardContent class="pt-0 pb-3 px-4 space-y-3">
          <!-- 組別列頭部與新增按鈕 -->
          <div class="flex items-center justify-between border-t pt-2.5">
            <Label class="text-xs font-semibold text-foreground">
              試驗組別
            </Label>
            <Button
              size="sm"
              variant="outline"
              type="button"
              class="h-6 text-xs px-2 gap-1 cursor-pointer"
              @click="addCategory"
            >
              <Plus class="size-3" />
              新增組別
            </Button>
          </div>

          <!-- 動態組別卡片列表 -->
          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
            <div
              v-for="(cat, idx) in categories"
              :key="idx"
              class="flex flex-col gap-1.5 p-2 rounded-lg border bg-card/60 relative group hover:border-primary/40 transition-colors"
            >
              <!-- 頂部顏色與刪除按鈕 -->
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-1.5">
                  <input
                    v-model="cat.color"
                    type="color"
                    aria-label="選擇組別代表顏色"
                    class="size-4 rounded cursor-pointer border-0 p-0 bg-transparent"
                    @input="isDirty = true"
                  />
                  <Badge
                    :variant="cat.is_control ? 'secondary' : 'outline'"
                    :class="[
                      'text-[10px] py-0 px-1 font-mono select-none',
                      cat.is_control ? 'cursor-default' : 'cursor-pointer hover:bg-accent/40'
                    ]"
                    :style="!cat.is_control ? { borderColor: cat.color + '80', color: cat.color } : {}"
                    :title="cat.is_control ? '目前為唯一對照組 (CK)' : '點擊設為對照組 (CK)'"
                    @click="toggleControl(cat)"
                  >
                    {{ cat.is_control ? '對照組 (CK)' : '處理組' }}
                  </Badge>
                </div>

                <button
                  v-if="!cat.is_control && categories.length > 1"
                  type="button"
                  aria-label="移除此組別"
                  class="text-muted-foreground hover:text-destructive opacity-70 group-hover:opacity-100 transition-opacity p-0.5 rounded cursor-pointer"
                  @click="removeCategory(idx)"
                >
                  <Trash2 class="size-3.5" />
                </button>
              </div>

              <!-- 對照組輸入單欄，處理組輸入藥劑＋劑量兩欄 -->
              <div v-if="cat.is_control" class="space-y-1">
                <Input
                  v-model="cat.name"
                  placeholder="未施藥對照 (CK)"
                  class="h-6 text-xs px-1.5 font-medium"
                  @input="isDirty = true"
                  @keydown.enter.prevent="handleSave"
                />
              </div>
              <div v-else class="space-y-1">
                <Input
                  v-model="cat.treatment"
                  placeholder="藥劑名稱 (如 快得寧)"
                  class="h-6 text-xs px-1.5 font-medium"
                  @input="onTreatmentChange(cat)"
                  @keydown.enter.prevent="handleSave"
                />
                <Input
                  v-model="cat.dose"
                  placeholder="劑量/倍數 (如 500x)"
                  class="h-6 text-xs px-1.5"
                  @input="onTreatmentChange(cat)"
                  @keydown.enter.prevent="handleSave"
                />
              </div>
            </div>
          </div>

          <!-- 操作按鈕列 -->
          <div class="flex items-center justify-end pt-1 border-t">
            <Button
              data-tour="save-scenario"
              size="sm"
              class="h-7 text-xs gap-1.5 px-3 cursor-pointer"
              :disabled="isSaving"
              @click="handleSave"
            >
              <Spinner v-if="isSaving" class="size-3.5 animate-spin" />
              <Save v-else class="size-3.5" />
              <span>{{ isSaving ? '儲存中...' : '儲存情境特徵' }}</span>
            </Button>
          </div>
        </CardContent>
      </CollapsibleContent>
    </Collapsible>
  </Card>
</template>
