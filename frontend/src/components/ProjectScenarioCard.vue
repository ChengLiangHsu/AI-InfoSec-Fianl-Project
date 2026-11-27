<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
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
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  CheckCircle2,
  Plus,
  Trash2,
  AlertCircle,
  Columns3,
  Lock,
  X,
} from '@lucide/vue'
import {
  CONTROL_COLOR,
  TREATMENT_PALETTE,
  deriveCategorySummary,
  normalizeScenario,
  type DynamicFieldDef,
  type DynamicFieldType,
  type DynamicFieldValue,
  type ScenarioCategoryItem,
  type ScenarioData,
} from '@/lib/scenarioSchema'

export type { ScenarioCategoryItem, ScenarioData }

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

const scenarioTitle = ref('試驗情境設定')
const scenarioType = ref('custom')
const scenarioDescription = ref('')
const metadataFields = ref<DynamicFieldDef[]>([])
const metadataValues = ref<Record<string, DynamicFieldValue>>({})
const groupFields = ref<DynamicFieldDef[]>([])
const categories = ref<ScenarioCategoryItem[]>([])

const saveState = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const saveError = ref('')
let saveTimer: ReturnType<typeof setTimeout> | null = null
let isHydrating = false

// 新增自訂欄位小面板狀態
const showAddField = ref(false)
const newFieldLabel = ref('')
const newFieldType = ref<DynamicFieldType>('text')
const newFieldUnit = ref('')
const newFieldOptionsText = ref('')

const scenarioTypeLabel = computed(() => {
  const raw = (scenarioType.value || '').toLowerCase()
  if (raw.includes('variety') || raw.includes('品種')) return '品種比較'
  if (raw.includes('pesticide') || raw.includes('insecticide') || raw.includes('herbicide') || raw.includes('fungicide') || raw.includes('藥')) return '農藥藥效'
  if (raw.includes('fertilizer') || raw.includes('肥')) return '肥料試驗'
  if (raw.includes('monitor') || raw.includes('growth') || raw.includes('長勢')) return '長勢監測'
  if (raw.includes('irrigation') || raw.includes('灌溉')) return '灌溉試驗'
  if (raw === 'custom' || !raw) return '自訂試驗'
  return scenarioType.value
})

function buildPayload(): ScenarioData {
  const mappedCategories = categories.value.map((cat, idx) => {
    if (cat.is_control || idx === 0) {
      return {
        id: cat.id || 'ck',
        name: (cat.name || '').trim() || '對照組 (CK)',
        color: CONTROL_COLOR,
        is_control: true,
        values: {},
        treatment: '',
        dose: '',
      }
    }
    const summary = deriveCategorySummary(cat, groupFields.value)
    return {
      id: cat.id || `grp-${idx}`,
      name: summary.label || (cat.name || '').trim() || `處理組 ${idx}`,
      color: cat.color || TREATMENT_PALETTE[(idx - 1) % TREATMENT_PALETTE.length],
      is_control: false,
      values: { ...(cat.values || {}) },
      treatment: summary.treatment,
      dose: summary.dose,
    }
  })

  return {
    version: 2,
    type: scenarioType.value || 'custom',
    title: scenarioTitle.value.trim() || '試驗情境設定',
    description: scenarioDescription.value.trim(),
    metadata_fields: metadataFields.value.map((f) => ({ ...f })),
    metadata_values: { ...metadataValues.value },
    group_fields: groupFields.value.map((f) => ({ ...f })),
    categories: mappedCategories,
  }
}

function hydrateFromScenario(raw: ScenarioData | null | undefined) {
  isHydrating = true
  const normalized = normalizeScenario(raw)
  scenarioTitle.value = normalized.title
  scenarioType.value = normalized.type
  scenarioDescription.value = normalized.description || ''
  metadataFields.value = normalized.metadata_fields || []
  metadataValues.value = { ...(normalized.metadata_values || {}) }
  groupFields.value = normalized.group_fields || []
  categories.value = normalized.categories.map((c) => ({
    ...c,
    values: { ...(c.values || {}) },
  }))
  if (raw && Object.keys(raw).length > 0) {
    saveState.value = 'saved'
  }
  isHydrating = false
}

watch(
  () => props.initialScenario,
  (newScenario) => {
    if (!newScenario) return
    const incomingJson = JSON.stringify(normalizeScenario(newScenario))
    const currentJson = JSON.stringify(buildPayload())
    if (incomingJson !== currentJson) {
      hydrateFromScenario(newScenario)
    }
  },
  { immediate: true, deep: true }
)

