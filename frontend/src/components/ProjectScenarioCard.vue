<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import {
  Card,
  CardContent,
  CardHeader,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import {
  CheckCircle2,
  Plus,
  Trash2,
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

// 對照組預設固定灰白色彩
const CONTROL_COLOR = '#94a3b8'

// 處理組高對比識別調色盤
const TREATMENT_PALETTE = [
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

const isSaving = ref(false)
const isSaved = ref(false)
const isDirty = ref(false)

const categories = ref<ScenarioCategoryItem[]>([])
const blurredInputs = ref<Record<string, boolean>>({})

// 檢驗單一組別是否填寫完整
function isCategoryValid(cat: ScenarioCategoryItem): boolean {
  if (cat.is_control) {
    return (cat.name || '').trim().length > 0
  }
  const trt = (cat.treatment || '').trim()
  const d = (cat.dose || '').trim()
  return trt.length > 0 && d.length > 0
}

// 檢驗所有組別是否填寫完整
const areAllCategoriesValid = computed<boolean>(() => {
  if (categories.value.length === 0) return false
  return categories.value.every(isCategoryValid)
})

const canAddCategory = computed<boolean>(() => areAllCategoriesValid.value)
const canSave = computed<boolean>(() => areAllCategoriesValid.value && !isSaving.value)

// 檢查特定欄位是否未填且需警示
function isFieldInvalid(idx: number, field: 'name' | 'treatment' | 'dose'): boolean {
  const cat = categories.value[idx]
  if (!cat) return false
  const key = `${idx}-${field}`
  const isChecked = Boolean(blurredInputs.value[key] || isDirty.value)
  if (!isChecked) return false
  if (field === 'name') return (cat.name || '').trim().length === 0
  if (field === 'treatment') return (cat.treatment || '').trim().length === 0
  if (field === 'dose') return (cat.dose || '').trim().length === 0
  return false
}

// 標記欄位已失焦
function markBlurred(idx: number, field: 'name' | 'treatment' | 'dose') {
  blurredInputs.value[`${idx}-${field}`] = true
}

// 聚焦特定欄位
function focusField(idx: number, field: 'name' | 'treatment' | 'dose') {
  const el = document.getElementById(`scenario-cat-${idx}-${field}`)
  if (el) {
    el.focus()
  }
}

// 劑量輸入框按下 Enter 鍵處理
function handleDoseEnter() {
  if (canSave.value) {
    handleSave()
  }
}

// 初始化預設組別骨架：首組恆為對照組 (CK) ＋ 1 個空白處理組
function initDefaultCategories() {
  categories.value = [
    { name: '未施藥對照 (CK)', treatment: '', dose: '', color: CONTROL_COLOR, is_control: true },
    { name: '', treatment: '', dose: '', color: TREATMENT_PALETTE[0], is_control: false },
  ]
  blurredInputs.value = {}
  isDirty.value = false
}

// 新增處理組別
async function addCategory() {
  if (!canAddCategory.value) return
  const treatmentCount = categories.value.filter((c) => !c.is_control).length
  const nextColor = TREATMENT_PALETTE[treatmentCount % TREATMENT_PALETTE.length]
  categories.value.push({
    name: '',
    treatment: '',
    dose: '',
    color: nextColor,
    is_control: false,
  })
  isDirty.value = true
  const newIdx = categories.value.length - 1
  await nextTick()
  focusField(newIdx, 'treatment')
}

// 移除組別（防呆守衛：對照組不可刪除）
function removeCategory(index: number) {
  if (categories.value[index]?.is_control) return
  categories.value.splice(index, 1)
  isDirty.value = true
}

// 當編輯藥劑名稱或劑量時同步組名
function onTreatmentChange(cat: ScenarioCategoryItem) {
  const trt = (cat.treatment || '').trim()
  const d = (cat.dose || '').trim()
  cat.name = [trt, d].filter(Boolean).join(' ')
  isDirty.value = true
}

// 載入已存在之情境設定（保證首組恆為對照組且為固定灰白色，其餘全為處理組）
function loadFromScenario(data: ScenarioData) {
  if (!data || !Array.isArray(data.categories) || data.categories.length === 0) {
    initDefaultCategories()
    return
  }
  const defaultTarget = (data.target || '').trim()

  // 1. 抽取原有標記為對照組之項目，若無則以第 1 個項目作為對照組
  let controlItem = data.categories.find((c) => c.is_control)
  const treatmentItems = data.categories.filter((c) => c !== controlItem)

  if (!controlItem) {
    controlItem = data.categories[0]
    treatmentItems.splice(0, 1)
  }

  const normalizedCategories: ScenarioCategoryItem[] = []

  // 2. 首組恆為對照組，色彩固定為 CONTROL_COLOR
  normalizedCategories.push({
    name: controlItem.name?.trim() || '未施藥對照 (CK)',
    treatment: '',
    dose: '',
    color: CONTROL_COLOR,
    is_control: true,
  })

  // 3. 其餘組別恆為處理組
  treatmentItems.forEach((c, idx) => {
    let trt = c.treatment || ''
    let d = c.dose || ''
    let n = c.name || ''

    if (!trt && defaultTarget) {
      trt = defaultTarget
    }
    if (!d && n && n !== trt) {
      d = n
    }
    if (!n) {
      n = [trt, d].filter(Boolean).join(' ') || `處理組 ${idx + 1}`
    }

    normalizedCategories.push({
      name: n,
      treatment: trt,
      dose: d,
      color: c.color || TREATMENT_PALETTE[idx % TREATMENT_PALETTE.length],
      is_control: false,
    })
  })

  categories.value = normalizedCategories
  blurredInputs.value = {}
  isDirty.value = false
  isSaved.value = true
}

watch(
  () => props.initialScenario,
  (newScenario) => {
    if (newScenario && typeof newScenario === 'object' && Object.keys(newScenario).length > 0) {
      loadFromScenario(newScenario as ScenarioData)
    } else {
      initDefaultCategories()
    }
  },
  { immediate: true }
)

// 儲存情境設定
async function handleSave() {
  if (!canSave.value) return
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
    <CardHeader class="py-2.5 px-4 border-b border-border/40">
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <Label class="text-xs font-semibold text-foreground">
            試驗組別
          </Label>

          <!-- 狀態提示 -->
          <Badge v-if="isSaved && !isDirty" variant="outline" class="text-emerald-600 border-emerald-500/30 bg-emerald-50/50 text-[11px] py-0">
            <CheckCircle2 class="size-3 mr-1" />
            已儲存特徵
          </Badge>
          <Badge v-else-if="isDirty" variant="outline" class="text-amber-600 border-amber-500/30 bg-amber-50/50 text-[11px] py-0">
            未儲存變更
          </Badge>
        </div>

        <Button
          size="sm"
          variant="outline"
          type="button"
          class="h-7 text-xs px-2.5 gap-1 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="!canAddCategory"
          :title="canAddCategory ? '新增組別' : '請先完整填寫現有組別資訊'"
          @click="addCategory"
        >
          <Plus class="size-3.5" />
          新增組別
        </Button>
      </div>
    </CardHeader>

    <CardContent class="pt-3 pb-3 px-4 space-y-3">
      <!-- Element Plus 風格暗黑極簡資料表格 -->
          <div class="overflow-x-auto rounded-md border border-border/40 bg-card/40">
            <table class="w-full text-left border-collapse text-xs">
              <thead class="border-b border-border/40 bg-muted/20 text-muted-foreground font-medium select-none">
                <tr>
                  <th class="py-2.5 px-3 w-16 text-center">色彩</th>
                  <th class="py-2.5 px-3">藥劑 / 組別名稱</th>
                  <th class="py-2.5 px-3 w-44">施用劑量 / 倍數</th>
                  <th class="py-2.5 px-3 w-24 text-right">操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border/30">
                <tr
                  v-for="(cat, idx) in categories"
                  :key="idx"
                  class="group transition-colors hover:bg-muted/20"
                >
                  <!-- 色彩欄位 -->
                  <td class="py-2 px-3 text-center align-middle">
                    <div class="flex items-center justify-center">
                      <!-- 對照組顯示靜態灰白色塊；處理組顯示自訂選色器 -->
                      <span
                        v-if="cat.is_control"
                        class="size-5 rounded bg-[#94a3b8] inline-block shrink-0 shadow-xs border border-border/50"
                        title="對照組固定灰白色"
                      />
                      <label
                        v-else
                        class="size-5 rounded inline-block shrink-0 shadow-xs border border-border/50 relative overflow-hidden cursor-pointer hover:scale-105 transition-transform"
                        :style="{ backgroundColor: cat.color }"
                        title="選擇組別代表顏色"
                      >
                        <input
                          v-model="cat.color"
                          type="color"
                          aria-label="選擇組別代表顏色"
                          class="absolute inset-0 opacity-0 w-full h-full cursor-pointer"
                          @input="isDirty = true"
                        />
                      </label>
                    </div>
                  </td>

                  <!-- 藥劑 / 組別名稱欄位 -->
                  <td class="py-2 px-3 align-middle">
                    <!-- 對照組名稱輸入框 -->
                    <Input
                      v-if="cat.is_control"
                      :id="`scenario-cat-${idx}-name`"
                      v-model="cat.name"
                      placeholder="未施藥對照 (CK)"
                      :class="[
                        'h-7 text-xs px-2 font-medium transition-colors w-full',
                        isFieldInvalid(idx, 'name') ? '!border-destructive/60 focus-visible:!ring-destructive/30' : ''
                      ]"
                      :aria-invalid="isFieldInvalid(idx, 'name')"
                      @input="isDirty = true"
                      @blur="markBlurred(idx, 'name')"
                      @keydown.enter.prevent="handleSave"
                    />

                    <!-- 處理組藥劑名稱輸入框 -->
                    <Input
                      v-else
                      :id="`scenario-cat-${idx}-treatment`"
                      v-model="cat.treatment"
                      placeholder="藥劑名稱 (如 快得寧)"
                      :class="[
                        'h-7 text-xs px-2 font-medium transition-colors w-full',
                        isFieldInvalid(idx, 'treatment') ? '!border-destructive/60 focus-visible:!ring-destructive/30' : ''
                      ]"
                      :aria-invalid="isFieldInvalid(idx, 'treatment')"
                      @input="onTreatmentChange(cat)"
                      @blur="markBlurred(idx, 'treatment')"
                      @keydown.enter.prevent="focusField(idx, 'dose')"
                    />
                  </td>

                  <!-- 施用劑量 / 倍數欄位 -->
                  <td class="py-2 px-3 align-middle">
                    <!-- 對照組無劑量（不適用） -->
                    <div v-if="cat.is_control" class="text-xs text-muted-foreground/60 px-2 py-1 select-none font-mono">
                      —（不適用）
                    </div>

                    <!-- 處理組劑量輸入框 -->
                    <Input
                      v-else
                      :id="`scenario-cat-${idx}-dose`"
                      v-model="cat.dose"
                      placeholder="劑量/倍數 (如 500x)"
                      :class="[
                        'h-7 text-xs px-2 transition-colors w-full',
                        isFieldInvalid(idx, 'dose') ? '!border-destructive/60 focus-visible:!ring-destructive/30' : ''
                      ]"
                      :aria-invalid="isFieldInvalid(idx, 'dose')"
                      @input="onTreatmentChange(cat)"
                      @blur="markBlurred(idx, 'dose')"
                      @keydown.enter.prevent="handleDoseEnter"
                    />
                  </td>

                  <!-- 操作欄位 -->
                  <td class="py-2 px-3 align-middle text-right">
                    <!-- 對照組基準鎖定 -->
                    <span v-if="cat.is_control" class="text-[11px] text-muted-foreground/50 select-none mr-2">
                      基準鎖定
                    </span>

                    <!-- 處理組刪除按鈕 (仿照 Element Plus 紅色危險按鈕) -->
                    <button
                      v-else-if="categories.length > 1"
                      type="button"
                      class="inline-flex items-center justify-center h-6 px-2.5 rounded text-xs font-medium text-white bg-rose-500 hover:bg-rose-600 active:bg-rose-700 shadow-xs cursor-pointer transition-colors"
                      title="刪除此組別"
                      @click="removeCategory(idx)"
                    >
                      刪除
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 操作按鈕列 -->
          <div class="flex items-center justify-end pt-1 border-t">
            <Button
              data-tour="save-scenario"
              size="sm"
              class="h-7 text-xs gap-1.5 px-3 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="!canSave"
              :title="canSave ? '儲存' : '請先完整填寫所有組別欄位'"
              @click="handleSave"
            >
              <Spinner v-if="isSaving" class="size-3.5 animate-spin" />
              <Save v-else class="size-3.5" />
              <span>{{ isSaving ? '儲存中...' : '儲存' }}</span>
            </Button>
          </div>
        </CardContent>
  </Card>
</template>