async function persistNow() {
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  if (!props.projectId || props.projectId === 'home') return
  const payload = buildPayload()
  emit('update:scenario', payload)

  saveState.value = 'saving'
  saveError.value = ''
  try {
    const res = await fetch(`/api/task/scenario/${props.projectId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario: payload }),
    })
    const data = await res.json().catch(() => null)
    if (res.ok && data?.result) {
      saveState.value = 'saved'
      emit('saved', data.data || payload)
    } else {
      saveState.value = 'error'
      saveError.value = data?.message || '自動儲存失敗'
    }
  } catch (err) {
    console.error('自動儲存情境表單錯誤:', err)
    saveState.value = 'error'
    saveError.value = '網路連線失敗'
  }
}

function scheduleAutoSave(immediate = false) {
  if (isHydrating) return
  const payload = buildPayload()
  emit('update:scenario', payload)

  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  if (immediate) {
    persistNow()
    return
  }
  saveState.value = 'saving'
  saveTimer = setTimeout(() => {
    persistNow()
  }, 600)
}

onUnmounted(() => {
  if (saveTimer) {
    clearTimeout(saveTimer)
    persistNow()
  }
})

function updateMetadataValue(key: string, val: DynamicFieldValue, immediate = false) {
  metadataValues.value = {
    ...metadataValues.value,
    [key]: val,
  }
  scheduleAutoSave(immediate)
}

function updateCategoryValue(catIdx: number, key: string, val: DynamicFieldValue, immediate = false) {
  const cat = categories.value[catIdx]
  if (!cat || cat.is_control) return
  cat.values = {
    ...(cat.values || {}),
    [key]: val,
  }
  const summary = deriveCategorySummary(cat, groupFields.value)
  cat.name = summary.label
  cat.treatment = summary.treatment
  cat.dose = summary.dose
  scheduleAutoSave(immediate)
}

function addCategory() {
  const treatmentCount = categories.value.filter((c) => !c.is_control).length
  const nextColor = TREATMENT_PALETTE[treatmentCount % TREATMENT_PALETTE.length]
  const emptyValues: Record<string, DynamicFieldValue> = {}
  for (const field of groupFields.value) {
    emptyValues[field.key] = field.type === 'boolean' ? false : ''
  }
  categories.value.push({
    id: `grp-${Date.now().toString(36)}`,
    name: `處理組 ${treatmentCount + 1}`,
    color: nextColor,
    is_control: false,
    values: emptyValues,
    treatment: '',
    dose: '',
  })
  scheduleAutoSave(true)
}

function removeCategory(idx: number) {
  if (idx === 0 || categories.value[idx]?.is_control) return
  categories.value.splice(idx, 1)
  scheduleAutoSave(true)
}

function addCustomGroupField() {
  const label = newFieldLabel.value.trim()
  if (!label) return
  const key = `col_${Date.now().toString(36)}`
  const field: DynamicFieldDef = {
    key,
    label,
    type: newFieldType.value,
  }
  if (newFieldType.value === 'number' && newFieldUnit.value.trim()) {
    field.unit = newFieldUnit.value.trim()
  }
  if (newFieldType.value === 'select') {
    field.options = newFieldOptionsText.value
      .split(/[,，、\n]/)
      .map((s) => s.trim())
      .filter(Boolean)
  }
  groupFields.value.push(field)
  for (const cat of categories.value) {
    if (!cat.is_control) {
      cat.values = {
        ...(cat.values || {}),
        [key]: field.type === 'boolean' ? false : '',
      }
    }
  }
  newFieldLabel.value = ''
  newFieldType.value = 'text'
  newFieldUnit.value = ''
  newFieldOptionsText.value = ''
  showAddField.value = false
  scheduleAutoSave(true)
}

function removeGroupField(fieldIdx: number) {
  if (groupFields.value.length <= 1) return
  const [removed] = groupFields.value.splice(fieldIdx, 1)
  if (removed) {
    for (const cat of categories.value) {
      if (cat.values && removed.key in cat.values) {
        delete cat.values[removed.key]
      }
    }
  }
  scheduleAutoSave(true)
}
</script>

<template>
  <Card class="border border-border/70 shadow-xs transition-all duration-200">
    <!-- 表單標頭：標題 + 自動存檔狀態 + 操作 -->
    <CardHeader class="py-3 px-4 border-b border-border/40 space-y-2">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2 min-w-0 flex-1">
          <Input
            v-model="scenarioTitle"
            placeholder="試驗情境標題"
            class="h-8 text-sm font-semibold px-2 max-w-xs border-transparent hover:border-border focus-visible:border-ring bg-transparent"
            @input="scheduleAutoSave(false)"
            @blur="persistNow"
          />
          <Badge variant="secondary" class="text-[11px] shrink-0">
            {{ scenarioTypeLabel }}
          </Badge>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <!-- 即時自動存檔狀態 -->
          <Badge
            v-if="saveState === 'saving'"
            variant="outline"
            class="text-amber-600 border-amber-500/30 bg-amber-50/50 text-[11px] py-0.5 gap-1"
          >
            <Spinner class="size-3 animate-spin" />
            自動儲存中...
          </Badge>
          <Badge
            v-else-if="saveState === 'saved'"
            variant="outline"
            class="text-emerald-600 border-emerald-500/30 bg-emerald-50/50 text-[11px] py-0.5 gap-1"
          >
            <CheckCircle2 class="size-3" />
            已自動儲存
          </Badge>
          <button
            v-else-if="saveState === 'error'"
            type="button"
            class="inline-flex items-center gap-1 rounded-full border border-destructive/40 bg-destructive/10 px-2 py-0.5 text-[11px] font-medium text-destructive cursor-pointer hover:bg-destructive/20"
            :title="saveError"
            @click="persistNow"
          >
            <AlertCircle class="size-3" />
            儲存失敗（點擊重試）
          </button>
        </div>
      </div>

      <p v-if="scenarioDescription" class="text-xs text-muted-foreground leading-relaxed px-2">
        {{ scenarioDescription }}
      </p>
    </CardHeader>

    <CardContent class="pt-4 pb-4 px-4 space-y-5">
      <!-- 區塊 1：試驗共通資訊（由 AI 依情境動態生成） -->
      <section v-if="metadataFields.length > 0" class="space-y-2.5">
        <div class="flex items-center justify-between">
          <Label class="text-xs font-semibold text-foreground">
            試驗共通資訊
          </Label>
          <span class="text-[11px] text-muted-foreground">整場試驗共用背景紀錄</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 rounded-lg border border-border/50 bg-muted/15 p-3">
          <div
            v-for="field in metadataFields"
            :key="field.key"
            class="space-y-1"
          >
            <Label :for="`meta-${field.key}`" class="text-[11px] text-muted-foreground flex items-center gap-1">
              <span>{{ field.label }}</span>
              <span v-if="field.unit" class="font-mono text-[10px] opacity-75">({{ field.unit }})</span>
            </Label>

            <!-- Select -->
            <Select
              v-if="field.type === 'select'"
              :model-value="String(metadataValues[field.key] ?? '')"
              @update:model-value="updateMetadataValue(field.key, $event as string, true)"
            >
              <SelectTrigger :id="`meta-${field.key}`" class="h-8 text-xs w-full bg-background">
                <SelectValue :placeholder="field.placeholder || `選擇${field.label}`" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="opt in field.options || []"
                  :key="opt"
                  :value="opt"
                  class="text-xs"
                >
                  {{ opt }}
                </SelectItem>
              </SelectContent>
            </Select>

            <!-- Boolean -->
            <div v-else-if="field.type === 'boolean'" class="flex items-center gap-2 h-8">
              <Switch
                :id="`meta-${field.key}`"
                :model-value="Boolean(metadataValues[field.key])"
                @update:model-value="updateMetadataValue(field.key, $event, true)"
              />
              <span class="text-xs text-muted-foreground">
                {{ metadataValues[field.key] ? '是' : '否' }}
              </span>
            </div>

            <!-- Number with optional unit -->
            <div v-else-if="field.type === 'number'" class="relative flex items-center">
              <Input
                :id="`meta-${field.key}`"
                type="number"
                :model-value="(metadataValues[field.key] as string | number) ?? ''"
                :placeholder="field.placeholder || '輸入數值'"
                class="h-8 text-xs bg-background"
                :class="field.unit ? 'pr-12' : ''"
                @update:model-value="updateMetadataValue(field.key, $event === '' ? '' : Number($event), false)"
                @blur="persistNow"
              />
              <span
                v-if="field.unit"
                class="pointer-events-none absolute right-2.5 text-[11px] font-mono text-muted-foreground"
              >
                {{ field.unit }}
              </span>
            </div>

            <!-- Date -->
            <Input
              v-else-if="field.type === 'date'"
              :id="`meta-${field.key}`"
              type="date"
              :model-value="String(metadataValues[field.key] ?? '')"
              class="h-8 text-xs bg-background"
              @update:model-value="updateMetadataValue(field.key, $event as string, true)"
            />

            <!-- Text (default) -->
            <Input
              v-else
              :id="`meta-${field.key}`"
              type="text"
              :model-value="String(metadataValues[field.key] ?? '')"
              :placeholder="field.placeholder || `輸入${field.label}`"
              class="h-8 text-xs bg-background"
              @update:model-value="updateMetadataValue(field.key, $event as string, false)"
              @blur="persistNow"
            />
          </div>
        </div>
      </section>

      <!-- 區塊 2：實驗組別清單動態表格（對應步驟 3 小區套用選項） -->
      <section class="space-y-2.5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <Label class="text-xs font-semibold text-foreground">
              實驗組別清單
            </Label>
            <span class="text-[11px] text-muted-foreground">
              將作為步驟 3 框選小區的套用組別
            </span>
          </div>

          <div class="flex items-center gap-1.5">
            <Button
              size="sm"
              variant="ghost"
              type="button"
              class="h-7 text-xs px-2 gap-1 cursor-pointer text-muted-foreground hover:text-foreground"
              @click="showAddField = !showAddField"
            >
              <Columns3 class="size-3.5" />
              <span>新增欄位</span>
            </Button>
            <Button
              size="sm"
              variant="outline"
              type="button"
              class="h-7 text-xs px-2.5 gap-1 cursor-pointer"
              @click="addCategory"
            >
              <Plus class="size-3.5" />
              <span>新增組別</span>
            </Button>
          </div>
        </div>

        <!-- 手動新增欄位小工具列 -->
        <div
          v-if="showAddField"
          class="flex flex-wrap items-end gap-2 rounded-lg border border-dashed border-primary/40 bg-primary/5 p-2.5 text-xs"
        >
          <div class="space-y-1 flex-1 min-w-[120px]">
            <Label class="text-[11px]">欄位名稱</Label>
            <Input
              v-model="newFieldLabel"
              placeholder="例：施用時期"
              class="h-7 text-xs bg-background"
              @keydown.enter.prevent="addCustomGroupField"
            />
          </div>
          <div class="space-y-1 w-28">
            <Label class="text-[11px]">型態</Label>
            <Select v-model="newFieldType">
              <SelectTrigger class="h-7 text-xs bg-background">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="text" class="text-xs">文字</SelectItem>
                <SelectItem value="number" class="text-xs">數字</SelectItem>
                <SelectItem value="select" class="text-xs">下拉選單</SelectItem>
                <SelectItem value="date" class="text-xs">日期</SelectItem>
                <SelectItem value="boolean" class="text-xs">是/否開關</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div v-if="newFieldType === 'number'" class="space-y-1 w-24">
            <Label class="text-[11px]">單位</Label>
            <Input v-model="newFieldUnit" placeholder="倍 / kg" class="h-7 text-xs bg-background" />
          </div>
          <div v-if="newFieldType === 'select'" class="space-y-1 flex-1 min-w-[160px]">
            <Label class="text-[11px]">選項（逗號分隔）</Label>
            <Input v-model="newFieldOptionsText" placeholder="例：葉面噴灑, 無人機, 灌注" class="h-7 text-xs bg-background" />
          </div>
          <div class="flex items-center gap-1">
            <Button size="sm" type="button" class="h-7 text-xs px-2.5 cursor-pointer" @click="addCustomGroupField">
              加入
            </Button>
            <Button size="sm" variant="ghost" type="button" class="h-7 w-7 p-0 cursor-pointer" @click="showAddField = false">
              <X class="size-3.5" />
            </Button>
          </div>
        </div>

        <!-- 動態多型態組別表格 -->
        <div class="overflow-x-auto rounded-md border border-border/50 bg-card/40">
          <table class="w-full text-left border-collapse text-xs">
            <thead class="border-b border-border/40 bg-muted/25 text-muted-foreground font-medium select-none">
              <tr>
                <th class="py-2.5 px-3 w-14 text-center whitespace-nowrap">色彩</th>
                <th
                  v-for="(field, fIdx) in groupFields"
                  :key="field.key"
                  class="py-2.5 px-2.5 min-w-[120px]"
                >
                  <div class="flex items-center justify-between gap-1 group/col">
                    <span class="truncate">
                      {{ field.label }}
                      <span v-if="field.unit" class="font-mono text-[10px] opacity-75">({{ field.unit }})</span>
                    </span>
                    <button
                      v-if="groupFields.length > 1"
                      type="button"
                      class="opacity-0 group-hover/col:opacity-100 rounded p-0.5 text-muted-foreground hover:text-destructive transition-opacity cursor-pointer"
                      :title="`移除「${field.label}」欄位`"
                      @click="removeGroupField(fIdx)"
                    >
                      <X class="size-3" />
                    </button>
                  </div>
                </th>
                <th class="py-2.5 px-3 w-24 text-right whitespace-nowrap">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border/30">
              <tr
                v-for="(cat, idx) in categories"
                :key="cat.id || idx"
                class="group transition-colors hover:bg-muted/20"
                :class="cat.is_control ? 'bg-muted/15' : ''"
              >
                <!-- 色彩欄 -->
                <td class="py-2 px-3 text-center align-middle">
                  <div class="flex items-center justify-center">
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
                        @input="scheduleAutoSave(false)"
                        @change="persistNow"
                      />
                    </label>
                  </div>
                </td>

                <!-- 對照組 (CK)：內建鎖定，無需設定動態處理欄位 -->
                <template v-if="cat.is_control">
                  <td :colspan="Math.max(1, groupFields.length)" class="py-2 px-2.5 align-middle">
                    <div class="flex items-center gap-2 text-xs text-muted-foreground select-none">
                      <span class="font-medium text-foreground">{{ cat.name || '對照組 (CK)' }}</span>
                      <span class="text-[11px] opacity-70">— 內建基準對照，無須設定處理參數</span>
                    </div>
                  </td>
                </template>

                <!-- 處理組：依 groupFields 渲染多型態元件 -->
                <template v-else>
                  <td
                    v-for="field in groupFields"
                    :key="field.key"
                    class="py-2 px-2 align-middle"
                  >
                    <!-- Select -->
                    <Select
                      v-if="field.type === 'select'"
                      :model-value="String(cat.values?.[field.key] ?? '')"
                      @update:model-value="updateCategoryValue(idx, field.key, $event as string, true)"
                    >
                      <SelectTrigger class="h-7 text-xs w-full bg-background">
                        <SelectValue :placeholder="field.placeholder || '請選擇'" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem
                          v-for="opt in field.options || []"
                          :key="opt"
                          :value="opt"
                          class="text-xs"
                        >
                          {{ opt }}
                        </SelectItem>
                      </SelectContent>
                    </Select>

                    <!-- Boolean -->
                    <div v-else-if="field.type === 'boolean'" class="flex items-center gap-1.5 px-1">
                      <Switch
                        :model-value="Boolean(cat.values?.[field.key])"
                        @update:model-value="updateCategoryValue(idx, field.key, $event, true)"
                      />
                      <span class="text-[11px] text-muted-foreground">
                        {{ cat.values?.[field.key] ? '是' : '否' }}
                      </span>
                    </div>

                    <!-- Number -->
                    <div v-else-if="field.type === 'number'" class="relative flex items-center">
                      <Input
                        type="number"
                        :model-value="(cat.values?.[field.key] as string | number) ?? ''"
                        :placeholder="field.placeholder || '數值'"
                        class="h-7 text-xs px-2 bg-background"
                        :class="field.unit ? 'pr-10' : ''"
                        @update:model-value="updateCategoryValue(idx, field.key, $event === '' ? '' : Number($event), false)"
                        @blur="persistNow"
                      />
                      <span
                        v-if="field.unit"
                        class="pointer-events-none absolute right-2 text-[10px] font-mono text-muted-foreground"
                      >
                        {{ field.unit }}
                      </span>
                    </div>

                    <!-- Date -->
                    <Input
                      v-else-if="field.type === 'date'"
                      type="date"
                      :model-value="String(cat.values?.[field.key] ?? '')"
                      class="h-7 text-xs px-2 bg-background"
                      @update:model-value="updateCategoryValue(idx, field.key, $event as string, true)"
                    />

                    <!-- Text -->
                    <Input
                      v-else
                      type="text"
                      :model-value="String(cat.values?.[field.key] ?? '')"
                      :placeholder="field.placeholder || field.label"
                      class="h-7 text-xs px-2 bg-background"
                      @update:model-value="updateCategoryValue(idx, field.key, $event as string, false)"
                      @blur="persistNow"
                    />
                  </td>
                </template>

                <!-- 操作欄 -->
                <td class="py-2 px-3 align-middle text-right">
                  <span
                    v-if="cat.is_control"
                    class="inline-flex items-center gap-1 text-[11px] text-muted-foreground/70 select-none whitespace-nowrap"
                  >
                    <Lock class="size-3 shrink-0" />
                    基準鎖定
                  </span>
                  <button
                    v-else
                    type="button"
                    class="inline-flex items-center justify-center h-6 px-2 rounded text-xs font-medium text-destructive hover:bg-destructive/10 cursor-pointer transition-colors"
                    title="刪除此組別"
                    @click="removeCategory(idx)"
                  >
                    <Trash2 class="size-3.5" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </CardContent>
  </Card>
</template>
